from api import start_api
from scenario import ScenarioState, ScriptedEvent
from scenario_server_base import main_loop
from util import save_scenario_to_file, load_scenario_from_file, load_scripted_events_from_file

SCENARIO_STATE: ScenarioState = ScenarioState()

SCRIPTED_EVENTS: list[ScriptedEvent] = []  # defaults get loaded from files


def main():
    global SCENARIO_STATE, SCRIPTED_EVENTS
    # Initialize the scenario state and scripted events
    print("Loading scenario data from files...")
    SCENARIO_STATE = load_scenario_from_file()
    SCRIPTED_EVENTS = load_scripted_events_from_file()
    print("Loading finished, starting server...")
    start_api()  # Start the API server in a background thread

    print("Starting main loop...")
    main_loop()  # this ends when SCENARIO_STATE.running is False

    # shutdown logic
    print("Saving scenario state...")
    save_scenario_to_file(SCENARIO_STATE, SCRIPTED_EVENTS)
    print("Saving finished, stopping server...")


if __name__ == "__main__":
    main()
