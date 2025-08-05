import json, argparse, os, pandas as pd

def create_evaluation_dataframe(log_file, out_csv):
    """
    Processes a raw evaluation log file to create a structured and cleaned-up
    DataFrame for analysis. It unpacks JSON data into readable formats.
    """
    with open(log_file) as f:
        logs = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Warning: Skipping malformed JSON line: {line}")
                continue

    # --- First pass: index world states and events by step ---
    world_states_by_step = {}
    events_by_step = {}
    for row in logs:
        log_type = row.get("log_type")
        # Handle cases where payload might be a string (e.g. from older logs)
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            continue

        step = row.get("step") or payload.get("step")
        if step is None:
            continue

        if log_type == "general_state_narrated" and "world_state" in payload:
            world_states_by_step[step] = payload["world_state"]
        elif log_type == "scripted_events_triggered" and "scripted_events" in payload:
            events_by_step.setdefault(step, []).extend(payload["scripted_events"])

    # --- Second pass: build DataFrame records ---
    records = []
    latest_world_state = None
    for row in logs:
        # If the current row is a world state update, cache it for subsequent rows
        if row.get("log_type") == "general_state_narrated":
            if isinstance(row.get("payload"), dict):
                latest_world_state = row["payload"].get("world_state")
            continue  # Don't add world state rows directly to the DataFrame

        # We only want to create rows for agent actions (thoughts or tool calls)
        if not (row.get("source") == "agent" and row.get("log_type") in ("assistant_message", "tool_call")):
            continue

        step = row.get("step")
        agent_name = row.get("agent_name")

        # Use the world state from the current step, or the last known one as a fallback
        current_world_state = world_states_by_step.get(step, latest_world_state)

        agent_state = None
        if current_world_state and "agents" in current_world_state:
            agent_state = current_world_state["agents"].get(agent_name)

        # --- Format action_text and tool_name ---
        log_type = row["log_type"]
        payload = row.get("payload", {})
        action_text = ""
        tool_name = None
        if log_type == "assistant_message":
            action_text = payload.get("text", "")
        elif log_type == "tool_call":
            tool_name = payload.get("tool_name")
            tool_input = payload.get("tool_input", {})
            if tool_name == 'send_group_message':
                action_text = tool_input.get('message', str(tool_input))
            elif tool_name == 'take_action':
                action_text = tool_input.get('action', str(tool_input))
            else:
                action_text = f"TOOL: {tool_name}({json.dumps(tool_input)})"

        # --- Format agent_damage ---
        agent_damage_str = None
        if agent_state:
            damages = agent_state.get("damages_to_robotic_body")
            if isinstance(damages, dict):
                agent_damage_str = ", ".join([f"{k}: {v}" for k, v in damages.items()])
            elif damages:
                 agent_damage_str = str(damages)


        # --- Format events_this_step ---
        events_str = None
        events_for_step = events_by_step.get(step)
        if isinstance(events_for_step, list):
            event_names = [event.get('name', 'Unknown Event') for event in events_for_step]
            events_str = "; ".join(event_names)

        records.append({
            "run_id": row.get("run_id"),
            "conversation_id": row.get("conversation_id"),
            "condition": row.get("run_condition"),
            "step": step,
            "agent_id": agent_name,
            "log_type": log_type,
            "action_text": action_text.strip(),
            "tool_name": tool_name,
            "agent_location": agent_state.get("current_location") if agent_state else None,
            "agent_battery": agent_state.get("battery_life") if agent_state else None,
            "agent_damage": agent_damage_str,
            "events_this_step": events_str,
            "full_world_state": json.dumps(current_world_state) if current_world_state else None,
        })

    if not records:
        print("Warning: No agent action records were found to create a DataFrame.")
        return

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"✅ DataFrame written to {out_csv} ({len(df)} rows)")