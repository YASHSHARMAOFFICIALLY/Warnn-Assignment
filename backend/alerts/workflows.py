from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from . import activities

TIMEOUT = timedelta(seconds=60)


@workflow.defn
class TriageWorkflow:
    @workflow.run
    async def run(self, alert_id: int) -> None:
        data = await workflow.execute_activity(activities.lookup_service, alert_id, start_to_close_timeout=TIMEOUT)
        try:
            result = await workflow.execute_activity(
                activities.triage_with_ai,
                data,
                start_to_close_timeout=TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=1)),
            )
        except ActivityError:
            await workflow.execute_activity(activities.mark_failed, alert_id, start_to_close_timeout=TIMEOUT)
            return
        await workflow.execute_activity(activities.save_result, args=[alert_id, result], start_to_close_timeout=TIMEOUT)
        await workflow.execute_activity(activities.mark_triaged, alert_id, start_to_close_timeout=TIMEOUT)
