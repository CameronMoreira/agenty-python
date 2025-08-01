
import datetime
import os
import sys
from unittest.mock import MagicMock

# Add agent directory to sys.path
agent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'agent'))
sys.path.insert(0, agent_dir)

# Set a dummy API key to avoid errors
os.environ["ANTHROPIC_API_KEY"] = "DUMMY_KEY"
os.environ["EVALUATION_LOG_URL"] = "http://localhost:8083"

from base_agent import Agent

def main():
    print("Testing agent logging...")

    # Mock the LLM client
    mock_llm_client = MagicMock()

    # Instantiate the agent
    agent = Agent(
        agent_name="TestAgent",
        llm_client=mock_llm_client,
        team_mode=False,
        base_url="http://localhost:8000"
    )

    # Directly call the logging function to test it
    conversation = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    agent.steps_since_last_eval_log = agent.eval_log_every_n_steps  # Trigger logging
    success = agent.check_and_send_evaluation_log(conversation)
    print(f"Log event sent successfully: {success}")

    print("Agent logging test finished.")

if __name__ == "__main__":
    main()
