import os
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

SYSTEM_PROMPT = (
    "You triage production alerts. Give the probable cause, a confidence from 0 to 1, "
    "a severity from Sev1 (worst) to Sev4, and a short list of action items."
)


class Triage(BaseModel):
    probable_cause: str
    confidence: float = Field(ge=0, le=1)
    severity: Literal["Sev1", "Sev2", "Sev3", "Sev4"]
    action_items: list[str]


def run_triage(alert: dict, team: str | None, oncall: str | None) -> Triage:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        model_name = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
        model = OpenAIChatModel(model_name, provider=OpenRouterProvider(api_key=api_key))
    else:
        model = TestModel()

    agent = Agent(model, output_type=Triage, system_prompt=SYSTEM_PROMPT)
    prompt = (
        f"Service: {alert['service']}\n"
        f"Message: {alert['message']}\n"
        f"Severity hint: {alert['severity_hint'] or 'none'}\n"
        f"Owning team: {team or 'unknown'} (on call: {oncall or 'unknown'})"
    )
    return agent.run_sync(prompt).output
