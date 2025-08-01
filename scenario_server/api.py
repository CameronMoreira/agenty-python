import threading

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from scenario_server_base import REGISTERED_AGENTS, AgentAction, actions_this_turn, Agent

app = FastAPI()


class RegisterAgentRequest(BaseModel):
    agent: str
    agent_index: int


@app.post("/register")
def register_agent(request: RegisterAgentRequest):  # agents need to call this on their startup
    agent_name = request.agent
    if agent_name in REGISTERED_AGENTS:
        raise HTTPException(status_code=400, detail="Agent already registered")
    agent_base_url = f"http://agents-agent-{request.agent_index}:8000"
    REGISTERED_AGENTS[agent_name] = Agent(name=request.agent, base_url=agent_base_url)
    print(f"\033[92mAgent '{agent_name}' registered successfully at {agent_base_url}\033[0m")
    return {"Registration successful"}


@app.post("/action")
async def post_action(action: AgentAction):
    actions_this_turn.append(action)  # store the action for processing during main loop
    return {"Processing action..."}


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
