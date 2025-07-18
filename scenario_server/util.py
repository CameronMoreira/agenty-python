import json
import time

from scenario_server.scenario import ScriptedEvent, ScenarioState


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


def load_defaults(scenario_state: ScenarioState, scripted_events: list[ScriptedEvent]) -> None:
    """
    Load initial variables and scripted events from JSON files.
    Expect two files in project root:
      - initial_state.json
      - scripted_events.json
    """
    import json
    # Load initial variables and locations
    try:
        with open("initial_state.json", "r") as f:
            init = json.load(f)
        scenario_state.variables = init.get("variables", {})
        scenario_state.locations = init.get("locations", {})
        scenario_state.step = init.get("step", scenario_state.step)
        scenario_state.time = init.get("time", scenario_state.time)
    except FileNotFoundError:
        print("initial_state.json not found, using defaults")

    # Load scripted events
    try:
        with open("scripted_events.json", "r") as f:
            events = json.load(f)
        for ev in events:
            scripted_events.append(ScriptedEvent(**ev))
    except FileNotFoundError:
        print("scripted_events.json not found, using hardcoded defaults")
