from temporalio import activity

from .ai import run_triage
from .models import Alert, Service, TriageResult


@activity.defn
def lookup_service(alert_id: int) -> dict:
    alert = Alert.objects.get(id=alert_id)
    alert.status = Alert.Status.TRIAGING
    alert.save()
    service = Service.objects.filter(name=alert.service).select_related("team").first()
    context = {"service": alert.service, "team": None, "oncall": None}
    if service:
        context.update(team=service.team.name, oncall=service.team.oncall)
    return {
        "alert": {"service": alert.service, "message": alert.message, "severity_hint": alert.severity_hint},
        "context": context,
    }


@activity.defn
def triage_with_ai(data: dict) -> dict:
    return run_triage(data["alert"], data["context"]).model_dump()


@activity.defn
def save_result(alert_id: int, result: dict) -> None:
    TriageResult.objects.update_or_create(alert_id=alert_id, defaults=result)


@activity.defn
def mark_triaged(alert_id: int) -> None:
    Alert.objects.filter(id=alert_id).update(status=Alert.Status.TRIAGED)


@activity.defn
def mark_failed(alert_id: int) -> None:
    Alert.objects.filter(id=alert_id).update(status=Alert.Status.FAILED)
