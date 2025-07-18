from scenario_server.api import start_api
from scenario_server.scenario import ScenarioState, ScriptedEvent
from scenario_server.scenario_server import main_loop
from scenario_server.util import load_defaults, save_scenario_to_file

SCENARIO_STATE = ScenarioState( # actual scenario gets loaded from file
    step=0,
    time=0.0,
    variables={},
    locations={},
    event_log=[]
)

SCRIPTED_EVENTS: list[ScriptedEvent] = [] # defaults get loaded from files


def main():
    # Initialize the scenario state and scripted events
    print("Loading scenario data from files...")
    load_defaults(SCENARIO_STATE, SCRIPTED_EVENTS)
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
