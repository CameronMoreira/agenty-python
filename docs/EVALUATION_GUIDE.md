# Agent and Evaluation Logging Development Guide

This guide provides instructions for running, testing, and interacting with the multi-agent system, with a focus on the new development workflow and evaluation logging system.

## Key Architectural Changes

The development environment has been improved to support a faster, more interactive feedback loop. The key changes are:

2.  **Development Mode (`DEV_MODE`)**: An environment variable that disables blocking logic, allowing developers to interact with agents directly without the `scenario_server`.
3.  **Team Mode (`TEAM_MODE`)**: An environment variable that toggles whether agents participate in group chat.
4.  **Silent Wait (`silentWait`)**: A per-agent configuration flag in `team-config.json` that controls whether an agent sends "I'm waiting" messages or waits silently.
5.  **Direct Port Access**: Agents running in Docker now expose their ports to the host machine, allowing for direct API calls for testing.

## Running the System

### Prerequisites

-   Docker and Docker Compose
-   An `.env` file in the project root with your `ANTHROPIC_API_KEY`.

### Deployment

To build and run the entire agent team, use the deployment script:

```bash
./scripts/deploy_agent_team.sh
```

This will start all services defined in `docker-compose.yaml`, including two agents and the group chat service.

## Development and Testing Workflow

The new flags provide a highly flexible environment for testing.

### How to Test a Single Agent in Isolation

This is the recommended workflow for developing a single agent's logic or testing the evaluation logging.

1.  **Configure `docker-compose.yaml`**:
    -   Set `DEV_MODE: "true"`
    -   Set `TEAM_MODE: "false"`

2.  **Configure `team-config.json`**:
    -   For the agent you are testing, set `"silentWait": true`. This will prevent it from getting stuck in a self-messaging loop.

3.  **Deploy and Interact**:
    -   Run `./scripts/deploy_agent_team.sh`.
    -   Find the agent's assigned host port by running `docker compose ps`.
    -   Use the **Insomnia Collection** (`insomnia_collection.json`) to send direct messages to the agent on its assigned port (e.g., `http://localhost:8088/send-message`).
    -   **Alternatively, use `curl` to send a direct message without Insomnia:**
        ```bash
        curl -X POST http://localhost:8088/send-message \
            -H "Content-Type: application/json" \
            -d '{"from_agent": "human_tester", "message": "This is a direct message for testing."}'
        ```
        - Replace `8088` with the actual port assigned to your agent (see `docker compose ps`).
        - The `from_agent` field can be any identifier for the sender.
        - The `message` field is the content you want to send to the agent.


### How to Test Multi-Agent Collaboration

To see the agents interact with each other:

1.  **Configure `docker-compose.yaml`**:
    -   Set `DEV_MODE: "true"`
    -   Set `TEAM_MODE: "true"`

2.  **Deploy and Observe**:
    -   Run `./scripts/deploy_agent_team.sh`.
    -   Watch the agents' conversational loop by following their logs:
        ```bash
        docker logs agents-agent-1 --follow
        docker logs agents-agent-2 --follow
        ```

## Evaluation Logging

The new logging system is simple, file-based, and records rich, structured information for each event.

-   **Log Location**: All structured evaluation logs are written to `evaluation_output/logs/evaluation_log.jsonl`.
-   **Format**: The log is a [JSONL file](https://jsonlines.org/), where each line is a separate JSON object representing a logged event.
-   **What Gets Logged**: Each log entry includes the following fields:
    - `source`: The component or module that generated the event (e.g., `"agent"`, `"group_chat"`).
    - `log_type`: The type of event (e.g., `"user_message"`, `"tool_call"`, `"assistant_message"`).
    - `timestamp`: The UTC timestamp when the event was logged, in ISO 8601 format.
    - `agent_name`: The name of the agent involved in the event (if applicable).
    - `payload`: The main content or data for the event (such as the message text, tool call details, etc.).
    - `metadata`: Any additional metadata relevant to the event (optional).
    - `conversation_id`: An identifier for the conversation (if available).
    - `turn_id`: The turn number within the conversation (if available).
    - `run_condition`: The current run condition or context for the event (if applicable).
-   **Persistence**: The log directory is mounted as a Docker volume, so the logs are persisted on your host machine and will not be lost when containers are removed.

**Example log entry:**

## Interacting with the APIs

The easiest way to interact with the system is to import the `insomnia_collection.json` file into Insomnia (or Postman, etc.).

The collection includes pre-configured requests for:
-   Sending and retrieving messages from the `group_chat` service (only when activated via TEAM_MODE).
-   Sending direct messages to a specific agent for testing.
-   Interacting with the `scenario_server` (when it is running) (not working yet).
