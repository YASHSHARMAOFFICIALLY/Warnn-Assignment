import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alert_triage.settings")
django.setup()

from django.conf import settings  # noqa: E402
from temporalio.client import Client  # noqa: E402
from temporalio.worker import Worker  # noqa: E402

from alerts import activities  # noqa: E402
from alerts.workflow import TriageWorkflow  # noqa: E402


async def main():
    client = await Client.connect(settings.TEMPORAL_HOST)
    worker = Worker(
        client,
        task_queue=settings.TASK_QUEUE,
        workflows=[TriageWorkflow],
        activities=[
            activities.mark_triaging,
            activities.lookup_service,
            activities.triage_with_ai,
            activities.save_result,
            activities.mark_triaged,
            activities.mark_failed,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=5),
    )
    await worker.run()


asyncio.run(main())
