import json
import os
import time
from typing import Any

import requests
from anthropic import Client
from pydantic import BaseModel

from scenario_server.main import SCENARIO_STATE, SCRIPTED_EVENTS
from scenario_server.narration import narrate_state, generate_agent_event
from scenario_server.scenario import ScriptedEvent, ScenarioState


class AgentAction(BaseModel):
    agent: str
    action_type: str
    payload: dict[str, Any]


class Agent(BaseModel):
    name: str
    base_url: str  # e.g. "http://localhost:8000"


REGISTERED_AGENTS: dict[str, Agent] = {}

anthropic_client = Client(api_key=os.getenv("ANTHROPIC_API_KEY"))


def process_action(action: AgentAction, scenario_state: ScenarioState) -> ScriptedEvent:
    # Call the LLM with the agent action and the current scenarioState, telling it to think about the effect the action will have, and to return a scripted event json
    event_json: str = generate_agent_event(agent_action=action, state=scenario_state, anthropic_client=anthropic_client)
    event_data: dict = json.loads(event_json)
    return ScriptedEvent(**event_data)


actions_this_turn: list[AgentAction] = []
max_steps: int = 100 # todo make this configurable


def main_loop():
    sleep_time_seconds = 3

    while SCENARIO_STATE.running:
        # Wait for all agents to submit their actions
        if actions_this_turn.count != len(REGISTERED_AGENTS):
            # If not all agents have submitted actions, wait (after which we check again)
            time.sleep(sleep_time_seconds)
            continue
        else:
            simulate_one_step(actions_this_turn)
            actions_this_turn.clear()
            if SCENARIO_STATE.current_step == max_steps:
                SCENARIO_STATE.running = False
                print("Scenario has ended after reaching the maximum number of steps.")


# takes the narrated general scenario state and the last action of the agent, as well as their location, and returns a narration for the agent
def narrate_agent_state(general_state_narrated: str, agent: str, agent_location: str) -> str:
    # todo!
    pass


def simulate_one_step(actions: list[AgentAction]):
    # first, process agent actions
    agent_events: list[ScriptedEvent] = [process_action(action, SCENARIO_STATE) for action in actions] # todo only create events when action type is action
    # todo log agent_events
    # trigger agent events
    SCENARIO_STATE.apply_events(agent_events)

    # trigger scripted events
    triggered_events = SCENARIO_STATE.apply_events(SCRIPTED_EVENTS)
    # todo log events that triggered this step

    all_events_triggered_this_round = triggered_events + agent_events

    # generate current state narration for each agent
    general_state_narrated = narrate_state(SCENARIO_STATE, all_events_triggered_this_round, anthropic_client)

    agent_narrations = {} # dict of narration string by agent_name
    for agent_name in REGISTERED_AGENTS:
        agent_narrations[agent_name] = narrate_agent_state(general_state_narrated, agent_name, ) # todo get agent location from scenario state

    # fifth, send narration to agents
    for agent_name in REGISTERED_AGENTS:
        agent_url = REGISTERED_AGENTS[
                        agent_name].base_url + "/scenario/roundnarration"
        requests.post(agent_url, json=agent_narrations[agent_name])
    return
