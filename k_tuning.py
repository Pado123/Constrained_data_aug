import argparse
import gc
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
FRAMEWORK_DIR = ROOT / "ConstraintBasedEventLogGenerator"
if str(FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_DIR))

from compute_cfld_all_scenarios import compute_cfld, compute_dfg_frequencies  # noqa: E402
from src.entropies import cf_entropy_seq  # noqa: E402


def _pick_first_existing_column(df: pd.DataFrame, candidates: list[str]):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _load_event_log_from_path(path: Path):
    """Load XES or CSV into a PM4Py EventLog."""
    suffix = path.suffix.lower()
    if suffix == ".xes":
        return xes_importer.apply(str(path))
    if suffix != ".csv":
        raise ValueError(f"Unsupported log type: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"CSV is empty: {path}")

    case_col = _pick_first_existing_column(
        df, ["case:concept:name", "case_id", "caseid", "case", "Case ID"]
    )
    act_col = _pick_first_existing_column(
        df, ["concept:name", "activity", "Activity", "event", "event_name"]
    )
    ts_col = _pick_first_existing_column(
        df, ["time:timestamp", "timestamp", "start:timestamp", "start_timestamp", "time", "date", "datetime"]
    )

    if case_col is None or act_col is None:
        raise ValueError(
            f"CSV missing required case/activity columns: {path} "
            f"(found columns: {list(df.columns)})"
        )

    work_df = df.copy()
    work_df["case:concept:name"] = work_df[case_col].astype(str)
    work_df["concept:name"] = work_df[act_col].astype(str)

    if ts_col is not None:
        work_df["time:timestamp"] = pd.to_datetime(work_df[ts_col], errors="coerce", utc=True)
        if work_df["time:timestamp"].isna().all():
            ts_col = None

    if ts_col is None:
        work_df["__event_order"] = work_df.groupby("case:concept:name").cumcount()
        base_ts = pd.Timestamp("2000-01-01 00:00:00", tz="UTC")
        work_df["time:timestamp"] = base_ts + pd.to_timedelta(work_df["__event_order"], unit="s")
        work_df = work_df.drop(columns=["__event_order"])

    work_df = pm4py.format_dataframe(
        work_df,
        case_id="case:concept:name",
        activity_key="concept:name",
        timestamp_key="time:timestamp",
    )
    return pm4py.convert_to_event_log(work_df)


def _extract_sequences(log) -> list[list[str]]:
    return [[event["concept:name"] for event in trace] for trace in log]


def _bootstrap_sequences(sequences: list[list[str]], rng: random.Random) -> list[list[str]]:
    if not sequences:
        return []
    return [list(sequences[rng.randrange(len(sequences))]) for _ in range(len(sequences))]


def _build_transition_model(
    sequences: list[list[str]], k: int
) -> dict[tuple, dict[str, float]]:
    counts = defaultdict(lambda: defaultdict(int))
    for trace in sequences:
        prefix: tuple = tuple()
        for activity in trace:
            counts[prefix][activity] += 1
            if k > 0:
                prefix = (prefix + (activity,))[-k:]
            else:
                prefix = tuple()
        counts[prefix]["<END>"] += 1

    model = {}
    for prefix, next_counts in counts.items():
        total = sum(next_counts.values())
        model[prefix] = {act: c / total for act, c in next_counts.items()}
    return model


def _sample_sequences_from_model(
    model: dict[tuple, dict[str, float]],
    n_traces: int,
    k: int,
    rng: random.Random,
    max_trace_length: int,
) -> list[list[str]]:
    sampled = []
    empty_prefix = tuple()
    for _ in range(n_traces):
        prefix = empty_prefix
        trace = []
        for _step in range(max_trace_length):
            probs = model.get(prefix)
            if probs is None:
                probs = model.get(empty_prefix)
            if probs is None:
                break
            activities = list(probs.keys())
            weights = list(probs.values())
            nxt = rng.choices(activities, weights=weights, k=1)[0]
            if nxt == "<END>":
                break
            trace.append(nxt)
            if k > 0:
                prefix = (prefix + (nxt,))[-k:]
            else:
                prefix = empty_prefix
        sampled.append(trace)
    return sampled


def _sequences_to_dataframe(sequences: list[list[str]]) -> pd.DataFrame:
    rows = []
    base_ts = pd.Timestamp("2000-01-01 00:00:00")
    for case_id, trace in enumerate(sequences, start=1):
        for order, activity in enumerate(trace):
            rows.append(
                {
                    "case:concept:name": str(case_id),
                    "concept:name": activity,
                    "time:timestamp": base_ts + pd.to_timedelta(order, unit="s"),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["case:concept:name", "concept:name", "time:timestamp"])
    return pd.DataFrame(rows)


def _compute_rescaled_trace_entropy(log_df: pd.DataFrame) -> float:
    if log_df.empty:
        return 0.0
    trace_entropy, n_traces = cf_entropy_seq(log_df, prefix=False, return_sequence_count=True)
    if n_traces <= 1:
        return 0.0
    return float(trace_entropy / math.log2(n_traces))


def _discover_event_logs(data_dir: Path) -> dict[str, Path]:
    event_logs = {}
    for case_dir in sorted([p for p in data_dir.iterdir() if p.is_dir()]):
        log_files = [f for f in case_dir.iterdir() if f.is_file() and f.suffix.lower() in {".xes", ".csv"}]
        for log_file in log_files:
            event_logs[case_dir.name] = log_file
            break  # just take the first .xes/.csv file found
    return event_logs


def _compute_pareto_frontier(points, maximize_y=True):
    # points is list of (x, y); lower x is better, higher y is better
    sorted_points = sorted(points, key=lambda p: (p[0], -p[1] if maximize_y else p[1]))
    pareto = []
    best_y = -float("inf") if maximize_y else float("inf")
    for x, y in sorted_points:
        if (maximize_y and y > best_y) or (not maximize_y and y < best_y):
            pareto.append((x, y))
            best_y = y
    return pareto


def run_k_tuning(
    data_dir: Path,
    output_dir: Path,
    k_values: list[int],
    n_runs: int,
    seed: int,
):
    """
    Instead of using a training set, this function now uses the whole available log as the "reference log"
    to compare the generated logs and select k through the pareto frontier on (cfld, entropy).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    detailed_path = output_dir / "k_tuning_detailed.csv"
    summary_path = output_dir / "k_tuning_summary.csv"
    pareto_path = output_dir / "k_tuning_pareto_front.csv"

    event_logs = _discover_event_logs(data_dir)
    if not event_logs:
        raise FileNotFoundError(f"No event logs found in {data_dir} (expected data/*/.xes or .csv files).")

    global_rng = random.Random(seed)
    detailed_rows = []

    print(f"Discovered {len(event_logs)} logs in {data_dir}.")
    for case_study, log_path in tqdm(event_logs.items(), desc="Case studies", unit="case"):
        print(f"\n[{case_study}] Import event log: {log_path}")
        log = _load_event_log_from_path(log_path)
        whole_sequences = _extract_sequences(log)
        if not whole_sequences:
            print(f"[{case_study}] skipped (empty log).")
            continue
        n_traces = len(whole_sequences)
        max_trace_length = max(len(trace) for trace in whole_sequences) if whole_sequences else 1

        reference_df = _sequences_to_dataframe(whole_sequences)
        reference_event_log = pm4py.convert_to_event_log(reference_df)
        reference_dfg = compute_dfg_frequencies(reference_event_log)

        for k in tqdm(k_values, desc=f"{case_study} k", leave=False):
            for run_id in range(n_runs):
                run_seed = global_rng.randint(0, 10**9)
                rng = random.Random(run_seed)

                # Instead of bootstrapping, just sample from the full log for now
                bootstrap_log = _bootstrap_sequences(whole_sequences, rng)
                ts_model = _build_transition_model(bootstrap_log, k=k)
                sim_sequences = _sample_sequences_from_model(
                    ts_model,
                    n_traces=n_traces,
                    k=k,
                    rng=rng,
                    max_trace_length=max_trace_length * 2,
                )
                sim_df = _sequences_to_dataframe(sim_sequences)
                sim_event_log = pm4py.convert_to_event_log(sim_df)
                sim_dfg = compute_dfg_frequencies(sim_event_log)

                cfld_value = compute_cfld(sim_dfg, reference_dfg)
                entropy_value = _compute_rescaled_trace_entropy(sim_df)
                detailed_rows.append(
                    {
                        "case_study": case_study,
                        "k": k,
                        "run_id": run_id,
                        "seed": run_seed,
                        "cfld": cfld_value,
                        "rescaled_trace_entropy": entropy_value,
                    }
                )

                del ts_model, sim_sequences, sim_df, sim_event_log, sim_dfg, bootstrap_log
                gc.collect()

        del log, whole_sequences, reference_df, reference_event_log, reference_dfg
        gc.collect()

    detailed_df = pd.DataFrame(detailed_rows).sort_values(
        ["case_study", "k", "run_id"], ignore_index=True
    )
    detailed_df.to_csv(detailed_path, index=False)

    summary_df = (
        detailed_df.groupby(["case_study", "k"], as_index=False)
        .agg(
            cfld_mean=("cfld", "mean"),
            cfld_std=("cfld", "std"),
            entropy_mean=("rescaled_trace_entropy", "mean"),
            entropy_std=("rescaled_trace_entropy", "std"),
        )
        .sort_values(["case_study", "k"], ignore_index=True)
    )
    summary_df.to_csv(summary_path, index=False)

    # Compute and save Pareto frontiers for each case study
    pareto_rows = []
    for case_study in summary_df["case_study"].unique():
        case_df = summary_df[summary_df["case_study"] == case_study]
        # On Pareto: higher entropy and lower cfld is better. But depends on whether cfld is a distance or a similarity.
        # Assuming lower cfld is better (distance).
        points = list(zip(case_df["k"], zip(-case_df["cfld_mean"], case_df["entropy_mean"])))
        # Use two-dim. Pareto optimization: maximize entropy, minimize cfld (so use -cfld for maximizing)
        pareto_candidates = [(k, entropy) for k, (neg_cfld, entropy) in points if neg_cfld is not None and entropy is not None]
        # Now sort and filter; filter k by non-dominated solutions:
        pareto_points = []
        last_entropy = -float("inf")
        best_cfld = float("-inf")
        sorted_rows = case_df.sort_values(by=["cfld_mean", "entropy_mean"], ascending=[True, False])
        for idx, row in sorted_rows.iterrows():
            entropy = row["entropy_mean"]
            neg_cfld = -row["cfld_mean"]
            if entropy > last_entropy:
                last_entropy = entropy
                best_cfld = neg_cfld
                pareto_points.append((row["k"], row["cfld_mean"], row["entropy_mean"]))
        for k, cfld, entropy in pareto_points:
            pareto_rows.append({"case_study": case_study, "k": k, "cfld_mean": cfld, "entropy_mean": entropy})

    pd.DataFrame(pareto_rows).to_csv(pareto_path, index=False)

    for case_study in summary_df["case_study"].unique():
        case_df = summary_df[summary_df["case_study"] == case_study]
        fig, ax_left = plt.subplots(figsize=(8, 4.5))
        ax_right = ax_left.twinx()

        line1 = ax_left.plot(
            case_df["k"], case_df["cfld_mean"], marker="o", color="tab:blue", label="CFLD mean"
        )
        line2 = ax_right.plot(
            case_df["k"],
            case_df["entropy_mean"],
            marker="s",
            color="tab:orange",
            label="Rescaled trace entropy mean",
        )

        # Highlight Pareto points in the plot, if any
        this_pareto = [row for row in pareto_rows if row["case_study"] == case_study]
        if this_pareto:
            ax_left.scatter(
                [row["k"] for row in this_pareto],
                [row["cfld_mean"] for row in this_pareto],
                marker="*", color="red", label="Pareto frontier"
            )

        ax_left.set_xlabel("k")
        ax_left.set_ylabel("CFLD", color="tab:blue")
        ax_right.set_ylabel("Rescaled trace entropy", color="tab:orange")
        ax_left.set_title(f"k tuning - {case_study}")
        ax_left.grid(True, alpha=0.25)

        lines = line1 + line2
        labels = [line.get_label() for line in lines]
        ax_left.legend(lines, labels, loc="best")

        fig.tight_layout()
        fig.savefig(plots_dir / f"{case_study}_k_tuning.png", dpi=150)
        plt.close(fig)

    print("\nDone.")
    print(f"- Detailed CSV: {detailed_path}")
    print(f"- Summary CSV: {summary_path}")
    print(f"- Pareto frontier CSV: {pareto_path}")
    print(f"- Plots dir:    {plots_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="k tuning on all data/*/log.xes/.csv using whole log and Pareto frontier selection (CFLD + rescaled trace entropy)."
    )
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "data"),
        help="Path containing case-study folders with logs (.xes or .csv).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "k_tuning_results"),
        help="Output path for CSV and plots.",
    )
    parser.add_argument("--n-runs", type=int, default=10, help="Number of runs per k.")
    parser.add_argument("--k-min", type=int, default=0, help="Min k.")
    parser.add_argument("--k-max", type=int, default=10, help="Max k.")
    parser.add_argument("--seed", type=int, default=42, help="Global random seed.")
    args = parser.parse_args()
import argparse
import gc
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer
from tqdm import tqdm


ROOT = Path(__file__).resolve().parent
FRAMEWORK_DIR = ROOT / "ConstraintBasedEventLogGenerator"
if str(FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_DIR))

from compute_cfld_all_scenarios import compute_cfld, compute_dfg_frequencies  # noqa: E402
from src.entropies import cf_entropy_seq  # noqa: E402


def _extract_sequences(log) -> list[list[str]]:
    return [[event["concept:name"] for event in trace] for trace in log]


def _bootstrap_sequences(sequences: list[list[str]], rng: random.Random) -> list[list[str]]:
    if not sequences:
        return []
    return [list(sequences[rng.randrange(len(sequences))]) for _ in range(len(sequences))]


def _build_transition_model(
    sequences: list[list[str]], k: int
) -> dict[tuple, dict[str, float]]:
    counts = defaultdict(lambda: defaultdict(int))
    for trace in sequences:
        prefix: tuple = tuple()
        for activity in trace:
            counts[prefix][activity] += 1
            if k > 0:
                prefix = (prefix + (activity,))[-k:]
            else:
                prefix = tuple()
        counts[prefix]["<END>"] += 1

    model = {}
    for prefix, next_counts in counts.items():
        total = sum(next_counts.values())
        model[prefix] = {act: c / total for act, c in next_counts.items()}
    return model


def _sample_sequences_from_model(
    model: dict[tuple, dict[str, float]],
    n_traces: int,
    k: int,
    rng: random.Random,
    max_trace_length: int,
) -> list[list[str]]:
    sampled = []
    empty_prefix = tuple()
    for _ in range(n_traces):
        prefix = empty_prefix
        trace = []
        for _step in range(max_trace_length):
            probs = model.get(prefix)
            if probs is None:
                probs = model.get(empty_prefix)
            if probs is None:
                break
            activities = list(probs.keys())
            weights = list(probs.values())
            nxt = rng.choices(activities, weights=weights, k=1)[0]
            if nxt == "<END>":
                break
            trace.append(nxt)
            if k > 0:
                prefix = (prefix + (nxt,))[-k:]
            else:
                prefix = empty_prefix
        sampled.append(trace)
    return sampled


def _sequences_to_dataframe(sequences: list[list[str]]) -> pd.DataFrame:
    rows = []
    base_ts = pd.Timestamp("2000-01-01 00:00:00")
    for case_id, trace in enumerate(sequences, start=1):
        for order, activity in enumerate(trace):
            rows.append(
                {
                    "case:concept:name": str(case_id),
                    "concept:name": activity,
                    "time:timestamp": base_ts + pd.to_timedelta(order, unit="s"),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["case:concept:name", "concept:name", "time:timestamp"])
    return pd.DataFrame(rows)


def _compute_rescaled_trace_entropy(log_df: pd.DataFrame) -> float:
    if log_df.empty:
        return 0.0
    trace_entropy, n_traces = cf_entropy_seq(log_df, prefix=False, return_sequence_count=True)
    if n_traces <= 1:
        return 0.0
    return float(trace_entropy / math.log2(n_traces))


def _discover_event_logs(data_dir: Path) -> dict[str, Path]:
    event_logs = {}
    for case_dir in sorted([p for p in data_dir.iterdir() if p.is_dir()]):
        log_files = [f for f in case_dir.iterdir() if f.is_file() and f.suffix.lower() in {".xes", ".csv"}]
        for log_file in log_files:
            event_logs[case_dir.name] = log_file
            break  # just take the first .xes/.csv file found
    return event_logs


def run_k_tuning(
    data_dir: Path,
    output_dir: Path,
    k_values: list[int],
    n_runs: int,
    seed: int,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    detailed_path = output_dir / "k_tuning_detailed.csv"
    summary_path = output_dir / "k_tuning_summary.csv"

    train_logs = _discover_event_logs(data_dir)
    if not train_logs:
        raise FileNotFoundError(f"No training logs found in {data_dir} (expected data/*/logTrain.xes).")

    global_rng = random.Random(seed)
    detailed_rows = []

    print(f"Discovered {len(train_logs)} training logs in {data_dir}.")
    for case_study, train_path in tqdm(train_logs.items(), desc="Case studies", unit="case"):
        print(f"\n[{case_study}] Import training log: {train_path}")
        train_log = _load_event_log_from_path(train_path)
        train_sequences = _extract_sequences(train_log)
        if not train_sequences:
            print(f"[{case_study}] skipped (empty training log).")
            continue
        n_traces = len(train_sequences)
        max_trace_length = max(len(trace) for trace in train_sequences) if train_sequences else 1

        train_df = _sequences_to_dataframe(train_sequences)
        train_event_log = pm4py.convert_to_event_log(train_df)
        train_dfg = compute_dfg_frequencies(train_event_log)

        for k in tqdm(k_values, desc=f"{case_study} k", leave=False):
            for run_id in range(n_runs):
                run_seed = global_rng.randint(0, 10**9)
                rng = random.Random(run_seed)

                # Different TS per run: bootstrap the training traces before estimating the k-order model.
                bootstrap_log = _bootstrap_sequences(train_sequences, rng)
                ts_model = _build_transition_model(bootstrap_log, k=k)
                sim_sequences = _sample_sequences_from_model(
                    ts_model,
                    n_traces=n_traces,
                    k=k,
                    rng=rng,
                    max_trace_length=max_trace_length * 2,
                )
                sim_df = _sequences_to_dataframe(sim_sequences)
                sim_event_log = pm4py.convert_to_event_log(sim_df)
                sim_dfg = compute_dfg_frequencies(sim_event_log)

                cfld_value = compute_cfld(sim_dfg, train_dfg)
                entropy_value = _compute_rescaled_trace_entropy(sim_df)
                detailed_rows.append(
                    {
                        "case_study": case_study,
                        "k": k,
                        "run_id": run_id,
                        "seed": run_seed,
                        "cfld": cfld_value,
                        "rescaled_trace_entropy": entropy_value,
                    }
                )

                del ts_model, sim_sequences, sim_df, sim_event_log, sim_dfg, bootstrap_log
                gc.collect()

        del train_log, train_sequences, train_df, train_event_log, train_dfg
        gc.collect()

    detailed_df = pd.DataFrame(detailed_rows).sort_values(
        ["case_study", "k", "run_id"], ignore_index=True
    )
    detailed_df.to_csv(detailed_path, index=False)

    summary_df = (
        detailed_df.groupby(["case_study", "k"], as_index=False)
        .agg(
            cfld_mean=("cfld", "mean"),
            cfld_std=("cfld", "std"),
            entropy_mean=("rescaled_trace_entropy", "mean"),
            entropy_std=("rescaled_trace_entropy", "std"),
        )
        .sort_values(["case_study", "k"], ignore_index=True)
    )
    summary_df.to_csv(summary_path, index=False)

    for case_study in summary_df["case_study"].unique():
        case_df = summary_df[summary_df["case_study"] == case_study]
        fig, ax_left = plt.subplots(figsize=(8, 4.5))
        ax_right = ax_left.twinx()

        line1 = ax_left.plot(
            case_df["k"], case_df["cfld_mean"], marker="o", color="tab:blue", label="CFLD mean"
        )
        line2 = ax_right.plot(
            case_df["k"],
            case_df["entropy_mean"],
            marker="s",
            color="tab:orange",
            label="Rescaled trace entropy mean",
        )

        ax_left.set_xlabel("k")
        ax_left.set_ylabel("CFLD", color="tab:blue")
        ax_right.set_ylabel("Rescaled trace entropy", color="tab:orange")
        ax_left.set_title(f"k tuning - {case_study}")
        ax_left.grid(True, alpha=0.25)

        lines = line1 + line2
        labels = [line.get_label() for line in lines]
        ax_left.legend(lines, labels, loc="best")

        fig.tight_layout()
        fig.savefig(plots_dir / f"{case_study}_k_tuning.png", dpi=150)
        plt.close(fig)

    print("\nDone.")
    print(f"- Detailed CSV: {detailed_path}")
    print(f"- Summary CSV: {summary_path}")
    print(f"- Plots dir:    {plots_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="k tuning on all data/*/logTrain.xes with CFLD + rescaled trace entropy."
    )
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "data"),
        help="Path containing case-study folders with logTrain.xes.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "k_tuning_results"),
        help="Output path for CSV and plots.",
    )
    parser.add_argument("--n-runs", type=int, default=10, help="Number of runs per k.")
    parser.add_argument("--k-min", type=int, default=0, help="Min k.")
    parser.add_argument("--k-max", type=int, default=10, help="Max k.")
    parser.add_argument("--seed", type=int, default=42, help="Global random seed.")
    args = parser.parse_args()

    if args.k_min < 0:
        raise ValueError("--k-min must be >= 0")
    if args.k_max < args.k_min:
        raise ValueError("--k-max must be >= --k-min")
    if args.n_runs <= 0:
        raise ValueError("--n-runs must be > 0")

    run_k_tuning(
        data_dir=Path(args.data_dir),
        output_dir=Path(args.output_dir),
        k_values=list(range(args.k_min, args.k_max + 1)),
        n_runs=args.n_runs,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
