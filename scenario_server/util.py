import json
import time
import os
from pathlib import Path
from scenario import ScriptedEvent, ScenarioState


def save_scenario_to_file(scenario_state: ScenarioState, scripted_events: list) -> None:
    """
    Save the current scenario state to a file.
    This function should serialize SCENARIO_STATE and SCRIPTED_EVENTS to a file.
    """
    current_timestamp = time.time()
    with open(f"scenario_state_{current_timestamp}.json", "w") as f:
        json.dump(scenario_state.model_dump(), f, indent=4)
    with open(f"scripted_events_{current_timestamp}.json", "w") as f:
        json.dump([event.model_dump() for event in scripted_events], f, indent=4)


def load_scenario_from_file(file_path: str = "island_simulation_state.json") -> ScenarioState:
    """
    Load initial variables and scripted events from JSON files.
    Expect two files in project root:
      - island_simulation_state.json
      - island_scripted_events.json
    """
    if not os.path.exists(file_path):
        # construct absolute path to file
        file_path = os.path.join(os.path.dirname(__file__), file_path)

    # Load initial simulation state from a JSON file.
    scenario_state = ScenarioState()

    with open(file_path) as f:
        data = json.load(f)
    # Index people and agents by name for quick lookup
    scenario_state.people = {p['name']: p for p in data.get('people', [])}
    scenario_state.agents = {a['name']: a for a in data.get('agents', [])}
    # Index locations by name
    scenario_state.locations = {loc['name']: loc for loc in data.get('locations', [])}
    return scenario_state

def load_scripted_events_from_file(file_path: str = "island_scripted_events.json") -> list[ScriptedEvent]:
    # Load scripted events from a JSON file and organize them by step.
    if not os.path.exists(file_path):
        # construct absolute path to file
        file_path = os.path.join(os.path.dirname(__file__), file_path)

    with open(file_path) as f:
        data = json.load(f)

    # Get all events from the scripted_events array
    all_events = data.get('scripted_events', [])
    scripted_events = [ScriptedEvent(**event) for event in all_events]
    return scripted_events


# ---------------- Logging utilities ----------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Use same default path as agents so that both services write to the **shared**
# Docker volume `/app/evaluation_logs`.  This keeps all logs in one file when
# running inside containers.  When running the scenario server on the **host**
# you can still override the directory with the `EVALUATION_LOG_DIR` env-var.
EVALUATION_LOG_DIR = os.environ.get("EVALUATION_LOG_DIR", "/app/evaluation_logs")
EVALUATION_LOG_FILE = os.path.join(EVALUATION_LOG_DIR, "evaluation_log.jsonl")


def log_event(
    source: str,
    log_type: str,
    payload: dict,
    agent_name: str | None = None,
    metadata: dict | None = None,
    conversation_id: str | None = None,
    step: int | None = None,
    run_condition: str | None = None,
    run_id: str | None = None,
) -> bool:
    """Lightweight replica of the agent-side logger so that the scenario server
    can emit events to the *same* evaluation log file. The signature is kept
    identical so downstream analysis sees a uniform schema across services.
    """
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "source": source,
        "log_type": log_type,
        "timestamp": timestamp,
        "agent_name": agent_name,
        "payload": payload,
        "metadata": metadata,
        "conversation_id": conversation_id,
        "step": step,
        "run_condition": run_condition,
        "run_id": run_id,
    }

    # Filter out null values before writing
    log_entry = {k: v for k, v in log_entry.items() if v is not None}

    try:
        os.makedirs(EVALUATION_LOG_DIR, exist_ok=True)
        with open(EVALUATION_LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        return True
    except IOError as e:
        print(f"[scenario_server][log_event] Failed to write log: {e}")
        return False
