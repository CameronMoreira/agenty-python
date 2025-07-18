from scenario_server.scenario import ScenarioState


# Here we take the current scenario state and generate a narrative description to be sent to each of the agents.
def narrate_state(
        state: ScenarioState,
        anthropic_client,
        model: str = "",  # todo
        max_tokens: int = 5000,
        temperature: float = 0.7,
) -> str:
    """
    Uses Anthropic API to produce a narrative of the current scenario state.
    """
    # todo implement this properly
    prompt = (
        f"Please provide a concise, vivid narrative of the following simulation state:\n"
        f"{state.model_dump_json()}\n"
    )
    response = anthropic_client.completions.create(
        model=model,
        prompt=prompt,
        max_tokens_to_sample=max_tokens,
        temperature=temperature
    )
    return response.completion
