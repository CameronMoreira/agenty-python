#!/usr/bin/env python3
import datetime
import time
import traceback

import util
from agent_work_log import send_work_log
from context_handling import (set_conversation_context, load_conversation,
                              get_all_from_message_queue, add_to_message_queue)
from llm import run_inference
from tools_utils import get_tool_list, execute_tool, deal_with_tool_results
from util import get_new_messages_from_group_chat, get_new_summaries, log_error, \
    generate_restart_summary, save_conv_and_restart, register_agent, propagate_action_to_external_systems


def get_new_message(is_team_mode: bool, consecutive_tool_count: list, read_user_input: bool) -> dict | None:
    # check message queue for new messages
    messages: list[str] = get_all_from_message_queue()

    if len(messages) > 0:
        consecutive_tool_count[0] = 0
        all_messages: str = ""
        for message in messages:
            all_messages += message + "\n"
        return {"role": "user", "content": all_messages}

    return {"role": "user", "content": "[Automated Message] There are currently no new messages. Please wait."}


class Agent:
    def __init__(self, agent_name: str, llm_client, team_mode: bool, base_url: str, agent_index = 1, turn_delay=0):
        self.llm_client = llm_client
        self.tools = get_tool_list(team_mode)
        self.is_team_mode = team_mode
        self.base_url = base_url
        self.agent_index = agent_index
        self.read_user_input = not team_mode  # initialise to True if not in team mode
        # Initialize counter for tracking consecutive tool calls without human interaction
        self.consecutive_tool_count = 0
        self.group_chat_messages = []
        self.last_logged_index = 0  # Last index of the group chat messages that were logged
        self.last_log_time = datetime.datetime.utcnow().isoformat()  # Last time a log was sent
        self.turn_delay = turn_delay

        self.name = agent_name

        # For work log tracking
        self.steps_since_last_log = 0
        self.log_every_n_steps = 10  # Default: Send log every 10 steps

        self.token_limit: int = 50_000

    def check_and_send_work_log(self, conversation):
        """Checks if a work log should be sent and sends it if necessary."""
        if self.steps_since_last_log >= self.log_every_n_steps:
            # Check if there are new messages since the last log
            new_messages = conversation[self.last_logged_index:]
            first_timestamp = self.last_log_time
            last_timestamp = datetime.datetime.utcnow().isoformat()
            success = send_work_log(self.name, new_messages, first_timestamp, last_timestamp)
            if success:
                self.steps_since_last_log = 0
                self.last_logged_index = len(conversation)
                self.last_log_time = last_timestamp

    def check_group_messages(self):
        """Checks for new group chat messages and adds them to the message queue.
        If there are no new messages, nothing happens.
        """
        new_messages = get_new_messages_from_group_chat(self.group_chat_messages)
        self.group_chat_messages.extend(new_messages)
        # Add new messages to the queue
        for message in new_messages:
            formatted_message = f"[Group Chat] {message['username']}: {message['message']}"
            add_to_message_queue(formatted_message)

    def check_new_summaries(self):
        """Checks for new summaries from the summary monitor and adds them to the message queue.
        If there are no new summaries, nothing happens.
        """
        try:
            new_summaries = get_new_summaries()
            if new_summaries:
                for summary in new_summaries:
                    formatted_summary = f"[Summary Monitor] Here is a summary from the group work log: {summary['summary']}"
                    add_to_message_queue(formatted_summary)
        except Exception as e:
            # Log the error but don't crash the agent
            error_msg = f"Error checking new summaries: {str(e)}\n{traceback.format_exc()}"
            log_error(error_msg)

    def run(self):
        # register with the robot's external systems
        register_agent(self.name, self.agent_index)

        # Try to load saved conversation context
        conversation = load_conversation()

        if conversation:
            print("Restored previous conversation context")
            # If we're continuing after a restart, add a system message to inform the agent
            conversation.append({
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": "The program has restarted and is continuing execution automatically. Please continue from where you left off.",
                    "cache_control": {"type": "ephemeral"}
                }]
            })
            self.read_user_input = False
        else:
            conversation = []

        # Set the global conversation context reference
        set_conversation_context(conversation)

        # main agent loop; every loop is one "step"
        while True:
            # Wait for external systems to respond before proceeding to the next step
            while not util.RECEIVED_EXTERNAL_SYSTEMS_RESPONSE:
                time.sleep(1)

            util.RECEIVED_EXTERNAL_SYSTEMS_RESPONSE = False  # reset for the next round

            if self.is_team_mode:
                self.check_group_messages()

            tool_count_object = [self.consecutive_tool_count]
            message = get_new_message(self.is_team_mode, tool_count_object, self.read_user_input)
            self.consecutive_tool_count = tool_count_object[0]
            if message is not None:
                conversation.append(message)

            response_content, token_usage = run_inference(conversation, self.llm_client, self.tools,
                                                          self.consecutive_tool_count,
                                                          self.name, self.is_team_mode)
            tool_results = []

            action_type: str = "nothing"
            action: str = "nothing"

            # print assistant text and collect any tool calls
            for block in response_content:
                if block.type == "text":
                    print(f"\033[93m{self.name}\033[0m: {block.text}")
                    action = f"internal thought: {block.text}"
                    action_type = "internal thought"
                elif block.type == "tool_use":
                    tool_name = block.name
                    action_type = f"tool call: {tool_name}"
                    action = f"tool call: {tool_name} with input {block.input}"
                    # If the tool call is the "take action" tool, we deal with it separately
                    if tool_name == "take_action":
                        action_type = "action"
                        action = block.input["action"]

                    print(f"\033[93m{self.name}\033[0m: Tool call: {tool_name} with input {block.input}")

                    result = execute_tool(self.tools, tool_name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # 2) First, append the assistant's own message (including its tool_use blocks!)
            conversation.append({
                "role": "assistant",
                "content": [
                    # for each block LLM returned, mirror it exactly
                    {
                        "type": b.type,
                        **({
                               "text": b.text
                           } if b.type == "text" else {
                            "id": b.id,
                            "name": b.name,
                            "input": b.input
                        }),
                        "cache_control": {"type": "ephemeral"}
                    }
                    for b in response_content
                ]
            })

            # 3) If there were any tool calls, follow up with tool_results as a user turn
            if tool_results:
                self.read_user_input = False
                deal_with_tool_results(tool_results, conversation)
            else:
                self.read_user_input = False  # we do not want to read user input ever

            # Count a step
            # self.steps_since_last_log += 1

            # Check if a work log should be sent
            # self.check_and_send_work_log(conversation)

            propagate_action_to_external_systems(self.name, action_type, action)

            # Check if we need to restart due to token limit
            if token_usage >= self.token_limit:
                print(f"\033[91mToken limit reached ({token_usage:,}/{self.token_limit:,}). Restarting...\033[0m")
                generate_restart_summary(self.llm_client, conversation,
                                         self.tools)  # this also adds the summary to the conversation
                # filter conversation to keep only the last message
                conversation = conversation[-1:]
                set_conversation_context(conversation)

                # Save the conversation context and restart
                save_conv_and_restart(conversation)

            # delay the next turn if configured to prevent running into rate limits
            if self.turn_delay > 0:
                time.sleep(self.turn_delay / 1000)
