import random
from typing import Any, Optional

from pydantic import BaseModel


class ScriptedEvent(BaseModel):
    name: str
    description: str
    effect: Optional[dict[str, Any]] = None
    location: Optional[str] = None
    at_step: Optional[int] = None
    repeatable: bool = False
    probability: float = 1.0  # Default to 100% if not specified
    trigger_condition: Optional[str] = None
    has_occurred: bool = False


class ScenarioState(BaseModel):
    people: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}
    locations: dict[str, dict[str, Any]] = {}
    variables: dict[str, Any] = {}
    event_log: list[dict[str, Any]] = []
    step: Optional[int] = None
    running: bool = False

    def apply_events(self, events: list[ScriptedEvent]) -> list[ScriptedEvent]:
        """
        Apply a list of scripted events, processing each one.
        This is used for events that are triggered by agent actions.
        """
        triggered_events = []

        for event in events:
            triggered = self._process_event(event)
            if triggered:
                triggered_events.append(event)
            if len(triggered_events) >= 5:
                # Limit to 5 events per step to avoid overwhelming the system
                break

        return triggered_events

    def _process_event(self, event: ScriptedEvent) -> bool:
        """
        Process a single event, checking conditions and applying effects.
        """
        # Skip non-repeatable events that already occurred
        if not event.repeatable and event.has_occurred:
            return False

        if event.at_step is not None and event.at_step != self.step:
            # Event is not for this step, skip it
            return False

        # Check trigger conditions if they exist
        if event.trigger_condition and not self._check_trigger_condition(event.trigger_condition):
            return False

        # Roll probability
        probability = event.probability or 1.0  # Default to 100% if not specified
        if random.random() <= probability:
            # Apply the effects
            if event.effect:
                self.apply_effect(event.effect, event.location)
            # Mark as occurred
            event.has_occurred = True
            # Log it
            self.event_log.append({
                'step': self.step,
                'name': event.name,
                'description': event.description,
                'effect': event.effect,
                'location': event.location,
            })
            return True
        return False

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

    def apply_effect(self, effect: dict[str, Any], location: Optional[str]) -> None:
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
