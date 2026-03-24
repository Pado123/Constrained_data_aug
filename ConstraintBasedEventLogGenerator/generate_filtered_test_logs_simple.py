"""
Simplified script to generate filtered test logs.

This version requires you to enable constraints for one experiment at a time
in constraints_per_log.py, then run the script.

For automatic experiment-based filtering, use generate_filtered_test_logs.py
(requires constraints to be restructured to support experiment selection).
"""

from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from src.train_utils import splitEventLog
from src.preprocess_utils import add_lc_to_act
from constraints.framework_constraints import get_filtered_log
from constraints.utils_ts import extract_event_seqs_and_alphabet
import os
import warnings

warnings.filterwarnings('ignore')

# Case study configurations
CASE_STUDIES = {
    'ds02': {
        'path': 'data/ds02/log.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'ds03': {
        'path': 'data/ds03/log.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'ds01': {
        'path': 'data/ds01/log.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'bpi12': {
        'path': 'data/bpi12/bpi12w.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'bpi12a': {
        'path': 'data/bpi12a/bpi12a_pp.xes',
        'experiments': ['exp1', 'exp2', 'exp3']
    },
    'bpi12o': {
        'path': 'data/bpi12o/bpi12o_pp.xes',
        'experiments': ['exp1', 'exp2']
    },
    'bpi17': {
        'path': 'data/bpi17/bpi17w.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    },
    'bpi17o': {
        'path': 'data/bpi17o/bpi17o_pp.xes',
        'experiments': ['exp1', 'exp2']
    },
    'ds06': {
        'path': 'data/ds06/log.xes',
        'experiments': ['exp1', 'exp2', 'exp3', 'exp4']
    }
}


def main():
    """Generate filtered test logs using currently enabled constraints in constraints_per_log.py."""
    
    output_base = 'filtered_test_logs'
    os.makedirs(output_base, exist_ok=True)
    
    print("=" * 80)
    print("Generating Filtered Test Logs")
    print("=" * 80)
    print("\n⚠️  NOTE: This script uses whatever constraints are currently enabled")
    print("   in constraints/constraints_per_log.py")
    print("   To filter by experiment, enable one experiment's constraints at a time.\n")
    
    for case_study, config in CASE_STUDIES.items():
        log_path = config['path']
        
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
            
            # Filter test log with currently enabled constraints
            print(f"\n3. Filtering test log with enabled constraints...")
            try:
                filtered_test_log = get_filtered_log(
                    test_log,
                    case_study,
                    alphabet,
                    mining_log=train_log,
                )
                
                # Save as test_log_filtered.xes (single file with current constraints)
                output_path = os.path.join(case_study_output, 'test_log_filtered.xes')
                
                if len(filtered_test_log) > 0:
                    xes_exporter.apply(filtered_test_log, output_path)
                    print(f"   ✓ Saved: {output_path} ({len(filtered_test_log)} traces)")
                else:
                    print(f"   ⚠️  Warning: No traces passed constraints")
                    print(f"   ⚠️  This may mean constraints are too restrictive or not enabled")
                    
            except ValueError as e:
                print(f"   ✗ Error filtering log: {e}")
                print(f"   ⚠️  Make sure constraints are enabled in constraints_per_log.py")
            except Exception as e:
                print(f"   ✗ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"\n✓ Completed processing {case_study}")
            
        except Exception as e:
            print(f"\n✗ Error processing {case_study}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 80}")
    print("Finished generating filtered test logs")
    print(f"Output directory: {output_base}/")
    print("\n⚠️  To filter by experiment, enable one experiment's constraints")
    print("   in constraints_per_log.py and re-run this script.")
    print("=" * 80)


if __name__ == '__main__':
    main()

