from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    oncall = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="services")

    def __str__(self):
        return self.name


class Alert(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received"
        TRIAGING = "triaging"
        TRIAGED = "triaged"
        FAILED = "failed"

    service = models.CharField(max_length=100)
    message = models.TextField()
    severity_hint = models.CharField(max_length=20, blank=True)
    timestamp = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # a unique index on a very long message can fail in Postgres, hash the message if that ever happens
        constraints = [models.UniqueConstraint(fields=["service", "message"], name="unique_alert")]


class TriageResult(models.Model):
    alert = models.OneToOneField(Alert, on_delete=models.CASCADE, related_name="result")
    probable_cause = models.TextField()
    confidence = models.FloatField()
    severity = models.CharField(max_length=10)
    action_items = models.JSONField(default=list)
