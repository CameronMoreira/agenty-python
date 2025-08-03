import re

from scenario import ScenarioState, ScriptedEvent
from scenario_server_base import AgentAction


# Here we take the current scenario state and generate a narrative description to be sent to each of the agents.
def narrate_state(
        state: ScenarioState,
        events_this_round: list[ScriptedEvent],
        anthropic_client,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 5000,
) -> str:
    """
    Uses Anthropic API to produce a narrative of the current scenario state.
    """
    prompt = {"role": "user",
              "content": f"Please provide a concise, vivid narrative of the following simulation state, keeping in mind " +
                         f"that one 'step' is approximately equivalent to 5 minutes or so, unless otherwise indicated through event descriptions:\n" +
                         f"{state.model_dump_json()}\n"
                         f"Mention especially the following events that occurred in the last round:\n" +
                         "\n".join([event.model_dump_json() for event in events_this_round])}

    response = anthropic_client.messages.create(
        model=model,
        messages=[prompt],
        max_tokens=max_tokens,
    )
    return response.content[0].text


# takes the narrated general scenario state and the last action of the agent, as well as their location, and returns a narration for the agent
def narrate_agent_state(general_state_narrated: str,
                        location_state: dict,
                        agent: str,
                        agent_location: str,
                        anthropic_client,
                        model: str = "claude-sonnet-4-20250514",
                        max_tokens: int = 5000) -> str:
    prompt = {"role": "user",
              "content": f"Please provide a concise, vivid narrative of the simulation state, specifically for agent {agent}," +
                         f" who is currently in the following location: {agent_location}. " +
                         f"Here is the current general simulation state, already narrated:\n" +
                         f"{general_state_narrated}\n\n" +
                         f"Here is the scenario state for the location that the agent is currently in ({agent_location}):\n" +
                         f"\n{location_state}\n\n" +
                         "Please include any relevant details about the agent's surroundings, current situation, and any " +  # todo add recent events
                         "actions they have taken recently, but make sure not to mention anything that the agent could not reasonably know."}

    response = anthropic_client.messages.create(
        model=model,
        messages=[prompt],
        max_tokens=max_tokens,
    )
    return response.content[0].text


def generate_agent_event(
        agent_action: AgentAction,
        state: ScenarioState,
        anthropic_client,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 5000,
) -> str:
    response = anthropic_client.messages.create(
        model=model,
        system="You are a helpful assistant that generates scripted events based on agent actions and the current scenario state.",
        messages=[
            {
                "role": "user",
                "content": f"Given the action {agent_action.model_dump_json()} and the current scenario state {state.model_dump_json()}, " +
                           f"generate a scripted event in JSON format. Make sure you think about the implications of the action and how it affects the scenario."
                           f"This is the structure for the scripted event:\n" +
                           """class ScriptedEvent(BaseModel):
                            name: str
                            description: str
                            effect: Optional[dict[str, Any]] = None
                            location: Optional[str] = None
                            at_step: Optional[int] = None
                            repeatable: bool = False
                            probability: float = 1.0  # Default to 100% if not specified
                            trigger_condition: Optional[str] = None  # "Person.attribute = value" or "Person.attribute != value"
                            has_occurred: bool = False""",
            }
        ],
        max_tokens=max_tokens,
    )
    return extract_json(response.content[0].text.replace("`", "").replace("json", "").strip())


def extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in text")
    return match.group(0)
