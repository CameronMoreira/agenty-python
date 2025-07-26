from random import random
from typing import Any, Optional

from pydantic import BaseModel

# todo rewrite this based on our needs/ideas for ScriptedEvents
class ScriptedEvent(BaseModel):
    name: str
    description: str
    at_step: Optional[int] = None
    trigger_condition: Optional[dict[str, Any]] = None
    probability: float = 1.0
    effect: dict[str, Any]
    location: Optional[str] = None
    repeatable: bool = False
    has_occurred: bool = False  # Used to track if the event has already occurred in the current scenario


# todo rewrite this based on the variables we want to track
class ScenarioState(BaseModel):
    step: int
    time: float  # abstract time units
    running: bool = True  # Indicates if the scenario is still running
    variables: dict[str, Any]
    locations: dict[str, list[str]]
    event_log: list[dict[str, Any]]

    def apply_events(self, events: list[ScriptedEvent]):
        """
        Apply a list of scripted events to the scenario state.
        Each event is checked against its conditions and applied if applicable.
        """
        for event in events:
            if not event.has_occurred or event.repeatable:
                self.apply_event(event)
                if not event.repeatable:
                    event.has_occurred = True

    def apply_event(self, event: ScriptedEvent):
        # TODO completely rewrite this once we've got the event system in place
        if random() <= event.probability:
            self.variables.update(event.effect)
            if event.location:
                self.locations.setdefault(event.location, []).extend(
                    event.effect.get("entities", [])
                )
            self.event_log.append({
                "step": self.step,
                "event": event.name,
                "effect": event.effect,
                "location": event.location,
            })


