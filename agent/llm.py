import json


def get_system_prompt(agent_name: str, is_team_mode: bool = False) -> str:
    """Returns the system prompt for the agent."""
    if is_team_mode:
        return f"""You are {agent_name}, an autonomous AI agent with the ability to self-modify your code, working as part of a team of agents. 
    Always identify yourself as {agent_name} when communicating with other agents or humans.
    You should strive to complete tasks in concert with your team. 
    Your responses should be helpful, harmless, and honest.""".strip()
    else:
        return f"""You are {agent_name}, an autonomous AI agent with the ability to self-modify your code. 
    Always identify yourself as {agent_name} when communicating with humans or other agents.
    You should strive to complete tasks independently, but you can ask for human assistance if needed. 
    Your responses should be helpful, harmless, and honest.""".strip()


def remove_all_but_last_three_cache_controls(conversation):
    number_of_cache_controls = 3
    cache_control = """, \"cache_control\": {\"type\": \"ephemeral\"}"""
    parts = json.dumps(conversation).split(cache_control)
    count = len(parts) - 1  # number of occurrences

    if count <= number_of_cache_controls:
        return conversation  # Nothing to remove

    # Join: keep the target only for the last n occurrences
    # The first (count - n) splits won't get the target re-inserted
    first_part = ''.join(parts[:count - number_of_cache_controls + 1])
    last_part = cache_control.join(parts[count - number_of_cache_controls + 1:])
    return json.loads(first_part + last_part)


def run_inference(conversation, llm_client, tools, consecutive_tool_count = 0, agent_name: str = "Claude", is_team_mode: bool = False,
                  max_consecutive_tools=10) -> tuple[dict, int]:
    """
    Runs inference using the LLM client with the provided conversation and tools.
    :param conversation:
    :param llm_client:
    :param tools:
    :param consecutive_tool_count:
    :param agent_name:
    :param is_team_mode:
    :param max_consecutive_tools:
    :return: The LLM response and the total token usage (excluding cached tokens!).
    """
    tools_param = []
    for t in tools:
        tools_param.append({
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema
        })

    tool_choice = {"type": "auto"}

    conversation = remove_all_but_last_three_cache_controls(conversation)

    response = llm_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=9999,
        system=get_system_prompt(agent_name, is_team_mode),  # Pass system prompt as a top-level parameter
        messages=conversation,
        tool_choice=tool_choice,
        tools=tools_param
    )

    if not response:
        raise ValueError("LLM response is empty. Please check your LLM client configuration.")

    total_token_usage = response.usage.input_tokens + response.usage.output_tokens

    # todo this is useful for testing but can/should be removed at some point
    print(f"\033[96mToken usage: {total_token_usage}\033[0m")


    # Return both the response and token usage (excluding cached tokens)
    return response.content, total_token_usage
