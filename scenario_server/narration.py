from scenario_server.scenario import ScenarioState
from scenario_server.scenario_server import AgentAction


# Here we take the current scenario state and generate a narrative description to be sent to each of the agents.
def narrate_state(
        state: ScenarioState,
        anthropic_client,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 5000,
) -> str:
    """
    Uses Anthropic API to produce a narrative of the current scenario state.
    """
    # todo add the events from the last round here
    prompt = {"role": "user",
              "content": f"Please provide a concise, vivid narrative of the following simulation state:\n" +
                         f"{state.model_dump_json()}\n"}

    response = anthropic_client.messages.create(
        model=model,
        messages=[prompt],
        max_tokens=max_tokens,
    )
    return response.content


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
                           f"generate a scripted event in JSON format. Make sure you think about the implications of the action and how it affects the scenario.",
            }
        ],
        max_tokens=max_tokens,
    )
    return response.content
