from pydantic import BaseModel

from scenario import ScenarioState, ScriptedEvent
from util import load_scenario_from_file, load_scripted_events_from_file

SCENARIO_STATE: ScenarioState = load_scenario_from_file()

SCRIPTED_EVENTS: list[ScriptedEvent] = load_scripted_events_from_file()

class AgentAction(BaseModel):
    agent: str
    action_type: str
    action: str


class Agent(BaseModel):
    name: str
    base_url: str  # e.g. "http://localhost:8000"
