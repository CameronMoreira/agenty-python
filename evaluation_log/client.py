#!/usr/bin/env python3
import os
from typing import Dict, Any

import requests

EVALUATION_LOG_URL = os.environ.get("EVALUATION_LOG_URL", "http://localhost:8002")


def log_error(message: str):
    """Logs an error message to a file."""
    with open("error.txt", "a") as f:
        f.write(f"[{__name__}] {message}\n")


def log_event(source: str, log_type: str, payload: Dict[str, Any], agent_name: str = None,
              metadata: Dict[str, Any] = None, conversation_id: str = None, turn_id: int = None,
              run_condition: str = None):
    """Sends a structured event to the evaluation log service."""
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        response = requests.post(
            f"{EVALUATION_LOG_URL}/log-event",
            json={
                "source": source,
                "log_type": log_type,
                "timestamp": timestamp,
                "agent_name": agent_name,
                "payload": payload,
                "metadata": metadata,
                "conversation_id": conversation_id,
                "turn_id": turn_id,
                "run_condition": run_condition,
            },
            timeout=5
        )
        if response.status_code == 200:
            return True
        else:
            error_message = f"Failed to send evaluation event. Status code: {response.status_code}, Response: {response.text}"
            log_error(error_message)
            return False
    except requests.exceptions.RequestException as e:
        error_message = f"Error sending evaluation event: {e}"
        log_error(error_message)
        return False
