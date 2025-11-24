#%% 
from collections import Counter
import pandas as pd
from scipy.stats import entropy as et
from src.eventlog_utils import convert_log

def convert_and_clean(df):
    if 'lifecycle:transition' in df.columns:
        df = convert_log(df)
        df.rename(columns={'START': 'start:timestamp', 'END': 'time:timestamp'}, inplace=True, errors='ignore')
    for col in ['start:timestamp', 'time:timestamp']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    df.reset_index(inplace=True, drop=True)
    return df
    
def compute_entropy(sequences):
    # Flatten all symbols from all sequences
    all_symbols = [symbol for seq in sequences for symbol in seq]
    
    # Count frequencies
    total = len(all_symbols)
    freq = Counter(all_symbols)
    prob = [count / total for count in freq.values()]

    # Compute probabilities and entropy
    entropy = et(prob, base=10)  # Using base 2 for bits
    return entropy

def get_all_prefixes(sequences):
    
    all_prefixes = []
    for seq in sequences:
        for i in range(1, len(seq) + 1):
            all_prefixes.append(seq[:i])
    return all_prefixes

def cf_entropy_seq(log, prefix=True, activity_name='concept:name', case_id_name='case:concept:name', return_sequence_count=False):
    
    # This function is used to compute the entropy of a log under the point of view of the prefix/trace perspective.
    # You can use prefix=False for trace entropy, or prefix=True for prefix entropy.
    # If return_sequence_count, return len(sequences) to have all values for normalization
    
    # Make a list of sequence of activities for each case
    cases = {}
    for index, row in log.iterrows():
        case_id = row[case_id_name]
        activity = row[activity_name]
        if case_id not in cases:
            cases[case_id] = []
        cases[case_id].append(activity)

    if prefix:
        sequences = get_all_prefixes(list(cases.values()))
    else:
        sequences = list(cases.values())

    entropy_value = compute_entropy(sequences)

    if return_sequence_count:
        return entropy_value, len(sequences)
    else:
        return entropy_value
