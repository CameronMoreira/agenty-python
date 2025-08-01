from typing import Any

from pydantic import BaseModel

from scenario import ScenarioState, ScriptedEvent

SCENARIO_STATE: ScenarioState = ScenarioState()

SCRIPTED_EVENTS: list[ScriptedEvent] = []  # defaults get loaded from files


class AgentAction(BaseModel):
    agent: str
    action_type: str
    payload: dict[str, Any]


class Agent(BaseModel):
    name: str
    base_url: str  # e.g. "http://localhost:8000"
