#!/usr/bin/env python3
"""
Data loading script to replace simulation in evaluation_poc.ipynb
This replaces all the simulation code with real data loading.
"""

import pandas as pd
import numpy as np

def load_real_data():
    """
    Load the real experimental data and format it for the evaluation framework.
    
    Returns:
        pd.DataFrame: Formatted dataframe compatible with the evaluation framework
    """
    print("📂 Loading real experimental data...")
    
    # Load the CSV data
    df = pd.read_csv('../evaluation_output/dataframe.csv')
    
    print(f"✅ Loaded {len(df)} rows of real experimental data")
    print(f"📊 Data shape: {df.shape}")
    
    # Map to expected column structure for compatibility with existing analysis
    # The rest of the notebook expects: run_id, condition, round, agent_id, action_text
    
    # Create the formatted dataframe
    formatted_df = pd.DataFrame({
        'run_id': df['run_id'],
        'condition': df['condition'], 
        'round': df['step'],  # Map 'step' to 'round'
        'agent_id': df['agent_id'],
        'action_text': df['action_text']
    })
    
    # Filter out rows where action_text is empty or null
    initial_size = len(formatted_df)
    formatted_df = formatted_df.dropna(subset=['action_text'])
    formatted_df = formatted_df[formatted_df['action_text'].str.strip() != '']
    print(f"🧹 Filtered out {initial_size - len(formatted_df)} empty action entries")
    
    # Map condition names to match expected format
    condition_mapping = {
        'single-agent': '1-AI Team',
        'multi-agent': 'Multi-AI Team'
    }
    formatted_df['condition'] = formatted_df['condition'].map(condition_mapping)
    
    print(f"\n📈 Final dataset summary:")
    print(f"  • Total actions: {len(formatted_df)}")
    print(f"  • Conditions: {formatted_df['condition'].unique()}")
    print(f"  • Actions per condition: {formatted_df['condition'].value_counts().to_dict()}")
    print(f"  • Unique agents: {formatted_df['agent_id'].nunique()}")
    print(f"  • Rounds covered: {formatted_df['round'].min()}-{formatted_df['round'].max()}")
    print(f"  • Runs per condition: {formatted_df.groupby('condition')['run_id'].nunique().to_dict()}")
    
    # Show sample data
    print(f"\n📋 Sample of real data:")
    sample_df = formatted_df[['condition', 'round', 'agent_id', 'action_text']].head(5)
    for idx, row in sample_df.iterrows():
        print(f"  [{row['condition']}] Round {row['round']} | {row['agent_id']}: {row['action_text'][:80]}...")
    
    return formatted_df

if __name__ == "__main__":
    # Test the data loading
    df = load_real_data()
    print(f"\n✅ Real data loading successful! Shape: {df.shape}")