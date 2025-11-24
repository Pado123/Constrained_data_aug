import pandas as pd
import numpy as np
import os
from scipy import stats
from src.entropies import (
    convert_and_clean,
    cf_entropy_seq
)

def get_log(path):
    df = pd.read_csv(path)
    df['time:timestamp'] = pd.to_datetime(df['time:timestamp'], format='mixed')

    def fix_microsecond(ts):
        if ts.microsecond == 0:
            return ts.replace(microsecond=1)
        return ts

    df['time:timestamp'] = df['time:timestamp'].apply(fix_microsecond)
    log = convert_and_clean(df)
    return log

def summary_stats(values):
    values = np.array(values)
    n = len(values)
    mean = np.mean(values)
    std = np.std(values, ddof=1) if n > 1 else 0.0

    # Intervallo di confidenza normale (z-score)
    z = 1.96
    ci_norm_low = mean - z * std / np.sqrt(n) if n > 1 else mean
    ci_norm_high = mean + z * std / np.sqrt(n) if n > 1 else mean

    # Intervallo di confidenza con t di Student
    t = stats.t.ppf(0.975, df=n-1) if n > 1 else 0.0
    ci_t_low = mean - t * std / np.sqrt(n) if n > 1 else mean
    ci_t_high = mean + t * std / np.sqrt(n) if n > 1 else mean

    return {
        "mean": mean,
        "std": std,
        "ci_norm_low": ci_norm_low,
        "ci_norm_high": ci_norm_high,
        "ci_t_low": ci_t_low,
        "ci_t_high": ci_t_high
    }

log_names = ["purchasing", "production", "consulta", "bpi12", "bpi12a", "bpi12o", "bpi17", "bpi17o", "hospital"]
scenarios = ["A", "B", "C", "D", "E"]
N_SIM = 10

path = "results"
# path = "results2"

os.makedirs(f'{path}/entropies', exist_ok=True)

for log_name in log_names:
    rows = []

    if log_name in ['purchasing', 'production', 'consulta', 'bpi12', 'bpi17', 'hospital']:
        experiments = ["exp1", "exp2", "exp3", "exp4",]
    elif log_name in ['bpi12a']:
        experiments = ["exp1", "exp2", "exp3"]
    else:
        experiments = ["exp1", "exp2"]

    for exp in experiments:
        for scenario in scenarios:
                if exp != 'exp1' and scenario in ["D", "E"]:
                    continue
                base_path = f"{path}/simulations/{log_name} {exp}/scenario{scenario}"
                
                prefix_entropies = []
                norm_prefix_entropies = []
                trace_entropies = []
                norm_trace_entropies = []

                for i in range(N_SIM):
                    path = f"{base_path}/sim_{i}.csv"
                    if not os.path.exists(path):
                        continue
                    print(f"[{exp}] {log_name}, scenario={scenario}, sim={i}")
                    log = get_log(path)

                    prefix_entropy, n_prefixes = cf_entropy_seq(log, prefix=True, return_sequence_count=True)
                    norm_prefix_entropy = prefix_entropy / np.log2(n_prefixes)

                    trace_entropy, n_traces = cf_entropy_seq(log, prefix=False, return_sequence_count=True)
                    norm_trace_entropy = trace_entropy / np.log2(n_traces)

                    rows.append({
                        'log_name': log_name,
                        'experiment': exp,
                        'scenario': scenario,
                        'simulation_id': i,
                        'prefix_entropy': prefix_entropy,
                        'n_prefixes': n_prefixes,
                        'normalized_prefix_entropy': norm_prefix_entropy,
                        'trace_entropy': trace_entropy,
                        'n_traces': n_traces,
                        'normalized_trace_entropy': norm_trace_entropy,
                    })

                    prefix_entropies.append(prefix_entropy)
                    norm_prefix_entropies.append(norm_prefix_entropy)
                    trace_entropies.append(trace_entropy)
                    norm_trace_entropies.append(norm_trace_entropy)

                
                sp = summary_stats(prefix_entropies)
                snp = summary_stats(norm_prefix_entropies)
                st = summary_stats(trace_entropies)
                snt = summary_stats(norm_trace_entropies)

                def make_stat_row(label, p=None, np_=None, t=None, nt=None):
                    return {
                        'log_name': log_name,
                        'experiment': exp,
                        'scenario': scenario,
                        'simulation_id': label,
                        'prefix_entropy': p,
                        'n_prefixes': np.nan,
                        'normalized_prefix_entropy': np_,
                        'trace_entropy': t,
                        'n_traces': np.nan,
                        'normalized_trace_entropy': nt,
                    }

                rows.extend([
                    make_stat_row("mean", sp["mean"], snp["mean"], t=st["mean"], nt=snt["mean"]),
                    make_stat_row("std", sp["std"], snp["std"], t=st["std"], nt=snt["std"]),
                    make_stat_row("ci95_norm_low", sp["ci_norm_low"], snp["ci_norm_low"], t=st["ci_norm_low"], nt=snt["ci_norm_low"]),
                    make_stat_row("ci95_norm_high", sp["ci_norm_high"], snp["ci_norm_high"], t=st["ci_norm_high"], nt=snt["ci_norm_high"]),
                    make_stat_row("ci95_t_low", sp["ci_t_low"], snp["ci_t_low"], t=st["ci_t_low"], nt=snt["ci_t_low"]),
                    make_stat_row("ci95_t_high", sp["ci_t_high"], snp["ci_t_high"], t=st["ci_t_high"], nt=snt["ci_t_high"]),
                ])

    
    df = pd.DataFrame(rows)
    df.to_csv(f"{path}/entropies/entropy_{log_name}.csv", index=False)
    print(f"Saved: {path}/entropies/entropy_{log_name}.csv")
