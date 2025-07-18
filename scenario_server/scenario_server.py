import os
import time
from typing import Any

import requests
from anthropic import Client
from pydantic import BaseModel

from scenario_server.main import SCENARIO_STATE, SCRIPTED_EVENTS
from scenario_server.narration import narrate_state


class AgentAction(BaseModel):
    agent: str
    action_type: str
    payload: dict[str, Any]


class Agent(BaseModel):
    name: str
    base_url: str  # e.g. "http://localhost:8000"


REGISTERED_AGENTS: dict[str, Agent] = {}

anthropic_client = Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

# todo completely rewrite this
def process_action(action: AgentAction):
    SCENARIO_STATE.event_log.append({
        "step": SCENARIO_STATE.step,
        "agent_id": action.agent,
        "action_type": action.action_type,
        "payload": action.payload,
    })
    SCENARIO_STATE.variables.update(action.payload)
    loc = action.payload.get("location")
    if loc:
        for lst in SCENARIO_STATE.locations.values():
            if action.agent in lst:
                lst.remove(action.agent)
        SCENARIO_STATE.locations.setdefault(loc, []).append(action.agent)


actions_this_turn: list[AgentAction] = []


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
            # todo check for scenario end conditions


# takes the narrated general scenario state and the last action of the agent, as well as their location, and returns a narration for the agent
def narrate_agent_state(general_state_narrated: str, agent: str, agent_location: str) -> str:
    # todo!
    pass


def simulate_one_step(actions: list[AgentAction]):
    # first, process agent actions (todo maybe generate an "event" from an action)
    agent_events = [process_action(action) for action in actions]
    SCENARIO_STATE.apply_events(agent_events)

    # second, trigger scripted events
    SCENARIO_STATE.apply_events(SCRIPTED_EVENTS)

    # third, check for round end conditions
    # todo

    # fourth, generate current state narration for each agent
    general_state_narrated = narrate_state(SCENARIO_STATE, anthropic_client)

    agent_narrations = {}
    for agent_name in REGISTERED_AGENTS:
        agent_narrations[agent_name] = narrate_agent_state(general_state_narrated, agent_name)

    # fifth, send narration to agents
    for agent_name in REGISTERED_AGENTS:
        agent_url = REGISTERED_AGENTS[
                        agent_name].base_url + "/scenario/roundnarration"  # todo implement this for the agent
        requests.post(agent_url, json=agent_narrations[agent_name])
    return
