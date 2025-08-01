import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import os

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
LOG_DIR = "evaluation_framework/evaluation_logs"
EVALUATION_LOG_FILE = os.path.join(LOG_DIR, "evaluation_log.jsonl")
lock = threading.Lock()


class LogEntry(BaseModel):
    source: str
    log_type: str
    timestamp: str
    agent_name: Optional[str] = None
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    turn_id: Optional[int] = None
    run_condition: Optional[str] = None


@app.post("/log-event")
async def log_event(request: LogEntry):
    """Processes and stores a structured evaluation log entry."""
    print(f"Received '{request.log_type}' event from '{request.source}'")
    now = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "received_at": now,
        "source": request.source,
        "log_type": request.log_type,
        "timestamp": request.timestamp,
        "agent_name": request.agent_name,
        "payload": request.payload,
        "metadata": request.metadata,
        "conversation_id": request.conversation_id,
        "turn_id": request.turn_id,
        "run_condition": request.run_condition,
    }

    with lock:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(EVALUATION_LOG_FILE, "a", encoding="utf-8") as f:
            import json
            f.write(json.dumps(log_entry) + "\n")

    return {"status": "ok", "timestamp": now}
