from unittest.mock import AsyncMock, patch

import pytest

from . import activities
from .models import Alert, Service, Team, TriageResult

pytestmark = pytest.mark.django_db

ALERT = {"service": "checkout-api", "message": "500s spiking", "severity_hint": "high"}


@pytest.fixture(autouse=True)
def fake_workflow():
    with patch("alerts.client.start_triage", new=AsyncMock()) as m:
        yield m


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


def test_get_result(client):
    alert = Alert.objects.create(service="checkout-api", message="x", status="triaged")
    TriageResult.objects.create(
        alert=alert, probable_cause="bad deploy", confidence=0.8, severity="Sev2", action_items=["rollback"]
    )
    body = client.get(f"/alerts/{alert.id}").json()
    assert body["result"]["severity"] == "Sev2"
    assert body["result"]["action_items"] == ["rollback"]
    assert client.get("/alerts").json()[0]["status"] == "triaged"


def test_activities_save_result():
    team = Team.objects.create(name="Payments", oncall="a@b.c")
    Service.objects.create(name="checkout-api", team=team)
    alert = Alert.objects.create(**ALERT)
    data = activities.lookup_service(alert.id)
    assert data["context"]["team"] == "Payments"
    alert.refresh_from_db()
    assert alert.status == "triaging"
    result = activities.triage_with_ai(data)
    activities.save_result(alert.id, result)
    activities.mark_triaged(alert.id)
    alert.refresh_from_db()
    assert alert.status == "triaged"
    assert alert.result.severity in ["Sev1", "Sev2", "Sev3", "Sev4"]


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
