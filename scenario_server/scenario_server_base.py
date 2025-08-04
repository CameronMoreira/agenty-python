import json
import os
import time

import requests
import hashlib
from util import log_event
from anthropic import Client

from classes import SCENARIO_STATE, SCRIPTED_EVENTS, Agent, AgentAction
from narration import narrate_state, generate_agent_event, narrate_agent_state
from scenario import ScriptedEvent, ScenarioState

REGISTERED_AGENTS: dict[str, Agent] = {}
# Determine how many agents are expected based on an environment variable.
# Falls back to 2 for backwards-compatibility.
EXPECTED_AGENTS: int = int(os.getenv("AGENT_COUNT", "2"))

RUN_ID = os.getenv("RUN_ID", "unknown_run")

anthropic_client = Client(api_key=os.getenv("ANTHROPIC_API_KEY"))


def process_action(action: AgentAction, scenario_state: ScenarioState) -> ScriptedEvent:
    # Call the LLM with the agent action and the current scenarioState, telling it to think about the effect the action will have, and to return a scripted event json
    event_json: str = generate_agent_event(agent_action=action, state=scenario_state, anthropic_client=anthropic_client)
    print(f"Generated event JSON for action '{action.action}' by agent '{action.agent}': \n\n{event_json}")
    event_data: dict = json.loads(event_json)
    return ScriptedEvent(**event_data)


actions_this_turn: list[AgentAction] = []
max_steps: int = 3  # todo make this configurable


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

    # Log agent events that were produced this step
    if agent_events:
        log_event(
            source="scenario_server",
            log_type="agent_events_processed",
            step=SCENARIO_STATE.step,
            payload={
                            "step": SCENARIO_STATE.step,
            "agent_events": [e.model_dump() for e in agent_events]
        },
        run_id=RUN_ID
        )
    # trigger agent events
    SCENARIO_STATE.apply_events(agent_events)
    print(f"Agent events processed for step {SCENARIO_STATE.step}: {len(agent_events)} events")

    # trigger scripted events
    triggered_events = SCENARIO_STATE.apply_events(SCRIPTED_EVENTS)
    # First, make sure every triggered event has a step number
    current_step = SCENARIO_STATE.step
    for event in triggered_events:
        if event.at_step is None:
            event.at_step = current_step

    # Log scripted events triggered by the environment this step
    # TODO deprecated lib
    if triggered_events:
        log_event(
            source="scenario_server",
            log_type="scripted_events_triggered",
            step=current_step,
            payload={
                "step": current_step,
                "scripted_events": [e.dict() if hasattr(e, "dict") else e for e in triggered_events]
            },
            run_id=RUN_ID
        )

    all_events_triggered_this_round = triggered_events + agent_events
    print(f"Events triggered this round: {len(all_events_triggered_this_round)}")

    # generate current state narration for each agent
    general_state_narrated = narrate_state(SCENARIO_STATE, all_events_triggered_this_round, anthropic_client)
    print(f"General state narration for step {SCENARIO_STATE.step}:\n{general_state_narrated}")
    narration_id = hashlib.sha256(general_state_narrated.encode()).hexdigest()[:12]
    # Log the general narration text (store full text once)
    # TODO deprecated lib
    log_event(
        source="scenario_server",
        log_type="general_state_narrated",
        step=SCENARIO_STATE.step,
        payload={
            "step": SCENARIO_STATE.step,
            "narration_id": narration_id,
            "narration": general_state_narrated,
            "events_this_round": [e.dict() if hasattr(e, "dict") else e for e in all_events_triggered_this_round],
            "world_state": SCENARIO_STATE.model_dump()
        },
        run_id=RUN_ID
    )

    agent_narrations: dict[str, str] = {}  # dict of narration string by agent_name
    for agent_name in REGISTERED_AGENTS:
        agent_location = SCENARIO_STATE.agents[agent_name]["current_location"]
        location_state = SCENARIO_STATE.locations.get(agent_location)
        agent_narrations[agent_name] = narrate_agent_state(
            general_state_narrated,
            location_state,
            all_events_triggered_this_round, 
            agent_name,
            agent_location,
            anthropic_client,
        )
        print(f"Agent narration generated for step {SCENARIO_STATE.step}: {agent_narrations[agent_name]}")
        # Log only reference to narration to avoid duplication
        log_event(
            source="scenario_server",
            log_type="agent_narration_sent",
            step=SCENARIO_STATE.step,
            agent_name=agent_name,
            payload={
                "step": SCENARIO_STATE.step,
                "narration_id": narration_id,
                "location": agent_location,
            },
            run_id=RUN_ID
        )

    # Only send narrations to agents if we have **not** reached the final step yet.
    # This prevents agents from receiving another round prompt once the scenario is finished.
    if SCENARIO_STATE.step < max_steps:
        # Send narration to each agent, trying a small port range in case the
        # expected port (8080+index) was unavailable and Docker mapped to the next
        # free one (common when 8082 is busy and the second agent ends up on 8083).
        for agent_name, agent in REGISTERED_AGENTS.items():
            narration_payload = {"narration": agent_narrations[agent_name]}
            base_url = agent.base_url

            # First try the stored URL
            try:
                requests.post(f"{base_url}/scenario/roundnarration", json=narration_payload, timeout=2)
                continue  # success
            except Exception:
                pass  # fall through to brute-force search

            # If that failed, probe a few adjacent host ports (helps when the host
            # reserved 8082 and Docker jumped to 8083, etc.)
            # Derive current host port from the stored base_url and probe a few
            # ports above it (Docker usually increments by +1 when the preferred
            # port is busy).
            # TODO: this is only relevant when scenario_server is running outside of Docker for debugging purposes; it won't run if the internal endpoint can be resolved in a docker env
            try:
                current_port = int(base_url.rsplit(":", 1)[-1])
            except ValueError:
                current_port = 8081  # fallback

            for port_offset in range(1, 4):  # try +1, +2, +3
                candidate_port = current_port + port_offset
                candidate_url = f"http://localhost:{candidate_port}/scenario/roundnarration"
                try:
                    requests.post(candidate_url, json=narration_payload, timeout=2)
                    # Update the registered base URL for future rounds
                    agent.base_url = f"http://localhost:{candidate_port}"
                    break
                except Exception:
                    continue
    else:
        print("\033[92mFinal step reached: no further narrations sent to agents.\033[0m")
    return
