from datetime import datetime

from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404
from ninja import Field, NinjaAPI, Schema
from ninja.errors import HttpError

from . import start_workflow
from .models import Alert

api = NinjaAPI()


class AlertIn(Schema):
    service: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1)
    severity_hint: str = Field("", max_length=20)
    timestamp: datetime | None = None


class TriageResultOut(Schema):
    probable_cause: str
    confidence: float
    severity: str
    action_items: list[str]


class AlertOut(Schema):
    id: int
    service: str
    message: str
    severity_hint: str
    timestamp: datetime | None
    status: str
    created_at: datetime
    severity: str | None = None

    @staticmethod
    def resolve_severity(alert):
        result = getattr(alert, "result", None)
        return result.severity if result else None


class AlertDetailOut(AlertOut):
    result: TriageResultOut | None = None


@api.post("/alerts", response=AlertOut)
def create_alert(request, payload: AlertIn):
    alert, created = Alert.objects.get_or_create(
        service=payload.service,
        message=payload.message,
        defaults={"severity_hint": payload.severity_hint, "timestamp": payload.timestamp},
    )
    if created:
        try:
            async_to_sync(start_workflow.start_triage)(alert.id)
        except Exception:
            # no workflow means nobody will ever triage it, so drop it and let the caller retry
            alert.delete()
            raise HttpError(503, "Could not start triage, workflow service is unavailable")
    return alert


@api.get("/alerts", response=list[AlertOut])
def list_alerts(request):
    return Alert.objects.select_related("result").order_by("-id")


@api.get("/alerts/{alert_id}", response=AlertDetailOut)
def get_alert(request, alert_id: int):
    # alert.result raises when there is no result yet, ninja treats that as missing and returns null
    return get_object_or_404(Alert.objects.select_related("result"), id=alert_id)
