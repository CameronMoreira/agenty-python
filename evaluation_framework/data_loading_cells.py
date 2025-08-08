"""
Replacement cell content for evaluation_poc.ipynb
Use this to replace the data simulation cells with real data loading.

Replace cells 3-6 (approximately) with these contents:
"""

# CELL 3: Data Loading Function
real_data_loading_cell = '''
def load_and_format_real_data():
    """
    Load the real experimental data and format it for the evaluation framework.
    
    Returns:
        pd.DataFrame: Formatted dataframe compatible with the evaluation framework
    """
    print("📂 Loading real experimental data from survival scenario...")
    
    # Load the CSV data
    df_raw = pd.read_csv('evaluation_output/dataframe.csv')
    
    print(f"✅ Loaded {len(df_raw)} rows of real experimental data")
    print(f"📊 Raw data shape: {df_raw.shape}")
    
    # Create the formatted dataframe with expected column structure
    # The rest of the notebook expects: run_id, condition, round, agent_id, action_text
    df = pd.DataFrame({
        'run_id': df_raw['run_id'],
        'condition': df_raw['condition'], 
        'round': df_raw['step'],  # Map 'step' to 'round'
        'agent_id': df_raw['agent_id'],
        'action_text': df_raw['action_text']
    })
    
    # Filter out rows where action_text is empty or null
    initial_size = len(df)
    df = df.dropna(subset=['action_text'])
    df = df[df['action_text'].str.strip() != '']
    print(f"🧹 Filtered out {initial_size - len(df)} empty action entries")
    
    # Map condition names to match expected format
    condition_mapping = {
        'single-agent': '1-AI Team',
        'multi-agent': 'Multi-AI Team'
    }
    df['condition'] = df['condition'].map(condition_mapping)
    
    # Remove any unmapped conditions
    df = df.dropna(subset=['condition'])
    
    print(f"\\n📈 Final dataset summary:")
    print(f"  • Total actions: {len(df)}")
    print(f"  • Conditions: {df['condition'].unique()}")
    print(f"  • Actions per condition: {df['condition'].value_counts().to_dict()}")
    print(f"  • Unique agents: {df['agent_id'].nunique()}")
    print(f"  • Rounds covered: {df['round'].min()}-{df['round'].max()}")
    print(f"  • Runs per condition: {df.groupby('condition')['run_id'].nunique().to_dict()}")
    
    return df

print("✅ Real data loading function defined!")
'''

# CELL 4: Load the actual data
data_loading_execution_cell = '''
# Load the real experimental data
print("🏝️ Loading Real Survival Scenario Data...")
print("  • Reading actual agent actions from survival experiments")
print("  • Processing single-agent vs multi-agent conditions")
print("  • Preparing data for behavioral analysis")

df = load_and_format_real_data()

print(f"\\n✅ Real data loaded successfully!")
print(f"📊 Data shape: {df.shape}")
print(f"🤖 Conditions: {df['condition'].unique()}")
print(f"🔄 Runs per condition: {df.groupby('condition')['run_id'].nunique().to_dict()}")
print(f"📈 Actions per condition: {df['condition'].value_counts().to_dict()}")

# Display sample of real data
print("\\n📋 Sample of real experimental data:")
sample_df = df[['condition', 'round', 'agent_id', 'action_text']].head(8)
for idx, row in sample_df.iterrows():
    print(f"  [{row['condition']}] Round {row['round']} | {row['agent_id']}: {row['action_text'][:80]}...")
'''

print("Cell replacement content created!")
print("\nTo update your notebook:")
print("1. Delete cells 3-6 (all the simulation code)")
print("2. Add these two new cells in their place")
print("3. The rest of the notebook should work unchanged!")