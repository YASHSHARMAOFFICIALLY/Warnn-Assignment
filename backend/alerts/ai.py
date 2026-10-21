import os
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel


class Triage(BaseModel):
    probable_cause: str
    confidence: float = Field(ge=0, le=1)
    severity: Literal["Sev1", "Sev2", "Sev3", "Sev4"]
    action_items: list[str]


PROMPT = "You triage production alerts. Give the probable cause, a confidence from 0 to 1, a severity Sev1 (worst) to Sev4, and short action items."


def run_triage(alert: dict, context: dict) -> Triage:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openrouter import OpenRouterProvider

        name = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
        model = OpenAIChatModel(name, provider=OpenRouterProvider(api_key=key))
    else:
        model = TestModel()
    agent = Agent(model, output_type=Triage, system_prompt=PROMPT)
    text = f"Alert: {alert}\nService owner info: {context}"
    return agent.run_sync(text).output
