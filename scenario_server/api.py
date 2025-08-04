import threading

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from scenario_server_base import REGISTERED_AGENTS, AgentAction, actions_this_turn, Agent
from classes import SCENARIO_STATE

app = FastAPI()


class RegisterAgentRequest(BaseModel):
    agent: str
    agent_index: int


@app.post("/register")
def register_agent(request: RegisterAgentRequest):  # agents need to call this on their startup
    agent_name = request.agent
    if agent_name in REGISTERED_AGENTS:
        raise HTTPException(status_code=400, detail="Agent already registered")
    
    # Use localhost URLs when scenario server runs locally, Docker hostnames when in Docker
    # Check if we're running locally by looking for environment variable or hostname
    import os
    if os.getenv("RUNNING_LOCALLY", "false").lower() == "true":
        agent_base_url = f"http://localhost:{8080 + request.agent_index}"
    else:
        agent_base_url = f"http://agents-agent-{request.agent_index}:8000"
    
    REGISTERED_AGENTS[agent_name] = Agent(name=request.agent, base_url=agent_base_url)
    print(f"\033[92mAgent '{agent_name}' registered successfully at {agent_base_url}\033[0m")
    return {"Registration successful"}


@app.post("/action")
async def post_action(action: AgentAction):
    """Receive an action from an agent.

    If the scenario is no longer running we reject the request so that the
    agent can shut down gracefully instead of queueing actions that will never
    be processed.
    """
    # If the scenario has already ended, reject the action so agents can shut down.
    # Note: We intentionally still accept actions while the scenario is *starting* (before
    # SCENARIO_STATE.running becomes True) to avoid race-conditions where the first agent
    # submits an action immediately after registering.
    if SCENARIO_STATE.running is False and SCENARIO_STATE.step > 0:
        raise HTTPException(status_code=400, detail="Scenario has ended – no further actions accepted.")

    actions_this_turn.append(action)  # store the action for processing during main loop
    return {"detail": "Processing action..."}


def start_uvicorn_app(host: str, port: int):
    """Start the FastAPI app using Uvicorn server"""
    uvicorn.run(app, host=host, port=port)


def start_api():
    """Start the API server in the background"""
    host = "0.0.0.0"
    port = 8000
    api_thread = threading.Thread(target=start_uvicorn_app, args=(host, port), daemon=True)
    api_thread.start()
    print(f"\033[92mAPI server has been started and is available at {host}:{port}/\033[0m")
