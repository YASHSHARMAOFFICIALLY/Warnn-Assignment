from django.conf import settings
from temporalio.client import Client

from .workflow import TriageWorkflow


async def start_triage(alert_id: int) -> None:
    client = await Client.connect(settings.TEMPORAL_HOST)
    await client.start_workflow(
        TriageWorkflow.run, alert_id, id=f"triage-{alert_id}", task_queue=settings.TASK_QUEUE
    )
