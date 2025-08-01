import json
import os
import time

import requests
from anthropic import Client

from classes import SCENARIO_STATE, SCRIPTED_EVENTS, Agent, AgentAction
from narration import narrate_state, generate_agent_event, narrate_agent_state
from scenario import ScriptedEvent, ScenarioState

REGISTERED_AGENTS: dict[str, Agent] = {}
EXPECTED_AGENTS: int = 2

anthropic_client = Client(api_key=os.getenv("ANTHROPIC_API_KEY"))


def process_action(action: AgentAction, scenario_state: ScenarioState) -> ScriptedEvent:
    # Call the LLM with the agent action and the current scenarioState, telling it to think about the effect the action will have, and to return a scripted event json
    event_json: str = generate_agent_event(agent_action=action, state=scenario_state, anthropic_client=anthropic_client)
    print(f"Generated event JSON for action {action.action_type} by agent {action.agent}: {event_json}")
    event_data: dict = json.loads(event_json)
    return ScriptedEvent(**event_data)


actions_this_turn: list[AgentAction] = []
max_steps: int = 50  # todo make this configurable


def main_loop():
    sleep_time_seconds = 3
    current_step = 0
    while len(REGISTERED_AGENTS) < EXPECTED_AGENTS:
        print(f"Waiting for all agents to register... ({len(REGISTERED_AGENTS)}/{EXPECTED_AGENTS})")
        time.sleep(sleep_time_seconds * 2)

    SCENARIO_STATE.running = True
    while SCENARIO_STATE.running:
        # Wait for all agents to submit their actions
        if len(actions_this_turn) < len(REGISTERED_AGENTS):
            # If not all agents have submitted actions, wait (after which we check again)
            print(f"Waiting for all agents to submit actions... ({len(actions_this_turn)}/{len(REGISTERED_AGENTS)})")
            time.sleep(sleep_time_seconds)
            continue
        else:
            current_step += 1
            SCENARIO_STATE.step = current_step
            simulate_one_step(actions_this_turn)
            actions_this_turn.clear()
            if SCENARIO_STATE.step == max_steps:
                SCENARIO_STATE.running = False
                print("Scenario has ended after reaching the maximum number of steps.")


def simulate_one_step(actions: list[AgentAction]):
    print(f"Simulating step {SCENARIO_STATE.step} with actions from all agents...")
    # first, process agent actions
    agent_events: list[ScriptedEvent] = []
    for action in actions:
        if action.action_type == "action":
            # Process the action and generate a scripted event
            event = process_action(action, SCENARIO_STATE)
            agent_events.append(event)

    # todo log agent_events
    # trigger agent events
    SCENARIO_STATE.apply_events(agent_events)
    print(f"Agent events processed for step {SCENARIO_STATE.step}: {len(agent_events)} events")

    # trigger scripted events
    triggered_events = SCENARIO_STATE.apply_events(SCRIPTED_EVENTS)
    # todo log events that triggered this step

    all_events_triggered_this_round = triggered_events + agent_events
    print(f"Events triggered this round: {len(all_events_triggered_this_round)}")

    # generate current state narration for each agent
    general_state_narrated = narrate_state(SCENARIO_STATE, all_events_triggered_this_round, anthropic_client)
    print(f"General state narration for step {SCENARIO_STATE.step}:\n{general_state_narrated}")
    # todo potentially log the general state narration

    agent_narrations: dict[str, str] = {}  # dict of narration string by agent_name
    for agent_name in REGISTERED_AGENTS:
        agent_location = SCENARIO_STATE.agents[agent_name]["current_location"]
        location_state = SCENARIO_STATE.locations.get(agent_location)
        agent_narrations[agent_name] = narrate_agent_state(general_state_narrated, location_state, agent_name,
                                                           agent_location, anthropic_client)
        print(f"Agent narration generated for step {SCENARIO_STATE.step}: {agent_narrations[agent_name]}")

    # send narration to agents
    for agent_name in REGISTERED_AGENTS:
        agent_url = REGISTERED_AGENTS[
                        agent_name].base_url + "/scenario/roundnarration"
        requests.post(agent_url, json={"narration": agent_narrations[agent_name]})
    return
