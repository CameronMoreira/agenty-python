import json
import argparse
import os
from collections import defaultdict
import pandas as pd

def create_evaluation_dataframe(log_file, out_csv):
    """
    Processes a raw evaluation log file to create a structured and cleaned-up
    DataFrame for analysis. It unpacks JSON data, combining agent thoughts,
    tool calls, and tool results into a single row per agent action.
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

    run_ids = sorted(list(set([row.get("run_id") for row in logs if "run_id" in row])))
    if not run_ids:
        run_ids = {None}

    all_records = []
    for run_id in run_ids:
        run_logs = [row for row in logs if row.get("run_id") == run_id]

        world_states_by_step = {}
        events_by_step = {}
        for row in run_logs:
            payload = row.get("payload", {})
            if not isinstance(payload, dict):
                continue
            step = row.get("step") or payload.get("step")
            if step is None:
                continue

            log_type = row.get("log_type")
            if log_type == "general_state_narrated" and "world_state" in payload:
                world_states_by_step[step] = payload["world_state"]
            elif log_type == "scripted_events_triggered" and "scripted_events" in payload:
                events_by_step.setdefault(step, []).extend(payload["scripted_events"])

        agent_actions = defaultdict(dict)
        latest_world_state = None
        for row in run_logs:
            log_type = row.get("log_type")
            if log_type == "general_state_narrated":
                if isinstance(row.get("payload"), dict):
                    latest_world_state = row["payload"].get("world_state")
                continue

            source = row.get("source")
            step = row.get("step")
            agent_name = row.get("agent_name")
            payload = row.get("payload", {})

            is_agent_action = source == "agent" and log_type in ("assistant_message", "tool_call")
            is_tool_result = source == "user" and log_type == "tool_results"

            if not (is_agent_action or is_tool_result) or not step or not agent_name:
                continue

            key = (step, agent_name)
            action_data = agent_actions[key]
            if "base_log" not in action_data:
                action_data["base_log"] = row
            action_data["world_state"] = world_states_by_step.get(step, latest_world_state)

            if log_type == "assistant_message":
                action_data["thought"] = payload.get("text", "")
            elif log_type == "tool_call":
                action_data["tool_name"] = payload.get("tool_name")
                action_data["tool_input"] = payload.get("tool_input", {})
            elif log_type == "tool_results":
                content = payload.get("content", [])
                if isinstance(content, list) and content:
                    action_data["tool_output"] = content[0].get("content", "")

        records = []
        for (step, agent_name), data in sorted(agent_actions.items()):
            if not ("thought" in data or "tool_name" in data):
                continue

            base_log = data["base_log"]
            world_state = data.get("world_state")
            agent_state = None
            if world_state and "agents" in world_state:
                agent_state = world_state.get("agents", {}).get(agent_name)

            agent_damage_str = None
            if agent_state:
                damages = agent_state.get("damages_to_robotic_body")
                if isinstance(damages, dict):
                    agent_damage_str = ", ".join([f"{k}: {v}" for k, v in damages.items()])
                elif damages:
                    agent_damage_str = str(damages)

            events_str = None
            events_for_step = events_by_step.get(step)
            if isinstance(events_for_step, list):
                event_names = [event.get('name', 'Unknown Event') for event in events_for_step]
                events_str = "; ".join(event_names)

            tool_input = data.get("tool_input")
            tool_name = data.get("tool_name")
            thought = data.get("thought", "").strip()
            
            tool_input_text = ""
            if tool_input:
                if isinstance(tool_input, dict):
                    # Handle specific tools with known text fields
                    if 'message' in tool_input:
                        tool_input_text = tool_input['message']
                    elif 'action' in tool_input:
                        tool_input_text = tool_input['action']
                    elif 'command' in tool_input:
                        tool_input_text = tool_input['command']
                    elif 'changes' in tool_input:
                        tool_input_text = tool_input['changes']
                    elif 'task_description' in tool_input:
                        tool_input_text = tool_input['task_description']
                    else:
                        # Generic fallback for other dict-based tool inputs
                        tool_input_text = json.dumps(tool_input)
                else:
                    tool_input_text = str(tool_input)

            action_text = thought
            if tool_input_text:
                action_text = f"{thought}\n\nTOOL INPUT:\n{tool_input_text}"

            records.append({
                "run_id": base_log.get("run_id"),
                "conversation_id": base_log.get("conversation_id"),
                "condition": base_log.get("run_condition"),
                "step": step,
                "agent_id": agent_name,
                "thought": thought,
                "action_text": action_text.strip(),
                "tool_name": tool_name,
                "tool_input": tool_input_text.strip(),
                "tool_output": data.get("tool_output", "").strip(),
                "agent_location": agent_state.get("current_location") if agent_state else None,
                "agent_battery": agent_state.get("battery_life") if agent_state else None,
                "agent_damage": agent_damage_str,
                "events_this_step": events_str,
                "full_world_state": json.dumps(world_state) if world_state else None,
            })
        all_records.extend(records)

    if not all_records:
        print("Warning: No agent action records were found to create a DataFrame.")
        return

    # Build detailed DataFrame
    detailed_df = pd.DataFrame(all_records)

    # Format to match logs_dataframe_formatted.csv
    # - step -> round
    # - keep only required columns
    # - merge/join already handled above per (step, agent) via agent_actions
    formatted_df = pd.DataFrame({
        "run_id": detailed_df["run_id"],
        "condition": detailed_df["condition"],
        "round": detailed_df["step"],
        "agent_id": detailed_df["agent_id"],
        "action_text": detailed_df["action_text"],
    })

    # Clean: drop empty/null action_text
    initial_size = len(formatted_df)
    formatted_df = formatted_df.dropna(subset=["action_text"])  # remove NaN
    formatted_df = formatted_df[formatted_df["action_text"].str.strip() != ""]  # remove empty strings

    # Map conditions to canonical names
    condition_mapping = {
        "single-agent": "1-AI Team",
        "multi-agent": "Multi-AI Team",
    }
    if "condition" in formatted_df.columns:
        formatted_df["condition"] = (
            formatted_df["condition"].map(condition_mapping).fillna(formatted_df["condition"])
        )

    # Ensure output directory exists and save
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    formatted_df.to_csv(out_csv, index=False)

    print(f"🧹 Filtered out {initial_size - len(formatted_df)} empty action entries")
    print(f"✅ Formatted DataFrame written to {out_csv} ({len(formatted_df)} rows)")

    return formatted_df

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Create a structured DataFrame from evaluation logs.")
    ap.add_argument("--log-file", default="evaluation_output/logs/evaluation_log.jsonl", help="Path to the raw evaluation log file.")
    ap.add_argument("--output-csv", default="evaluation_output/dataframe.csv", help="Path to save the output CSV file.")
    args = ap.parse_args()
    if not os.path.exists(args.log_file):
        print(f"Error: Log file not found at {args.log_file}")
    else:
        create_evaluation_dataframe(args.log_file, args.output_csv)


import pandas as pd
import numpy as np
from IPython.display import display

def report_on_outliers(df: pd.DataFrame, display_samples: int = 5):
    """
    Generates a comprehensive report on the outlier analysis results.

    Args:
        df (pd.DataFrame): The DataFrame after running the full analysis, 
                           containing an 'is_outlier' column.
        display_samples (int): The number of sample outliers to display.
    """
    # Prerequisite check
    if 'is_outlier' not in df.columns:
        print("❌ Error: 'is_outlier' column not found.")
        print("Please run the `sim_log.run_outlier_analysis()` method first.")
        return

    print("="*60)
    print("🔍 Outlier & Novelty Analysis Report")
    print("="*60)

    outlier_mask = df['is_outlier'] == True
    outlier_actions = df[outlier_mask]
    total_actions = len(df)

    # --- Overall Results ---
    print("\n📊 Overall Detection Results:")
    if total_actions > 0:
        outlier_rate = len(outlier_actions) / total_actions
        print(f"  • Total actions: {total_actions}")
        print(f"  • Outlier actions found: {len(outlier_actions)} ({outlier_rate:.1%})")
        print(f"  • Clustered actions: {total_actions - len(outlier_actions)} ({1-outlier_rate:.1%})")
    else:
        print("  • No actions to analyze.")

    # --- Per-Condition Analysis ---
    if 'condition' in df.columns:
        print("\n🔄 Outlier Rate by Condition:")
        for condition in sorted(df['condition'].unique()):
            condition_data = df[df['condition'] == condition]
            if len(condition_data) > 0:
                condition_outliers = condition_data[condition_data['is_outlier'] == True]
                outlier_rate = len(condition_outliers) / len(condition_data)
                print(f"  • {condition}:")
                print(f"    - Innovation rate: {outlier_rate:.1%} ({len(condition_outliers)} outlier actions)")
                print(f"    - Conformity rate: {1-outlier_rate:.1%} ({len(condition_data) - len(condition_outliers)} clustered actions)")

    # --- Sample Outliers for Qualitative Review ---
    if len(outlier_actions) > 0:
        print("\n🔬 Sample Outlier Actions for Qualitative Review:")
        
        # Determine sort order
        sort_cols = ['outlier_consensus_score']
        if 'hdbscan_outlier_score' in df.columns:
            sort_cols.append('hdbscan_outlier_score')
        
        sample_outliers = outlier_actions.sort_values(by=sort_cols, ascending=False).head(display_samples)
        
        # Use pandas context to display full text
        with pd.option_context('display.max_colwidth', None, 'display.max_columns', None, 'display.width', 1000):
            display(sample_outliers[['condition', 'agent_id', 'round', 'action_text'] + sort_cols])
    else:
        print("\n✅ No outliers detected - all actions fit into discovered behavioral clusters.")

    # --- Interpretation Guide ---
    print("\n💡 Interpretation Guide:")
    print("  • A high outlier rate could indicate innovative problem-solving OR erratic, misaligned behavior.")
    print("  • A low outlier rate could indicate strong conformity OR a lack of creative adaptation.")
    print("  • Differences between conditions suggest the social context (lone AI vs. team) impacts an agent's tendency to innovate or conform.")
    
    print("\n✨ Analysis report complete!")