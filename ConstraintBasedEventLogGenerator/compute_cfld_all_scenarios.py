"""
Script to compute CFLD (Conformance Checking based on Frequencies of Labeled Directly-follows Relations)
between generated simulation logs and their corresponding filtered test logs.

For each scenario in simulations folder, this script:
1. Loads all simulation CSV files (sim_0.csv through sim_9.csv) from the scenario
2. Loads the corresponding filtered test log (filtered_test_logs/{case_study}/test_log_{exp}.xes)
3. Computes CFLD between the generated log and the filtered test log
4. Saves results progressively in a CSV table

CFLD measures the similarity between two event logs based on their directly-follows relations frequencies.
"""

import pandas as pd
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog
from collections import defaultdict
import os
import glob
import warnings
from tqdm import tqdm

warnings.filterwarnings('ignore')


def normalize_activity_names(log: EventLog) -> EventLog:
    """
    Normalize activity names to keep only complete events.
    Filters out start events and keeps only complete events for directly-follows analysis.
    
    Args:
        log: EventLog object
    
    Returns:
        EventLog with only complete events
    """
    from pm4py.objects.log.obj import EventLog, Trace
    
    normalized_log = EventLog()
    
    for trace in log:
        normalized_trace = Trace()
        
        # Copy trace attributes properly
        for attr_key, attr_value in trace.attributes.items():
            normalized_trace.attributes[attr_key] = attr_value
        
        for event in trace:
            activity_name = event.get('concept:name', '')
            
            # Check if activity has lifecycle suffix
            if '_lc:start' in activity_name:
                continue  # Skip start events
            elif '_lc:complete' in activity_name:
                # Keep complete events
                normalized_trace.append(event)
            else:
                # No lifecycle suffix, assume it's a complete event
                normalized_trace.append(event)
        
        if len(normalized_trace) > 0:
            normalized_log.append(normalized_trace)
    
    return normalized_log


def load_scenario_logs(scenario_path: str) -> EventLog:
    """
    Load all simulation CSV files from a scenario directory and combine them into one event log.
    Normalizes to only complete events with consistent naming.
    
    Args:
        scenario_path: Path to scenario directory (e.g., 'simulations/Purchasing exp1/scenarioA')
    
    Returns:
        Combined EventLog from all sim_*.csv files (only complete events)
    """
    csv_files = sorted(glob.glob(os.path.join(scenario_path, 'sim_*.csv')))
    
    if not csv_files:
        raise ValueError(f"No simulation CSV files found in {scenario_path}")
    
    # Load and combine all CSV files
    dfs = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        df['time:timestamp'] = pd.to_datetime(df['time:timestamp'], format='mixed')
        
        # Convert case ID to string (required by pm4py)
        if 'case:concept:name' in df.columns:
            df['case:concept:name'] = df['case:concept:name'].astype(str)
        
        # Filter only 'complete' lifecycle transitions and add lifecycle suffix to activity name
        if 'lifecycle:transition' in df.columns:
            df = df[df['lifecycle:transition'] == 'complete'].copy()
            # Add lifecycle suffix to match filtered test log format
            df['concept:name'] = df['concept:name'] + '_lc:complete'
        
        dfs.append(df)
    
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Sort by case and timestamp to ensure correct ordering
    combined_df = combined_df.sort_values(['case:concept:name', 'time:timestamp']).reset_index(drop=True)
    
    # Convert to event log
    event_log = pm4py.convert_to_event_log(combined_df)
    
    return event_log


def load_filtered_test_log(case_study: str, experiment: str, base_path: str = 'filtered_test_logs') -> EventLog:
    """
    Load the filtered test log for a given case study and experiment.
    Normalizes to only complete events for consistency with simulation logs.
    
    Args:
        case_study: Name of the case study (e.g., 'Purchasing')
        experiment: Experiment identifier (e.g., 'exp1')
        base_path: Base path to filtered_test_logs directory
    
    Returns:
        EventLog from the filtered test log file (only complete events)
    """
    test_log_path = os.path.join(base_path, case_study, f'test_log_{experiment}.xes')
    
    if not os.path.exists(test_log_path):
        raise FileNotFoundError(f"Filtered test log not found: {test_log_path}")
    
    log = xes_importer.apply(test_log_path)
    
    # Normalize to only complete events
    normalized_log = normalize_activity_names(log)
    
    return normalized_log


def compute_dfg_frequencies(log: EventLog) -> dict:
    """
    Compute directly-follows graph (DFG) with frequencies from an event log.
    
    Uses pm4py's DFG discovery for efficiency.
    
    Args:
        log: EventLog object
    
    Returns:
        Dictionary mapping (activity_from, activity_to) -> frequency count
    """
    # Use pm4py's DFG discovery
    dfg, start_activities, end_activities = pm4py.discover_dfg(log)
    
    # Convert to dictionary format: (activity_from, activity_to) -> frequency
    dfg_dict = {pair: count for pair, count in dfg.items()}
    
    return dfg_dict


def compute_cfld(log1_dfg: dict, log2_dfg: dict) -> float:
    """
    Compute CFLD (Conformance Checking based on Frequencies of Labeled Directly-follows Relations)
    between two event logs based on their DFGs.
    
    CFLD compares the frequencies of directly-follows relations between two logs.
    Lower values indicate better conformance.
    
    Args:
        log1_dfg: DFG frequencies from first log (dict: (activity_from, activity_to) -> frequency)
        log2_dfg: DFG frequencies from second log (dict: (activity_from, activity_to) -> frequency)
    
    Returns:
        Normalized CFLD distance in [0, 1] (L1 distance divided by 2).
    """
    # Get all unique directly-follows relations from both logs
    all_relations = set(log1_dfg.keys()) | set(log2_dfg.keys())
    
    if not all_relations:
        return 0.0  # Both logs are empty
    
    # Normalize frequencies to probabilities for each log
    total_freq_1 = sum(log1_dfg.values())
    total_freq_2 = sum(log2_dfg.values())
    
    if total_freq_1 == 0 or total_freq_2 == 0:
        return 1.0  # One log is empty -> maximal normalized distance
    
    # Compute probability distributions
    prob_1 = {rel: log1_dfg.get(rel, 0) / total_freq_1 for rel in all_relations}
    prob_2 = {rel: log2_dfg.get(rel, 0) / total_freq_2 for rel in all_relations}
    
    # L1 distance between two probability distributions is in [0, 2].
    # Normalize to [0, 1] for easier interpretation.
    cfld = 0.5 * sum(abs(prob_1[rel] - prob_2[rel]) for rel in all_relations)
    
    return cfld


def _compute_2gram_frequencies(log: EventLog) -> dict:
    """
    Compute normalized 2-gram frequencies over activity sequences in an event log.
    """
    gram_counts = defaultdict(int)
    total = 0
    for trace in log:
        seq = [event.get("concept:name", "") for event in trace]
        if len(seq) < 2:
            continue
        for i in range(len(seq) - 1):
            gram = (seq[i], seq[i + 1])
            gram_counts[gram] += 1
            total += 1
    if total == 0:
        return {}
    return {gram: cnt / total for gram, cnt in gram_counts.items()}


def compute_2gram_distance(log1: EventLog, log2: EventLog) -> float:
    """
    Compute distance between two logs using normalized 2-gram distributions.
    Distance is the normalized L1 distance in [0, 1].
    """
    dist1 = _compute_2gram_frequencies(log1)
    dist2 = _compute_2gram_frequencies(log2)
    grams = set(dist1.keys()) | set(dist2.keys())
    if not grams:
        return 0.0
    return 0.5 * sum(abs(dist1.get(g, 0.0) - dist2.get(g, 0.0)) for g in grams)


def get_all_scenarios(simulations_base_path: str) -> list:
    """
    Get all scenario paths from the simulations folder.
    
    Args:
        simulations_base_path: Base path to simulations folder
    
    Returns:
        List of tuples (case_study, experiment, scenario_name, full_path)
    """
    scenarios = []
    
    for case_exp_dir in sorted(os.listdir(simulations_base_path)):
        case_exp_path = os.path.join(simulations_base_path, case_exp_dir)
        
        if not os.path.isdir(case_exp_path):
            continue
        
        # Parse case study and experiment from directory name (e.g., "Purchasing exp1")
        parts = case_exp_dir.rsplit(' exp', 1)
        if len(parts) != 2:
            continue
        
        case_study = parts[0]
        experiment = 'exp' + parts[1]
        
        # Get all scenario subdirectories
        for scenario_dir in sorted(os.listdir(case_exp_path)):
            scenario_path = os.path.join(case_exp_path, scenario_dir)
            
            if os.path.isdir(scenario_path):
                scenarios.append((case_study, experiment, scenario_dir, scenario_path))
    
    return scenarios


def main():
    """Main function to compute CFLD between generated logs and filtered test logs."""
    
    simulations_base_path = '../simulations'
    filtered_logs_base_path = 'filtered_test_logs'
    output_file = 'cfld_results.csv'
    
    # Check if simulations folder exists
    if not os.path.exists(simulations_base_path):
        print(f"Error: Simulations folder not found at {simulations_base_path}")
        return
    
    # Check if filtered test logs folder exists
    if not os.path.exists(filtered_logs_base_path):
        print(f"Error: Filtered test logs folder not found at {filtered_logs_base_path}")
        return
    
    print("=" * 80)
    print("Computing CFLD: Generated Logs vs Filtered Test Logs")
    print("=" * 80)
    
    # Get all scenarios
    print("\n1. Discovering all scenarios...")
    all_scenarios = get_all_scenarios(simulations_base_path)
    print(f"   Found {len(all_scenarios)} scenarios")
    
    if not all_scenarios:
        print("   No scenarios found. Exiting.")
        return
    
    # Check existing results
    results_file_exists = os.path.exists(output_file)
    computed_scenarios = set()
    
    if results_file_exists:
        existing_df = pd.read_csv(output_file)
        computed_scenarios = set(
            zip(existing_df['case_study'], existing_df['experiment'], existing_df['scenario'])
        )
        print(f"   Found existing results file with {len(existing_df)} entries")
        print("   Will skip already computed scenarios and continue...")
    else:
        print("   Starting fresh computation...")
    
    # Process each scenario
    print("\n2. Computing CFLD for each scenario...")
    results = []
    
    for case_study, experiment, scenario_name, scenario_path in tqdm(all_scenarios, desc="Computing CFLD"):
        scenario_key = (case_study, experiment, scenario_name)
        
        # Skip if already computed
        if scenario_key in computed_scenarios:
            continue
        
        try:
            # Load generated simulation log
            sim_log = load_scenario_logs(scenario_path)
            sim_dfg = compute_dfg_frequencies(sim_log)
            
            # Load corresponding filtered test log
            test_log = load_filtered_test_log(case_study, experiment, filtered_logs_base_path)
            test_dfg = compute_dfg_frequencies(test_log)
            
            # Compute CFLD
            cfld_value = compute_cfld(sim_dfg, test_dfg)
            
            # Store result
            result_row = {
                'case_study': case_study,
                'experiment': experiment,
                'scenario': scenario_name,
                'CFLD': cfld_value,
                'sim_traces': len(sim_log),
                'test_traces': len(test_log)
            }
            results.append(result_row)
            
            # Save progressively after each computation
            if results:
                df_new = pd.DataFrame(results)
                
                if results_file_exists:
                    # Append to existing file
                    existing_df = pd.read_csv(output_file)
                    df_combined = pd.concat([existing_df, df_new], ignore_index=True)
                    df_combined.to_csv(output_file, index=False)
                else:
                    # Create new file
                    df_new.to_csv(output_file, index=False)
                    results_file_exists = True
                
                results = []  # Clear results after saving
            
        except FileNotFoundError as e:
            print(f"\n   ⚠️  Warning: {e}")
            continue
        except Exception as e:
            print(f"\n   ⚠️  Error processing {scenario_key}: {e}")
            continue
    
    print(f"\n✓ Completed!")
    print(f"✓ Results saved to: {output_file}")
    print("=" * 80)


if __name__ == '__main__':
    main()
