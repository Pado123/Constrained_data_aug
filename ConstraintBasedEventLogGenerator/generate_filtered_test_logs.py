"""
Script to generate filtered test logs for each case study and experiment.

For each event log, this script:
1. Loads the original event log
2. Splits into train/test (80/20 split)
3. For each experiment (exp1-exp4), filters the test log based on constraints
4. Saves filtered test logs in organized folder structure

Output structure:
filtered_test_logs/
  {case_study}/
    test_log_exp1.xes
    test_log_exp2.xes
    test_log_exp3.xes
    test_log_exp4.xes
"""

from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from src.train_utils import splitEventLog
from src.preprocess_utils import add_lc_to_act
from constraints.framework_constraints import get_filtered_log
from constraints.utils_ts import extract_event_seqs_and_alphabet
from constraints.constraints_per_log import create_nfa_constraints
from pm4py.objects.log.obj import EventLog
from constraints.constants import END_PLACEHOLDER
from automata.fa.nfa import NFA
import os
import warnings

warnings.filterwarnings('ignore')

# Case study configurations
# Note: Paths are relative to workspace root (one level up from this script)
CASE_STUDIES = {
    'Purchasing': {
        'path': '../data/Purchasing/PurchasingExample.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'Production': {
        'path': '../data/Production/production.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'Consulta': {
        'path': '../data/Consulta/ConsultaDataMining201618.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'bpi12': {
        'path': '../data/bpi12/bpi12w.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'bpi12a': {
        'path': '../data/bpi12a/bpi12a_pp.xes',
        'experiments': ['exp1', 'exp2', 'exp3']
    },
    'bpi12o': {
        'path': '../data/bpi12o/bpi12o_pp.xes',
        'experiments': ['exp1', 'exp2']
    },
    'bpi17': {
        'path': '../data/bpi17/bpi17w.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'bpi17o': {
        'path': '../data/bpi17o/bpi17o_pp.xes',
        'experiments': ['exp1', 'exp2']
    },
    # 'hospital': {
    #     'path': '../data/hospital/hospital_pp_res.xes',
    #     'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    # }
}

def create_nfa_for_experiment(
    log_name: str,
    alphabet: list,
    experiment: str,
    mining_log: EventLog = None,
) -> NFA:
    """
    Create NFA constraints for a specific experiment.
    
    Uses the updated create_nfa_constraints function that supports experiment selection.
    """
    from constraints.constraints_per_log import create_nfa_constraints
    
    try:
        return create_nfa_constraints(log_name, alphabet, experiment, log=mining_log)
    except ValueError as e:
        # If experiment parameter isn't supported yet, fall back to all constraints
        try:
            return create_nfa_constraints(log_name, alphabet, log=mining_log)
        except Exception:
            raise ValueError(f"No constraints found for {log_name} experiment {experiment}. "
                           f"Constraints may be commented out in constraints_per_log.py. "
                           f"Original error: {e}")


def filter_log_by_experiment(
    log: EventLog,
    case_study: str,
    alphabet: list,
    experiment: str,
    mining_log: EventLog = None,
):
    """
    Filter a log based on constraints for a specific experiment.
    
    Args:
        log: Event log to filter
        case_study: Name of the case study
        alphabet: List of activities
        experiment: Experiment identifier (exp1, exp2, etc.)
    
    Returns:
        Filtered event log
    """
    constraints_nfa = create_nfa_for_experiment(
        case_study, alphabet, experiment, mining_log=mining_log
    )
    new_log = EventLog()
    
    print(f'  Filtering log for {experiment}...')
    for trace in log:
        event_seq = [event['concept:name'] for event in trace]
        event_seq.append(END_PLACEHOLDER)
        
        if constraints_nfa.accepts_input(event_seq):
            new_log.append(trace)
    
    original_len = len(log)
    filtered_len = len(new_log)
    removed_pct = (original_len - filtered_len) / original_len * 100 if original_len > 0 else 0
    
    print(f'    Original: {original_len} traces, Filtered: {filtered_len} traces '
          f'({removed_pct:.2f}% removed)')
    
    return new_log


def main():
    """Main function to generate filtered test logs for all case studies and experiments."""
    
    output_base = 'filtered_test_logs'
    os.makedirs(output_base, exist_ok=True)
    
    print("=" * 80)
    print("Generating Filtered Test Logs")
    print("=" * 80)
    
    for case_study, config in CASE_STUDIES.items():
        log_path = config['path']
        experiments = config['experiments']
        
        # Check if log file exists
        if not os.path.exists(log_path):
            print(f"\n⚠️  Skipping {case_study}: Log file not found at {log_path}")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"Processing: {case_study}")
        print(f"Log file: {log_path}")
        print(f"{'=' * 80}")
        
        # Create output directory for this case study
        case_study_output = os.path.join(output_base, case_study)
        os.makedirs(case_study_output, exist_ok=True)
        
        try:
            # Load original log
            print(f"\n1. Loading event log...")
            log = xes_importer.apply(log_path)
            print(f"   Loaded {len(log)} traces")
            
            # Split into train/test
            print(f"\n2. Splitting into train/test (80/20 split)...")
            train_log, test_log = splitEventLog(log, train_size=0.8, split_temporal=True)
            print(f"   Train: {len(train_log)} traces")
            print(f"   Test: {len(test_log)} traces")
            
            # Add lifecycle to activities
            train_log = add_lc_to_act(train_log)
            test_log = add_lc_to_act(test_log)
            
            # Extract alphabet
            _, alphabet = extract_event_seqs_and_alphabet(test_log)
            print(f"   Alphabet: {len(alphabet)} activities")
            
            # Process each experiment
            print(f"\n3. Filtering test log for each experiment...")
            for exp in experiments:
                try:
                    output_path = os.path.join(case_study_output, f'test_log_{exp}.xes')
                    
                    # Filter test log for this experiment
                    filtered_test_log = filter_log_by_experiment(
                        test_log,
                        case_study,
                        alphabet,
                        exp,
                        mining_log=train_log,
                    )
                    
                    # Save filtered log
                    if len(filtered_test_log) > 0:
                        xes_exporter.apply(filtered_test_log, output_path)
                        print(f"   ✓ Saved: {output_path} ({len(filtered_test_log)} traces)")
                    else:
                        print(f"   ⚠️  Warning: No traces passed constraints for {exp}")
                        print(f"   ⚠️  Skipping save (would create empty log)")
                    
                except ValueError as e:
                    print(f"   ✗ Error filtering for {exp}: {e}")
                except Exception as e:
                    print(f"   ✗ Unexpected error for {exp}: {e}")
            
            print(f"\n✓ Completed processing {case_study}")
            
        except Exception as e:
            print(f"\n✗ Error processing {case_study}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 80}")
    print("Finished generating filtered test logs")
    print(f"Output directory: {output_base}/")
    print("=" * 80)


if __name__ == '__main__':
    main()

