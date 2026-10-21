from unittest.mock import AsyncMock, patch

import pytest

from . import activities
from .ai import run_triage
from .models import Alert, Service, Team, TriageResult

pytestmark = pytest.mark.django_db

ALERT = {"service": "checkout-api", "message": "500s spiking", "severity_hint": "high"}


@pytest.fixture(autouse=True)
def fake_workflow():
    with patch("alerts.start_workflow.start_triage", new=AsyncMock()) as mock:
        yield mock


def post(client, body=ALERT):
    return client.post("/alerts", data=body, content_type="application/json")


def test_create_alert(client, fake_workflow):
    res = post(client)
    assert res.status_code == 200
    assert res.json()["status"] == "received"
    assert Alert.objects.count() == 1
    fake_workflow.assert_awaited_once()


def test_duplicate_returns_existing(client, fake_workflow):
    first = post(client).json()
    second = post(client).json()
    assert first["id"] == second["id"]
    assert Alert.objects.count() == 1
    fake_workflow.assert_awaited_once()


def test_invalid_alert_rejected(client):
    assert post(client, {"service": "", "message": "x"}).status_code == 422
    assert post(client, {"message": "x"}).status_code == 422
    assert Alert.objects.count() == 0


def test_workflow_down_returns_503_and_keeps_nothing(client, fake_workflow):
    fake_workflow.side_effect = RuntimeError("temporal down")
    res = post(client)
    assert res.status_code == 503
    assert Alert.objects.count() == 0


def test_get_result(client):
    alert = Alert.objects.create(service="checkout-api", message="x", status="triaged")
    TriageResult.objects.create(
        alert=alert, probable_cause="bad deploy", confidence=0.8, severity="Sev2", action_items=["rollback"]
    )
    body = client.get(f"/alerts/{alert.id}").json()
    assert body["result"]["severity"] == "Sev2"
    assert body["result"]["action_items"] == ["rollback"]
    first = client.get("/alerts").json()[0]
    assert first["status"] == "triaged"
    assert first["severity"] == "Sev2"
    assert first["created_at"]


def test_get_alert_without_result_and_missing_alert(client):
    alert = Alert.objects.create(**ALERT)
    assert client.get(f"/alerts/{alert.id}").json()["result"] is None
    assert client.get("/alerts/9999").status_code == 404


def test_activities_in_order():
    team = Team.objects.create(name="Payments", oncall="a@b.c")
    Service.objects.create(name="checkout-api", team=team)
    alert = Alert.objects.create(**ALERT)

    activities.mark_triaging(alert.id)
    alert.refresh_from_db()
    assert alert.status == "triaging"

    data = activities.lookup_service(alert.id)
    assert data["team"] == "Payments"

    activities.save_result(alert.id, activities.triage_with_ai(data))
    activities.mark_triaged(alert.id)
    alert.refresh_from_db()
    assert alert.status == "triaged"
    assert alert.result.severity in ["Sev1", "Sev2", "Sev3", "Sev4"]


@pytest.mark.parametrize(
    "message, severity, word",
    [
        ("5xx rate above 20%", "Sev2", "dependency"),
        ("payment timeouts", "Sev2", "dependency"),
        ("disk full on node 7", "Sev3", "volume"),
        ("cert expires in 2 days", "Sev3", "certificate"),
        ("something odd happened", "Sev3", "Not enough detail"),
    ],
)
def test_local_model_answers_from_alert_text(monkeypatch, message, severity, word):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = run_triage({"service": "x", "message": message, "severity_hint": ""}, None, None)
    assert result.severity == severity
    assert word in result.probable_cause
    assert len(result.action_items) == 3


def test_failed_ai_call_marks_failed():
    alert = Alert.objects.create(**ALERT)
    data = activities.lookup_service(alert.id)
    with patch("alerts.activities.run_triage", side_effect=RuntimeError("model down")):
        with pytest.raises(RuntimeError):
            activities.triage_with_ai(data)
    # the workflow runs this after the 3 attempts are used up
    activities.mark_failed(alert.id)
    alert.refresh_from_db()
    assert alert.status == "failed"
