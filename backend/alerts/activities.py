from temporalio import activity

from .ai import run_triage
from .models import Alert, Service, TriageResult


@activity.defn
def mark_triaging(alert_id: int) -> None:
    Alert.objects.filter(id=alert_id).update(status=Alert.Status.TRIAGING)


@activity.defn
def lookup_service(alert_id: int) -> dict:
    """Load the alert and the team that owns its service. Team is None for unknown services."""
    alert = Alert.objects.get(id=alert_id)
    service = Service.objects.filter(name=alert.service).select_related("team").first()
    return {
        "alert": {"service": alert.service, "message": alert.message, "severity_hint": alert.severity_hint},
        "team": service.team.name if service else None,
        "oncall": service.team.oncall if service else None,
    }


@activity.defn
def triage_with_ai(data: dict) -> dict:
    return run_triage(data["alert"], data["team"], data["oncall"]).model_dump()


@activity.defn
def save_result(alert_id: int, result: dict) -> None:
    # update_or_create so a retried activity does not fail on the one-to-one
    TriageResult.objects.update_or_create(alert_id=alert_id, defaults=result)


@activity.defn
def mark_triaged(alert_id: int) -> None:
    Alert.objects.filter(id=alert_id).update(status=Alert.Status.TRIAGED)


@activity.defn
def mark_failed(alert_id: int) -> None:
    Alert.objects.filter(id=alert_id).update(status=Alert.Status.FAILED)
