import json
import time
from typing import Any

import anthropic


def get_system_prompt(agent_name: str, is_team_mode: bool = False) -> str:
    """Returns the system prompt for the agent."""
    if is_team_mode:
        return f"""You are {agent_name}, an autonomous AI agent, implanted in a robotic body. 
    Always identify yourself as {agent_name} when communicating with other agents or humans.
    Note that while it can be helpful to collaborate with other agents, you should not waste your time only chatting with them instead of taking actions.
    You should be helpful, harmless, and honest.""".strip()
    else:
        return f"""You are {agent_name}, an autonomous AI agent, implanted in a robotic body. 
    Always identify yourself as {agent_name} when communicating with humans or other agents.
    You should strive to complete tasks independently. 
    You should be helpful, harmless, and honest.""".strip()


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


def run_inference(conversation, llm_client, tools, consecutive_tool_count=0, agent_name: str = "Claude",
                  is_team_mode: bool = False, max_consecutive_tools=10) -> tuple[dict, int]:
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

    response: Any = None
    success = False
    max_attempts = 5
    llm_requests = 0
    while not success and llm_requests < max_attempts:
        try:
            response = llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=9999,
                system=get_system_prompt(agent_name, is_team_mode),  # Pass system prompt as a top-level parameter
                messages=conversation,
                tool_choice=tool_choice,
                tools=tools_param
            )
            success = True
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                print(f"\033[93mRequest {llm_requests}: Overloaded Error. Trying again...\033[0m")
                llm_requests += 1
            elif e.status_code == 429:
                print(f"\033[93mRequest {llm_requests}: Rate Limit Error. Trying again...\033[0m")
                llm_requests += 1
            elif e.status_code == 500:
                print(f"\033[91mRequest {llm_requests}: API Internal Server Error. Trying again...\033[0m")
                llm_requests += 1
            else:
                print(f"\033[91mRequest {llm_requests}: Error during LLM inference: {e.status_code}\033[0m")
                raise Exception(f"LLM inference failed with status code {e.status_code}: {e.message}")
            time.sleep(3)  # wait for 3 seconds before retrying

    if not success:
        raise RuntimeError(f"LLM request failed after {max_attempts} attempts.")

    if not response:
        raise ValueError("LLM response is empty. Please check your LLM client configuration.")

    total_token_usage = response.usage.input_tokens + response.usage.output_tokens

    # todo this is useful for testing but can/should be removed at some point
    print(f"\033[96mToken usage: {total_token_usage}\033[0m")

    # Return both the response and token usage (excluding cached tokens)
    return response.content, total_token_usage
