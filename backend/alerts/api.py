from datetime import datetime
from typing import Optional

from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema

from . import client
from .models import Alert

api = NinjaAPI()


class AlertIn(Schema):
    service: str
    message: str
    severity_hint: str = ""
    timestamp: Optional[datetime] = None


class ResultOut(Schema):
    probable_cause: str
    confidence: float
    severity: str
    action_items: list[str]


class AlertOut(Schema):
    id: int
    service: str
    message: str
    severity_hint: str
    timestamp: Optional[datetime]
    status: str


class AlertDetailOut(AlertOut):
    result: Optional[ResultOut] = None


@api.post("/alerts", response=AlertOut)
def create_alert(request, payload: AlertIn):
    alert, created = Alert.objects.get_or_create(
        service=payload.service,
        message=payload.message,
        defaults={"severity_hint": payload.severity_hint, "timestamp": payload.timestamp},
    )
    if created:
        async_to_sync(client.start_triage)(alert.id)
    return alert


@api.get("/alerts", response=list[AlertOut])
def list_alerts(request):
    return Alert.objects.order_by("-id")


@api.get("/alerts/{alert_id}", response=AlertDetailOut)
def get_alert(request, alert_id: int):
    alert = get_object_or_404(Alert.objects.select_related("result"), id=alert_id)
    out = AlertDetailOut.from_orm(alert)
    out.result = getattr(alert, "result", None) and ResultOut.from_orm(alert.result)
    return out
