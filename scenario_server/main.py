from api import start_api
from classes import SCENARIO_STATE, SCRIPTED_EVENTS
from scenario_server_base import main_loop
from util import save_scenario_to_file


def main():
    start_api()  # Start the API server in a background thread

    print("Starting main loop...")
    main_loop()  # this ends when SCENARIO_STATE.running is False

    # shutdown logic
    print("Saving scenario state...")
    save_scenario_to_file(SCENARIO_STATE, SCRIPTED_EVENTS)
    print("Saving finished, stopping server...")


if __name__ == "__main__":
    main()
