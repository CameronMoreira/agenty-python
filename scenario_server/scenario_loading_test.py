from scenario import ScenarioState, ScriptedEvent
from util import load_scenario_from_file, load_scripted_events_from_file

if __name__ == '__main__':
    sim: ScenarioState = load_scenario_from_file()
    scripted_events: list[ScriptedEvent] = load_scripted_events_from_file()

    for step in range(30):
        sim.step = step + 1
        print(f"\n=== Applying step {step} ===")
        sim.apply_events(scripted_events)
        # Print events that occurred this step
        for entry in sim.event_log:
            if entry['step'] == step:
                print(f"- {entry['name']}: {entry['effect']}")

    # Output final state
    print('\n=== Final Scenario State ===')
    print(sim.model_dump_json(indent=2))