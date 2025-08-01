import json
import time

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
    with open(file_path) as f:
        data = json.load(f)

    # Get all events from the scripted_events array
    all_events = data.get('scripted_events', [])
    scripted_events = [ScriptedEvent(**event) for event in all_events]
    return scripted_events