import json
import random
from typing import Dict, Any, Optional, List

class ScenarioState:
    def __init__(self):
        # Initialize state containers
        self.people: Dict[str, Dict[str, Any]] = {}
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.locations: Dict[str, Dict[str, Any]] = {}
        self.variables: Dict[str, Any] = {}
        self.events_by_step: Dict[int, List[Dict[str, Any]]] = {}
        self.event_log: List[Dict[str, Any]] = []
        self.step: Optional[int] = None

    def load_state(self, state_file: str) -> None:
        """
        Load initial simulation state from a JSON file.
        """
        with open(state_file) as f:
            data = json.load(f)
        # Index people and agents by name for quick lookup
        self.people = {p['name']: p for p in data.get('people', [])}
        self.agents = {a['name']: a for a in data.get('agents', [])}
        # Index locations by name
        self.locations = {loc['name']: loc for loc in data.get('locations', [])}

    def load_events(self, events_file: str) -> None:
        """
        Load scripted events from a JSON file and organize them by step.
        """
        with open(events_file) as f:
            data = json.load(f)
        
        # Get all events from the scripted_events array
        all_events = data.get('scripted_events', [])
        
        # Organize events by step
        self.events_by_step = {}
        for event in all_events:
            at_step = event.get('at_step')
            if at_step is not None:
                # Event is tied to a specific step
                if at_step not in self.events_by_step:
                    self.events_by_step[at_step] = []
                self.events_by_step[at_step].append(event)
            # Events without at_step will be handled in apply_step

    def apply_step(self, step_num: int) -> None:
        """
        Apply all events for the given step number.
        """
        self.step = step_num
        
        # Get events for this specific step
        step_events = self.events_by_step.get(step_num, [])
        
        # Process step-specific events
        for event in step_events:
            self._process_event(event)
        
        # Also process any events that don't have at_step (can occur at any step)
        # We'll collect all events and filter for those without at_step
        all_events = []
        for events in self.events_by_step.values():
            all_events.extend(events)
        
        # Filter for events without at_step
        any_step_events = [event for event in all_events if event.get('at_step') is None]
        
        # Process any-step events
        for event in any_step_events:
            self._process_event(event)

    def apply_round(self, round_num: int) -> None:
        """
        Apply all events for the given round number. Sets step=round_num.
        (Backward compatibility method)
        """
        self.apply_step(round_num)

    def _process_event(self, event: Dict[str, Any]) -> None:
        """
        Process a single event, checking conditions and applying effects.
        """
        # Skip non-repeatable events that already occurred
        if not event.get('repeatable', False) and event.get('has_occurred', False):
            return
        
        # Check trigger conditions if they exist
        trigger_condition = event.get('trigger_condition')
        if trigger_condition and not self._check_trigger_condition(trigger_condition):
            return
        
        # Roll probability
        if random.random() <= event.get('probability', 1.0):
            # Apply the effects
            self.apply_effect(event.get('effect', {}), event.get('location'))
            # Mark as occurred
            event['has_occurred'] = True
            # Log it
            self.event_log.append({
                'step': self.step,
                'name': event.get('name'),
                'description': event.get('description'),
                'effect': event.get('effect'),
                'location': event.get('location'),
            })

    def _check_trigger_condition(self, condition: str) -> bool:
        """
        Check if a trigger condition is met.
        Format: "Person.attribute = value" or "Person.attribute != value"
        """
        try:
            if '=' in condition:
                person_attr, value = condition.split('=', 1)
                person_name, attr = person_attr.strip().split('.', 1)
                person_name = person_name.strip()
                attr = attr.strip()
                value = value.strip()
                
                if person_name in self.people:
                    person = self.people[person_name]
                    if attr in person:
                        return str(person[attr]) == value
                elif person_name in self.agents:
                    agent = self.agents[person_name]
                    if attr in agent:
                        return str(agent[attr]) == value
            return False
        except:
            return False

    def apply_effect(self, effect: Dict[str, Any], location: Optional[str]) -> None:
        """
        Apply the given effect dict to the scenario state.
        Keys matching person or agent names update their stats.
        Keys 'food', 'water', 'materials' update supplies at the given location or globally.
        Other keys are treated as global variables/flags.
        """
        for key, change in effect.items():
            # Person
            if key in self.people:
                for attr, delta in change.items():
                    if isinstance(delta, dict):
                        # Handle nested attributes like injuries or damages_to_robotic_body
                        if attr not in self.people[key]:
                            self.people[key][attr] = {}
                        self.people[key][attr].update(delta)
                    else:
                        self.people[key][attr] = self.people[key].get(attr, 0) + delta
            # Agent
            elif key in self.agents:
                for attr, delta in change.items():
                    if isinstance(delta, dict):
                        # Handle nested attributes like damages_to_robotic_body
                        if attr not in self.agents[key]:
                            self.agents[key][attr] = {}
                        self.agents[key][attr].update(delta)
                    else:
                        self.agents[key][attr] = self.agents[key].get(attr, 0) + delta
            # Supplies categories
            elif key in ('food', 'water', 'materials'):
                target = None
                if location and location in self.locations:
                    # Update supplies at specific location
                    supplies = self.locations[location]['supplies_at_location'].setdefault(key, {})
                    target = supplies
                else:
                    # Update global supplies variable
                    target = self.variables.setdefault(key, {})
                for item, delta in change.items():
                    # Handle case where target might be a list instead of dict
                    if isinstance(target, list):
                        # Convert list to dict with count 1 for each item
                        target_dict = {}
                        for existing_item in target:
                            target_dict[existing_item] = target_dict.get(existing_item, 0) + 1
                        target = target_dict
                        # Update the original location with the new dict structure
                        if location and location in self.locations:
                            self.locations[location]['supplies_at_location'][key] = target
                        else:
                            self.variables[key] = target
                    # Now target is guaranteed to be a dict
                    target[item] = target.get(item, 0) + delta
            # Generic global variable or flag
            else:
                self.variables[key] = change

    def to_dict(self) -> Dict[str, Any]:
        """
        Export the full scenario state (including any global variables and event log).
        """
        return {
            'people': list(self.people.values()),
            'agents': list(self.agents.values()),
            'locations': list(self.locations.values()),
            'variables': self.variables,
            'event_log': self.event_log,
        }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run island scenario simulation')
    parser.add_argument('--state', type=str, default='island_simulation_state.json',
                        help='Path to the initial simulation state JSON')
    parser.add_argument('--events', type=str, default='island_scripted_events.json',
                        help='Path to the scripted events JSON')
    parser.add_argument('--steps', type=int, nargs='+', default=None,
                        help='Specific steps to run (e.g., 1 2 3). Defaults to all.')
    args = parser.parse_args()

    sim = ScenarioState()
    sim.load_state(args.state)
    sim.load_events(args.events)

    # Determine steps to run
    all_steps = sorted(sim.events_by_step.keys())
    steps_to_run = args.steps if args.steps else all_steps

    for step in steps_to_run:
        print(f"\n=== Applying step {step} ===")
        sim.apply_step(step)
        # Print events that occurred this step
        for entry in sim.event_log:
            if entry['step'] == step:
                print(f"- {entry['name']}: {entry['effect']}")

    # Output final state
    final = sim.to_dict()
    print('\n=== Final Scenario State ===')
    #print(json.dumps(final, indent=2))