import os
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.openai import OpenAIChatModel
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


# word to look for in the alert -> (probable cause, severity, confidence, action items)
LOCAL_RULES = [
    (
        ("5xx", "timeout"),
        (
            "A downstream dependency (database, payment provider or another service) is failing or slow",
            "Sev2",
            0.7,
            [
                "Check the health of the services this one calls",
                "Look at the latest deploys and roll back if one lines up",
                "Watch the error rate for the next 15 minutes",
            ],
        ),
    ),
    (
        ("disk full", "disk space"),
        (
            "A volume is almost full, most likely from logs or temp files that were not cleaned up",
            "Sev3",
            0.75,
            ["Find the largest directories on the node", "Delete or rotate old logs", "Add a disk usage alert at 80%"],
        ),
    ),
    (
        ("cert expires", "certificate"),
        (
            "A TLS certificate is close to its expiry date and auto renewal did not run",
            "Sev3",
            0.8,
            ["Renew the certificate", "Deploy it to every host that uses it", "Check why auto renewal failed"],
        ),
    ),
]
GENERIC = (
    "Not enough detail to name a cause, needs a person to look at the logs",
    "Sev3",
    0.5,
    [
        "Read the service logs around the alert time",
        "Ask the owning team if anything changed recently",
        "Add more detail to the alert message",
    ],
)


def local_stand_in(messages, info: AgentInfo) -> ModelResponse:
    # no API key: pick an answer by looking for words in the alert, so it runs offline
    text = str(messages[-1].parts[-1].content).lower()
    cause, severity, confidence, actions = GENERIC
    for words, answer in LOCAL_RULES:
        if any(word in text for word in words):
            cause, severity, confidence, actions = answer
            break
    args = {"probable_cause": cause, "confidence": confidence, "severity": severity, "action_items": actions}
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])


def run_triage(alert: dict, team: str | None, oncall: str | None) -> Triage:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        model_name = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
        model = OpenAIChatModel(model_name, provider=OpenRouterProvider(api_key=api_key))
    else:
        model = FunctionModel(local_stand_in)

    agent = Agent(model, output_type=Triage, system_prompt=SYSTEM_PROMPT)
    prompt = (
        f"Service: {alert['service']}\n"
        f"Message: {alert['message']}\n"
        f"Severity hint: {alert['severity_hint'] or 'none'}\n"
        f"Owning team: {team or 'unknown'} (on call: {oncall or 'unknown'})"
    )
    return agent.run_sync(prompt).output
