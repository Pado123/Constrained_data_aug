import argparse
import gc
import importlib.util
import os
import random
import shutil
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pm4py
from tqdm import tqdm
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.discovery.declare import algorithm as declare_miner
from pm4py.algo.discovery.declare.variants import classic as declare_classic


ROOT = Path(__file__).resolve().parent
from data_paths import LEGACY_CASE_TO_ID, path_for  # noqa: E402

FRAMEWORK_DIR = ROOT / "ConstraintBasedEventLogGenerator"
if str(FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_DIR))

# Load root constraints.py without colliding with framework constraints package.
constraints_script_spec = importlib.util.spec_from_file_location(
    "root_constraints_script", str(ROOT / "constraints.py")
)
root_constraints_script = importlib.util.module_from_spec(constraints_script_spec)
constraints_script_spec.loader.exec_module(root_constraints_script)
mine_declare_constraints = root_constraints_script.mine_declare_constraints

# Expose framework constraints package for framework imports.
constraints_pkg = types.ModuleType("constraints")
constraints_pkg.__path__ = [str(FRAMEWORK_DIR / "constraints")]
sys.modules["constraints"] = constraints_pkg

from EventLogGenerator import EventLogGenerator  # noqa: E402
from constraints.framework_constraints import get_filtered_log  # noqa: E402
from constraints.utils_ts import extract_event_seqs_and_alphabet  # noqa: E402
from src.preprocess_utils import add_lc_to_act  # noqa: E402
from src.entropies import convert_and_clean, cf_entropy_seq  # noqa: E402


# Generic dataset ids (ds01..ds04); logs under data/dsNN/ — see data_paths.py
CASE_STUDIES = {
    "ds02": {
        "path_log": path_for("ds02"),
        "label_data_attributes": [],
        "k": 2,
    },
    "ds03": {
        "path_log": path_for("ds03"),
        "label_data_attributes": [],
        "k": 2,
    },
    "ds01": {
        "path_log": path_for("ds01"),
        "label_data_attributes": [],
        "k": 2,
    },
    "ds04": {
        "path_log": path_for("ds04"),
        "label_data_attributes": [],
        "k": 2,
    },
}


SCENARIOS = ["A", "B", "C"]
CONSTRAINTS_PER_SIMULATION_SETS = [25, 50, 100]
GC_EVERY_N_SIMS = 1
RAM_LIMIT_GB = 28.0
SUPPORT_FILTER_MODE = "all"
DEFAULT_RANKING_MODE = "support_confidence"
DEFAULT_K = 2
SPLIT_LOG_STEMS = {"logtrain", "logtest", "train", "test"}

# When USE_TRAIN_TEST_SPLIT_50=1: train/test split; when 0: train and test on whole log
USE_TRAIN_TEST_SPLIT_50 = os.environ.get("USE_TRAIN_TEST_SPLIT_50", "").strip() == "1"
# When FILTER_REFERENCE_BY_CONSTRAINTS=0: use unfiltered reference for 2-gram (no constraint filtering)
FILTER_REFERENCE_BY_CONSTRAINTS = os.environ.get("FILTER_REFERENCE_BY_CONSTRAINTS", "1").strip() != "0"


def _split_log_train_test(log, train_ratio: float = 0.5):
    """Split log into train and test randomly (shuffled by trace)."""
    from src.train_utils import splitEventLog  # noqa: E402

    return splitEventLog(log, train_size=train_ratio, split_temporal=False)


class _RunningStats:
    """Online mean/std accumulator (Welford) for multiple metrics."""

    def __init__(self):
        self.n = 0
        self.mean = {}
        self.m2 = {}

    def update(self, values: dict):
        self.n += 1
        for key, x in values.items():
            x = float(x)
            prev_mean = self.mean.get(key, 0.0)
            delta = x - prev_mean
            new_mean = prev_mean + delta / self.n
            self.mean[key] = new_mean
            self.m2[key] = self.m2.get(key, 0.0) + delta * (x - new_mean)

    def finalize(self, keys):
        out = {}
        for key in keys:
            mean = self.mean.get(key, np.nan)
            if self.n <= 1:
                std = np.nan
            else:
                std = float(np.sqrt(self.m2.get(key, 0.0) / (self.n - 1)))
            out[f"{key}_mean"] = mean
            out[f"{key}_std"] = std
        return out


def _append_row_csv(path: Path, row: dict, columns):
    pd.DataFrame([row], columns=columns).to_csv(
        path, mode="a", header=(not path.exists()), index=False
    )


def _is_split_log(path: Path) -> bool:
    return path.stem.lower() in SPLIT_LOG_STEMS


def _pick_first_existing_column(df: pd.DataFrame, candidates: list[str]):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _load_event_log_from_path(path: Path):
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


def _mine_declare_constraints_from_log_object(log):
    parameters = {
        declare_classic.Parameters.MIN_SUPPORT_RATIO: 0.0,
        declare_classic.Parameters.MIN_CONFIDENCE_RATIO: 0.0,
        declare_classic.Parameters.ACTIVITY_KEY: "concept:name",
    }
    model = declare_miner.apply(log, parameters=parameters)
    n_traces = len(log)
    rows = []
    for template_name, rules in model.items():
        for activities, metrics in rules.items():
            support_count = int(metrics.get("support", 0) or 0)
            confidence_count = int(metrics.get("confidence", 0) or 0)
            rows.append(
                {
                    "template": template_name,
                    "activities": str(activities),
                    "support": support_count,
                    "confidence": confidence_count,
                    "satisfied_ratio_total_traces": (
                        float(confidence_count) / float(n_traces) if n_traces > 0 else 0.0
                    ),
                }
            )
    return pd.DataFrame(rows)


def _build_case_studies(data_dir: Path, selected_cases: list[str], default_k: int) -> dict:
    override_cfg = CASE_STUDIES
    discovered_paths = sorted(
        p
        for p in data_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".xes", ".csv"} and not _is_split_log(p)
    )
    case_studies = {}
    seen_names = set()
    for path in discovered_paths:
        rel = path.relative_to(data_dir)
        case_name = rel.parent.name if str(rel.parent) != "." else path.stem
        if case_name in seen_names:
            case_name = rel.with_suffix("").as_posix().replace("/", "__")
        seen_names.add(case_name)
        merged_cfg = {
            "path_log": path,
            "label_data_attributes": [],
            "k": default_k,
        }
        if case_name in override_cfg:
            merged_cfg["label_data_attributes"] = override_cfg[case_name].get(
                "label_data_attributes", []
            )
            merged_cfg["k"] = int(override_cfg[case_name].get("k", default_k))
        elif case_name in LEGACY_CASE_TO_ID:
            ds_key = LEGACY_CASE_TO_ID[case_name]
            if ds_key in override_cfg:
                merged_cfg["label_data_attributes"] = override_cfg[ds_key].get(
                    "label_data_attributes", []
                )
                merged_cfg["k"] = int(override_cfg[ds_key].get("k", default_k))
        case_studies[case_name] = merged_cfg

    if selected_cases:
        missing = [name for name in selected_cases if name not in case_studies]
        if missing:
            available = ", ".join(sorted(case_studies.keys()))
            raise ValueError(
                f"Requested cases not found: {missing}. Available discovered cases: {available}"
            )
        case_studies = {name: case_studies[name] for name in selected_cases}

    if not case_studies:
        raise FileNotFoundError(f"No .xes/.csv logs found under {data_dir}")
    return case_studies


def _current_rss_gb() -> float:
    """
    Return current resident memory (RSS) in GB, using Linux /proc.
    Falls back to 0.0 if unavailable.
    """
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    # VmRSS value is in kB.
                    kb = float(parts[1])
                    return kb / (1024.0 * 1024.0)
    except Exception:
        return 0.0
    return 0.0


def _enforce_ram_limit_or_exit(context: str):
    """
    Abort execution if process RSS exceeds RAM_LIMIT_GB.
    Exit code 137 is used to signal forced termination due to memory cap.
    """
    rss_gb = _current_rss_gb()
    if rss_gb > RAM_LIMIT_GB:
        print(
            f"[RAM GUARD] Exceeded limit ({rss_gb:.2f} GB > {RAM_LIMIT_GB:.2f} GB) "
            f"during {context}. Terminating run."
        )
        raise SystemExit(137)


def _prepare_activity_dataframe(df_in: pd.DataFrame) -> pd.DataFrame:
    # Keep only columns required by log-distance/event-log conversion and entropy.
    keep_cols = [
        c
        for c in ["case:concept:name", "concept:name", "lifecycle:transition", "time:timestamp"]
        if c in df_in.columns
    ]
    # Include alternate activity column names so we can normalize to concept:name
    for alt in ["activity", "Activity", "event", "event_name"]:
        if alt in df_in.columns and alt not in keep_cols:
            keep_cols.append(alt)
    df = df_in.loc[:, keep_cols].copy()
    if "case:concept:name" not in df.columns:
        df["case:concept:name"] = "1"
    df["case:concept:name"] = df["case:concept:name"].astype(str)
    # Ensure concept:name exists (pm4py may use different keys for some formats)
    if "concept:name" not in df.columns:
        act_col = _pick_first_existing_column(
            df, ["concept:name", "activity", "Activity", "event", "event_name"]
        )
        if act_col is not None:
            df["concept:name"] = df[act_col].astype(str)
    if "lifecycle:transition" in df.columns:
        df = df[df["lifecycle:transition"] == "complete"].copy()
        df["concept:name"] = df["concept:name"] + "_lc:complete"
    if "time:timestamp" in df.columns:
        df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], format="mixed")
        df = df.sort_values(["case:concept:name", "time:timestamp"]).reset_index(drop=True)
    else:
        df["__event_order"] = df.groupby("case:concept:name").cumcount()
        df = df.sort_values(["case:concept:name", "__event_order"]).reset_index(drop=True)
        base_ts = pd.Timestamp("2000-01-01 00:00:00")
        df["time:timestamp"] = base_ts + pd.to_timedelta(df["__event_order"], unit="s")
        df = df.drop(columns=["__event_order"])
    return df


def _is_skippable_generation_error(message: str) -> bool:
    """Return True for known data-sparsity errors that should skip a scenario."""
    msg = (message or "").lower()
    patterns = [
        "too restrictive",
        "no acceptable paths",
        "no constraints found",
        "max() iterable argument is empty",
        "zero-size array to reduction operation",
        "empty",
        "projected ts x constraints product is too large",
        "projected fallback-constraint product is too large",
        "reference for 2-gram",
    ]
    return any(p in msg for p in patterns)


def _build_skip_summary(skipped_rows):
    skipped_df = pd.DataFrame(skipped_rows)
    if skipped_df.empty:
        return skipped_df, pd.DataFrame(columns=["reason", "count"])
    if "reason" not in skipped_df.columns:
        skipped_df["reason"] = "unknown"
    reason_summary = (
        skipped_df.groupby("reason", as_index=False).size().rename(columns={"size": "count"})
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )
    return skipped_df, reason_summary


def _sim_df_to_event_log(df_in: pd.DataFrame):
    df = _prepare_activity_dataframe(df_in)
    return pm4py.convert_to_event_log(df)


def _sim_csv_to_event_log(sim_csv: Path):
    df = pd.read_csv(sim_csv)
    return _sim_df_to_event_log(df)


def _entropy_from_dataframe(df_in: pd.DataFrame):
    log_df = convert_and_clean(_prepare_activity_dataframe(df_in))
    prefix_entropy = cf_entropy_seq(log_df, prefix=True)
    trace_entropy = cf_entropy_seq(log_df, prefix=False)
    return {
        "prefix_entropy": prefix_entropy,
        "trace_entropy": trace_entropy,
    }


def _entropy_from_csv(sim_csv: Path):
    df = pd.read_csv(sim_csv)
    return _entropy_from_dataframe(df)


def _export_simulation_constraint_artifacts(sim_cache_root: Path, out_dir: Path, sim_id: int):
    """
    Export sampled constraints and output automaton for one simulation.
    Files are copied from the per-simulation cache hash directory to stable names.
    """
    if not sim_cache_root.exists():
        return

    # Each simulation cache root should contain a single hash directory.
    cache_dirs = [p for p in sim_cache_root.iterdir() if p.is_dir()]
    if not cache_dirs:
        return
    cache_dir = cache_dirs[0]

    sampled_constraints_src = cache_dir / "constraints_sampled_stats.csv"
    if not sampled_constraints_src.exists():
        # Backward compatibility with older cache artifacts.
        sampled_constraints_src = cache_dir / "constraints_post_quantile_stats.csv"
    applied_constraints_src = cache_dir / "constraints_applied_stats.csv"
    automaton_src = cache_dir / "final_intersection.pkl"

    sampled_constraints_dst = out_dir / f"sim_{sim_id}_sampled_constraints.csv"
    applied_constraints_dst = out_dir / f"sim_{sim_id}_applied_constraints.csv"
    automaton_dst = out_dir / f"sim_{sim_id}_output_automaton.pkl"

    if sampled_constraints_src.exists():
        shutil.copy2(sampled_constraints_src, sampled_constraints_dst)
    if applied_constraints_src.exists():
        shutil.copy2(applied_constraints_src, applied_constraints_dst)
    if automaton_src.exists():
        shutil.copy2(automaton_src, automaton_dst)


def _build_intersection_bottleneck_reports(constraints_dir: Path, metrics_dir: Path):
    profile_paths = list(constraints_dir.glob("**/intersection_profile.csv"))
    if not profile_paths:
        pd.DataFrame().to_csv(metrics_dir / "intersection_bottlenecks_top.csv", index=False)
        pd.DataFrame(columns=["skip_reason", "count"]).to_csv(
            metrics_dir / "intersection_skip_reasons.csv", index=False
        )
        return

    frames = []
    for p in profile_paths:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if df.empty:
            continue
        pstr = str(p)
        case_study = ""
        scenario = ""
        sim_folder = ""
        if "simulation_artifacts" in p.parts:
            idx = p.parts.index("simulation_artifacts")
            if idx - 1 >= 0:
                case_study = p.parts[idx - 1]
            if idx + 1 < len(p.parts):
                scenario = p.parts[idx + 1]
            if idx + 2 < len(p.parts):
                sim_folder = p.parts[idx + 2]
        df["case_study"] = case_study
        df["scenario"] = scenario
        df["simulation_folder"] = sim_folder
        df["profile_path"] = pstr
        frames.append(df)

    if not frames:
        pd.DataFrame().to_csv(metrics_dir / "intersection_bottlenecks_top.csv", index=False)
        pd.DataFrame(columns=["skip_reason", "count"]).to_csv(
            metrics_dir / "intersection_skip_reasons.csv", index=False
        )
        return

    all_profiles = pd.concat(frames, ignore_index=True)
    top_cols = [
        "case_study",
        "scenario",
        "simulation_folder",
        "rule_index",
        "template",
        "component_index",
        "candidate_states",
        "cumulative_states_before",
        "projected_product_states",
        "intersection_time_sec",
        "rss_gb",
        "accepted",
        "skip_reason",
        "profile_path",
    ]
    top = all_profiles.sort_values("intersection_time_sec", ascending=False).head(50)
    top.reindex(columns=top_cols).to_csv(
        metrics_dir / "intersection_bottlenecks_top.csv", index=False
    )
    skip_summary = (
        all_profiles[all_profiles["skip_reason"].astype(str) != ""]
        .groupby("skip_reason", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("count", ascending=False, ignore_index=True)
    )
    skip_summary.to_csv(metrics_dir / "intersection_skip_reasons.csv", index=False)


def _prefilter_constraints_df(constraints_df: pd.DataFrame) -> pd.DataFrame:
    """
    No threshold-based filtering: keep all mined constraints.
    """
    return constraints_df.copy()


def _build_summary_dataframe(grouped_stats: dict) -> pd.DataFrame:
    if not grouped_stats:
        return pd.DataFrame(
            columns=[
                "case_study",
                "scenario",
                "two_gram_distance_mean",
                "two_gram_distance_std",
                "prefix_entropy_mean",
                "prefix_entropy_std",
                "trace_entropy_mean",
                "trace_entropy_std",
            ]
        )

    summary_rows = []
    for (case_study, scenario), stats in grouped_stats.items():
        row = {"case_study": case_study, "scenario": scenario}
        row.update(
            stats.finalize(
                [
                    "two_gram_distance",
                    "prefix_entropy",
                    "trace_entropy",
                ]
            )
        )
        summary_rows.append(row)
    return pd.DataFrame(summary_rows).sort_values(
        ["case_study", "scenario"], ignore_index=True
    )


def _write_summary_checkpoints(metrics_dir: Path, grouped_stats: dict, skip_reason_counts: dict):
    summary_out = metrics_dir / "summary_mean_std_metrics.csv"
    _build_summary_dataframe(grouped_stats).to_csv(summary_out, index=False)
    skipped_by_reason_out = metrics_dir / "skipped_summary_by_reason.csv"
    skipped_by_reason_df = (
        pd.DataFrame(
            [{"reason": reason, "count": count} for reason, count in skip_reason_counts.items()]
        )
        .sort_values("count", ascending=False, ignore_index=True)
        if skip_reason_counts
        else pd.DataFrame(columns=["reason", "count"])
    )
    skipped_by_reason_df.to_csv(skipped_by_reason_out, index=False)


def run_pipeline_for_config(
    n_sim: int,
    output_root: Path,
    constraints_per_simulation: int,
    ranking_mode: str,
    case_studies: dict,
    default_k: int = DEFAULT_K,
    seed: int | None = None,
    train_split_ratio: float = 0.5,
    use_train_test_split: bool | None = None,
    filter_reference_by_constraints: bool | None = None,
):
    use_split = use_train_test_split if use_train_test_split is not None else USE_TRAIN_TEST_SPLIT_50
    filter_ref = filter_reference_by_constraints if filter_reference_by_constraints is not None else FILTER_REFERENCE_BY_CONSTRAINTS

    os.environ["DECLARE_SUPPORT_FILTER_MODE"] = SUPPORT_FILTER_MODE
    os.environ["DECLARE_CONSTRAINT_RANKING_MODE"] = ranking_mode
    os.environ.setdefault("DECLARE_MIN_SUPPORT_RATIO", "0.0")
    os.environ.setdefault("DECLARE_MIN_CONFIDENCE_RATIO", "0.0")
    os.environ.setdefault("DECLARE_MAX_CONSTRAINTS", "0")
    os.environ["DECLARE_SAMPLE_SIZE"] = str(constraints_per_simulation)
    os.environ["DECLARE_MAX_AUTOMATA_COMPONENTS"] = str(constraints_per_simulation)

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        os.environ["DECLARE_SAMPLE_SEED"] = str(seed)
        print(f"Random seed set to {seed}")

    config_root = output_root / f"constraints_{constraints_per_simulation}_k_{default_k}"
    config_root.mkdir(parents=True, exist_ok=True)
    constraints_dir = config_root / "constraints"
    sims_dir = config_root / "simulations"
    metrics_dir = config_root / "metrics"
    for d in [constraints_dir, sims_dir, metrics_dir]:
        d.mkdir(parents=True, exist_ok=True)

    print(
        "\n================ SINGLE RUN ================\n"
        f"Constraint sample size per simulation: {constraints_per_simulation}\n"
        f"Constraint ranking mode: {ranking_mode}"
    )
    if use_split:
        pct_train = int(round(train_split_ratio * 100))
        pct_test = 100 - pct_train
        print(f"*** TRAIN/TEST SPLIT: train on random {pct_train}%, eval 2-gram on remaining {pct_test}% ***")
    else:
        print("*** WHOLE LOG MODE: train and test on full log ***")

    if filter_ref:
        print("*** 2-gram reference: constraint-filtered (TS ∩ constraints) ***")
    else:
        print("*** 2-gram reference: unfiltered (no constraint filtering) ***")

    print("Step 1/4 - Ensuring constraints are available")
    case_iterator = tqdm(case_studies.items(), desc="Use cases", unit="case")
    for case_study, cfg in case_iterator:
        _enforce_ram_limit_or_exit(f"Step 1 case {case_study}")
        case_iterator.set_postfix_str(case_study)
        full_log_path = cfg["path_log"]

        constraints_case_dir = constraints_dir / case_study
        constraints_case_dir.mkdir(parents=True, exist_ok=True)
        split_suffix = f"_train_{int(round(train_split_ratio * 100))}" if use_split else ""
        constraints_stem = f"declare_constraints{split_suffix}_raw.csv" if use_split else "declare_constraints_full_log_raw.csv"
        constraints_raw_path = constraints_case_dir / constraints_stem
        prefiltered_stem = f"declare_constraints{split_suffix}_prefiltered.csv" if use_split else "declare_constraints_full_log_prefiltered.csv"
        constraints_prefiltered_path = constraints_case_dir / prefiltered_stem
        legacy_constraints_path = constraints_case_dir / "declare_constraints_full_log.csv"
        legacy_train_constraints_path = constraints_case_dir / "declare_constraints_train.csv"
        if constraints_raw_path.exists():
            print(f"[{case_study}] Found cached raw constraints CSV")
            constraints_df = pd.read_csv(constraints_raw_path)
        else:
            if use_split:
                print(f"[{case_study}] Mining constraints on train {int(round(train_split_ratio*100))}% and saving")
                full_log = _load_event_log_from_path(full_log_path)
                train_log, _ = _split_log_train_test(full_log, train_ratio=train_split_ratio)
                del full_log
                constraints_df = _mine_declare_constraints_from_log_object(train_log)
                del train_log
            else:
                print(f"[{case_study}] Mining constraints on full log and saving")
                if full_log_path.suffix.lower() == ".xes":
                    constraints_df = mine_declare_constraints(
                        str(full_log_path), min_support=0.0, min_confidence=0.0
                    )
                else:
                    mined_log = _load_event_log_from_path(full_log_path)
                    constraints_df = _mine_declare_constraints_from_log_object(mined_log)
            constraints_df.to_csv(constraints_raw_path, index=False)

        # Backward compatibility for older runs with legacy constraint file names.
        if not constraints_raw_path.exists() and legacy_constraints_path.exists():
            constraints_df = pd.read_csv(legacy_constraints_path)
            constraints_df.to_csv(constraints_raw_path, index=False)
        elif not constraints_raw_path.exists() and legacy_train_constraints_path.exists():
            constraints_df = pd.read_csv(legacy_train_constraints_path)
            constraints_df.to_csv(constraints_raw_path, index=False)

        prefiltered_constraints_df = _prefilter_constraints_df(constraints_df)
        prefiltered_constraints_df.to_csv(constraints_prefiltered_path, index=False)
        # Keep legacy filename but make semantics explicit via additional raw/prefiltered files.
        prefiltered_constraints_df.to_csv(legacy_constraints_path, index=False)
        print(
            f"[{case_study}] Constraints: raw={len(constraints_df)} "
            f"prefiltered={len(prefiltered_constraints_df)} "
            f"(no thresholding applied)"
        )
        del constraints_df
        del prefiltered_constraints_df
        gc.collect()

    print("\nStep 2/4 - Running simulations (A, B, C)")
    per_sim_columns = [
        "case_study",
        "scenario",
        "simulation_id",
        "two_gram_distance",
        "prefix_entropy",
        "trace_entropy",
    ]
    per_sim_out = metrics_dir / "per_simulation_metrics.csv"
    if per_sim_out.exists():
        per_sim_out.unlink()

    full_log_metrics_columns = [
        "case_study",
        "scenario",
        "simulation_id",
        "two_gram_distance",
        "prefix_entropy",
        "trace_entropy",
    ]
    full_log_metrics_out = metrics_dir / "full_log_metrics.csv"
    if full_log_metrics_out.exists():
        full_log_metrics_out.unlink()

    skipped_columns = ["case_study", "scenario", "simulation_id", "reason"]
    skipped_out = metrics_dir / "skipped_simulations.csv"
    if skipped_out.exists():
        skipped_out.unlink()
    scenario_status_columns = [
        "case_study",
        "scenario",
        "requested_simulations",
        "completed_simulations",
        "skipped_simulations",
        "status",
        "reason_if_not_runnable",
    ]
    scenario_status_out = metrics_dir / "scenario_run_status.csv"
    if scenario_status_out.exists():
        scenario_status_out.unlink()
    scenario_status_rows = []
    skip_reason_counts = {}
    # Checkpoints are written eagerly so partial progress is preserved on crashes.
    _write_summary_checkpoints(metrics_dir, grouped_stats={}, skip_reason_counts=skip_reason_counts)

    grouped_stats = {}
    for case_study, cfg in tqdm(case_studies.items(), desc="Simulating", unit="case"):
        _enforce_ram_limit_or_exit(f"Step 2 case {case_study}")
        full_log = _load_event_log_from_path(Path(cfg["path_log"]))
        if use_split:
            train_log, test_log = _split_log_train_test(full_log, train_ratio=train_split_ratio)
            del full_log
            log_for_generator = add_lc_to_act(train_log)
            reference_log_lc = add_lc_to_act(test_log)
            del train_log
            del test_log
            n_traces_to_generate = len(reference_log_lc)
        else:
            full_log_lc = add_lc_to_act(full_log)
            del full_log
            log_for_generator = full_log_lc
            reference_log_lc = full_log_lc
            n_traces_to_generate = len(full_log_lc)
        gc.collect()

        start_timestamp = log_for_generator[0][0]["time:timestamp"]

        # Baseline metrics (full log, or test half when in split mode)
        baseline_df = pm4py.convert_to_dataframe(reference_log_lc)
        baseline_df_clean = _prepare_activity_dataframe(baseline_df)
        t_prefix = cf_entropy_seq(baseline_df_clean, prefix=True)
        t_trace = cf_entropy_seq(baseline_df_clean, prefix=False)
        _append_row_csv(
            full_log_metrics_out,
            {
                "case_study": case_study,
                "scenario": "full_log" if not use_split else "test_50",
                "simulation_id": "original_full_log" if not use_split else "original_test_50",
                "two_gram_distance": 0.0,
                "prefix_entropy": t_prefix,
                "trace_entropy": t_trace,
            },
            full_log_metrics_columns,
        )

        for scenario in tqdm(SCENARIOS, desc=f"{case_study} scenarios", leave=False):
            _enforce_ram_limit_or_exit(f"Step 2 {case_study} {scenario}")
            scenario_name = f"scenario{scenario}"
            out_dir = sims_dir / case_study / scenario_name
            out_dir.mkdir(parents=True, exist_ok=True)
            scenario_completed = 0
            scenario_skipped = 0
            scenario_first_skip_reason = ""
            scenario_entropy_columns = [
                "simulation_id",
                "prefix_entropy",
                "trace_entropy",
            ]
            scenario_entropy_path = out_dir / "scenario_entropy_per_simulation.csv"
            if scenario_entropy_path.exists():
                scenario_entropy_path.unlink()
            scenario_stats = _RunningStats()
            print(
                f"[{case_study}] Generating {scenario_name} with {n_sim} simulations "
                f"(using top {constraints_per_simulation} constraints by support/confidence)"
            )
            scenario_cache_root = (
                constraints_dir / case_study / "simulation_artifacts" / scenario_name / "shared_constraints"
            )
            scenario_cache_root.mkdir(parents=True, exist_ok=True)
            os.environ["DECLARE_AUTOMATA_CACHE_DIR"] = str(scenario_cache_root)
            if seed is None:
                os.environ.pop("DECLARE_SAMPLE_SEED", None)

            # Reference for 2-gram distance:
            # - filter_ref=True: remove non-compliant traces (TS ∩ constraints)
            # - filter_ref=False: use reference as-is, no filtering
            if filter_ref:
                event_seqs, alphabet = extract_event_seqs_and_alphabet(log_for_generator)
                k_scenario = 50 if scenario in ["B"] else cfg["k"]
                filtered_log = get_filtered_log(
                    reference_log_lc,
                    case_study,
                    alphabet,
                    event_seqs=event_seqs,
                    k=k_scenario,
                    mining_log=log_for_generator if use_split else None,
                )
                ref_df = pm4py.convert_to_dataframe(filtered_log)
            else:
                ref_df = pm4py.convert_to_dataframe(reference_log_lc)
            reference_df_clean = _prepare_activity_dataframe(ref_df)

            for sim_id in tqdm(range(n_sim), desc=f"{scenario_name} sims", leave=False):
                _enforce_ram_limit_or_exit(f"simulation start {case_study}/{scenario_name}/{sim_id}")
                sim_path = out_dir / f"sim_{sim_id}.csv"
                sim_cache_root = scenario_cache_root

                try:
                    generator = EventLogGenerator(
                        log_for_generator,
                        k=(50 if scenario in ["B"] else cfg["k"]),
                        label_data_attributes=cfg["label_data_attributes"],
                        case_study=case_study,
                        scenario=scenario_name,
                    )
                except ValueError as exc:
                    msg = str(exc)
                    _export_simulation_constraint_artifacts(sim_cache_root, out_dir, sim_id)
                    if _is_skippable_generation_error(msg):
                        print(f"[{case_study}] Skipping {scenario_name} sim_{sim_id}: {msg}")
                        scenario_skipped += 1
                        if not scenario_first_skip_reason:
                            scenario_first_skip_reason = msg
                        _append_row_csv(
                            skipped_out,
                            {
                                "case_study": case_study,
                                "scenario": scenario_name,
                                "simulation_id": sim_id,
                                "reason": msg,
                            },
                            skipped_columns,
                        )
                        skip_reason_counts[msg] = skip_reason_counts.get(msg, 0) + 1
                        _write_summary_checkpoints(
                            metrics_dir, grouped_stats=grouped_stats, skip_reason_counts=skip_reason_counts
                        )
                        continue
                    raise

                try:
                    if scenario in ["A", "B", "C"]:
                        simulated_df = generator.apply(N=n_traces_to_generate, start_timestamp=start_timestamp)
                    else:
                        simulated_df = generator.sample_traces(N=n_traces_to_generate)
                except (ValueError, IndexError) as exc:
                    msg = str(exc)
                    _export_simulation_constraint_artifacts(sim_cache_root, out_dir, sim_id)
                    if _is_skippable_generation_error(msg):
                        print(f"[{case_study}] Skipping {scenario_name} sim_{sim_id}: {msg}")
                        scenario_skipped += 1
                        if not scenario_first_skip_reason:
                            scenario_first_skip_reason = msg
                        _append_row_csv(
                            skipped_out,
                            {
                                "case_study": case_study,
                                "scenario": scenario_name,
                                "simulation_id": sim_id,
                                "reason": msg,
                            },
                            skipped_columns,
                        )
                        skip_reason_counts[msg] = skip_reason_counts.get(msg, 0) + 1
                        _write_summary_checkpoints(
                            metrics_dir, grouped_stats=grouped_stats, skip_reason_counts=skip_reason_counts
                        )
                        del generator
                        continue
                    raise
                simulated_df.to_csv(sim_path, index=False)
                _export_simulation_constraint_artifacts(sim_cache_root, out_dir, sim_id)

                sim_log_cf = _sim_df_to_event_log(simulated_df)
                from log_distance_measures.n_gram_distribution import n_gram_distribution_distance
                from log_distance_measures.config import EventLogIDs

                try:
                    event_log_ids = EventLogIDs(
                        case="case:concept:name",
                        activity="concept:name",
                        start_time="time:timestamp",
                        end_time="time:timestamp",
                    )
                    # Simulated df has no timestamp; add synthetic one for event ordering
                    sim_for_dist = simulated_df.copy()
                    sim_for_dist["time:timestamp"] = (
                        pd.Timestamp("2000-01-01 00:00:00", tz="UTC")
                        + pd.to_timedelta(
                            sim_for_dist.groupby("case:concept:name").cumcount(),
                            unit="s",
                        )
                    )
                    req_cols = ["case:concept:name", "concept:name", "time:timestamp"]
                    if not all(c in reference_df_clean.columns for c in req_cols):
                        missing = [c for c in req_cols if c not in reference_df_clean.columns]
                        raise ValueError(
                            f"Reference for 2-gram missing columns {missing} "
                            f"(columns: {list(reference_df_clean.columns)}); "
                            "possibly all test traces filtered out as non-compliant."
                        )
                    if reference_df_clean.empty:
                        raise ValueError(
                            "Reference for 2-gram is empty (all test traces filtered out as non-compliant)."
                        )
                    ref_for_dist = reference_df_clean[req_cols].copy()
                    # Normalize activity names (ref has _lc:complete, simulated does not)
                    ref_for_dist["concept:name"] = ref_for_dist[
                        "concept:name"
                    ].astype(str).str.replace("_lc:complete", "", regex=False)
                    two_gram_distance = n_gram_distribution_distance(
                        sim_for_dist,
                        event_log_ids,
                        ref_for_dist,
                        event_log_ids,
                        n=2,
                    )
                except (ValueError, KeyError) as exc:
                    msg = str(exc)
                    if _is_skippable_generation_error(msg) or "reference for 2-gram" in msg.lower():
                        print(f"[{case_study}] Skipping {scenario_name} sim_{sim_id}: {msg}")
                        scenario_skipped += 1
                        if not scenario_first_skip_reason:
                            scenario_first_skip_reason = msg
                        _append_row_csv(
                            skipped_out,
                            {
                                "case_study": case_study,
                                "scenario": scenario_name,
                                "simulation_id": sim_id,
                                "reason": msg,
                            },
                            skipped_columns,
                        )
                        skip_reason_counts[msg] = skip_reason_counts.get(msg, 0) + 1
                        _write_summary_checkpoints(
                            metrics_dir, grouped_stats=grouped_stats, skip_reason_counts=skip_reason_counts
                        )
                        del sim_log_cf
                        del simulated_df
                        del generator
                        continue
                    raise

                ent = _entropy_from_dataframe(simulated_df)
                sim_metrics_path = out_dir / f"sim_{sim_id}_metrics.csv"
                pd.DataFrame([{"two_gram_distance": two_gram_distance, **ent}]).to_csv(
                    sim_metrics_path, index=False
                )

                per_sim_row = {
                    "case_study": case_study,
                    "scenario": scenario_name,
                    "simulation_id": sim_id,
                    "two_gram_distance": two_gram_distance,
                    **ent,
                }
                _append_row_csv(per_sim_out, per_sim_row, per_sim_columns)
                grouped_key = (case_study, scenario_name)
                if grouped_key not in grouped_stats:
                    grouped_stats[grouped_key] = _RunningStats()
                grouped_stats[grouped_key].update(
                    {
                        "two_gram_distance": two_gram_distance,
                        "prefix_entropy": ent["prefix_entropy"],
                        "trace_entropy": ent["trace_entropy"],
                    }
                )
                _write_summary_checkpoints(
                    metrics_dir, grouped_stats=grouped_stats, skip_reason_counts=skip_reason_counts
                )
                scenario_entropy_row = {
                    "simulation_id": sim_id,
                    "prefix_entropy": ent["prefix_entropy"],
                    "trace_entropy": ent["trace_entropy"],
                }
                _append_row_csv(scenario_entropy_path, scenario_entropy_row, scenario_entropy_columns)
                scenario_stats.update(
                    {
                        "prefix_entropy": scenario_entropy_row["prefix_entropy"],
                        "trace_entropy": scenario_entropy_row["trace_entropy"],
                    }
                )
                print(
                    f"[SIM DONE] use_case={case_study} scenario={scenario_name} simulation={sim_id}"
                )
                scenario_completed += 1
                del sim_log_cf
                del simulated_df
                del generator
                if (sim_id + 1) % GC_EVERY_N_SIMS == 0:
                    gc.collect()
                _enforce_ram_limit_or_exit(f"simulation end {case_study}/{scenario_name}/{sim_id}")

            summary_keys = [
                "prefix_entropy",
                "trace_entropy",
            ]
            if scenario_stats.n == 0:
                scenario_entropy_summary_df = pd.DataFrame(
                    columns=[
                        "prefix_entropy_mean",
                        "prefix_entropy_std",
                        "trace_entropy_mean",
                        "trace_entropy_std",
                    ]
                )
            else:
                scenario_entropy_summary_df = pd.DataFrame([scenario_stats.finalize(summary_keys)])
            scenario_entropy_summary_df.to_csv(out_dir / "scenario_entropy_summary.csv", index=False)
            if scenario_completed == 0:
                scenario_status = "not_runnable"
                not_runnable_reason = scenario_first_skip_reason or "all simulations skipped"
            elif scenario_skipped > 0:
                scenario_status = "partially_runnable"
                not_runnable_reason = ""
            else:
                scenario_status = "runnable"
                not_runnable_reason = ""
            scenario_status_rows.append(
                {
                    "case_study": case_study,
                    "scenario": scenario_name,
                    "requested_simulations": n_sim,
                    "completed_simulations": scenario_completed,
                    "skipped_simulations": scenario_skipped,
                    "status": scenario_status,
                    "reason_if_not_runnable": not_runnable_reason,
                }
            )
            del scenario_entropy_summary_df
            gc.collect()

        del log_for_generator
        del reference_log_lc
        del baseline_df
        del baseline_df_clean
        gc.collect()

    print("\nStep 3/4 - Computing summary statistics (mean/std over simulations)")
    if not per_sim_out.exists():
        pd.DataFrame(columns=per_sim_columns).to_csv(per_sim_out, index=False)
    if not skipped_out.exists():
        pd.DataFrame(columns=skipped_columns).to_csv(skipped_out, index=False)
    pd.DataFrame(scenario_status_rows, columns=scenario_status_columns).to_csv(
        scenario_status_out, index=False
    )

    summary = _build_summary_dataframe(grouped_stats)
    summary_out = metrics_dir / "summary_mean_std_metrics.csv"
    summary.to_csv(summary_out, index=False)
    skipped_by_reason_out = metrics_dir / "skipped_summary_by_reason.csv"
    skipped_by_reason_df = (
        pd.DataFrame(
            [{"reason": reason, "count": count} for reason, count in skip_reason_counts.items()]
        )
        .sort_values("count", ascending=False, ignore_index=True)
        if skip_reason_counts
        else pd.DataFrame(columns=["reason", "count"])
    )
    skipped_by_reason_df.to_csv(skipped_by_reason_out, index=False)

    print("\nStep 4/4 - Saving full-log reference metrics and final report")
    _build_intersection_bottleneck_reports(constraints_dir=constraints_dir, metrics_dir=metrics_dir)
    if full_log_metrics_out.exists():
        shutil.copy2(full_log_metrics_out, metrics_dir / "full_log_entropy.csv")
    else:
        pd.DataFrame(columns=full_log_metrics_columns).to_csv(full_log_metrics_out, index=False)
        shutil.copy2(full_log_metrics_out, metrics_dir / "full_log_entropy.csv")

    with open(metrics_dir / "README_results.txt", "w") as f:
        f.write("Results generated with N_SIM=%d for scenarios A, B, C.\n" % n_sim)
        f.write("Constraint selection mode: no-threshold, deterministic top-N.\n")
        f.write(f"Constraint ranking mode: {ranking_mode}\n")
        f.write(f"Constraint sample size per simulation: {constraints_per_simulation}\n")
        f.write("Metrics include 2-gram distance and entropy per simulation and mean/std summaries.\n")
        f.write("Constraints are mined from full logs and cached per case study.\n")
        f.write(
            f"Fixed top constraints used in every simulation: {constraints_per_simulation}.\n"
        )
        f.write(f"Per-simulation metrics: {per_sim_out}\n")
        f.write(f"Summary (mean/std): {summary_out}\n")
        f.write(f"Original full-log metrics (2-gram distance + entropies): {full_log_metrics_out}\n")
        f.write(f"Skipped scenarios/simulations: {skipped_out}\n")
        f.write(f"Scenario run-status report: {scenario_status_out}\n")
        f.write(f"Skipped summary by reason: {skipped_by_reason_out}\n")
        f.write(
            f"Intersection bottlenecks (top 50 by time): "
            f"{metrics_dir / 'intersection_bottlenecks_top.csv'}\n"
        )
        f.write(
            f"Intersection skip reasons: {metrics_dir / 'intersection_skip_reasons.csv'}\n"
        )

    skipped_count = int(sum(skip_reason_counts.values()))
    if skipped_count == 0:
        print("Skip summary: no skipped scenarios/simulations.")
    else:
        print(f"Skip summary: {skipped_count} skipped entries.")
        print("Top skip reasons:")
        for _, row in skipped_by_reason_df.iterrows():
            print(f"  - {row['reason']}: {int(row['count'])}")

    print("\nPipeline completed successfully.")
    print(f"All outputs saved under: {config_root}")


def run_pipeline(
    n_sim: int,
    output_root: Path,
    ranking_mode: str,
    case_studies: dict,
    default_k: int = DEFAULT_K,
    seed: int | None = None,
    train_split_ratio: float = 0.5,
    use_train_test_split: bool | None = None,
    filter_reference_by_constraints: bool | None = None,
):
    output_root.mkdir(parents=True, exist_ok=True)
    for constraints_per_simulation in CONSTRAINTS_PER_SIMULATION_SETS:
        _enforce_ram_limit_or_exit(
            f"experimental set start (constraints_per_simulation={constraints_per_simulation})"
        )
        run_pipeline_for_config(
            n_sim=n_sim,
            output_root=output_root,
            constraints_per_simulation=constraints_per_simulation,
            ranking_mode=ranking_mode,
            case_studies=case_studies,
            default_k=default_k,
            seed=seed,
            train_split_ratio=train_split_ratio,
            use_train_test_split=use_train_test_split,
            filter_reference_by_constraints=filter_reference_by_constraints,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Run five-case-study pipeline with full-log constraint mining and A/B/C simulations."
    )
    parser.add_argument(
        "--n-sim",
        type=int,
        default=10,
        help="Number of simulations per scenario (default: 10).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "five_case_results"),
        help="Output directory for constraints, splits, simulations and metrics.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "data"),
        help="Root folder where .xes/.csv event logs are discovered recursively.",
    )
    parser.add_argument(
        "--cases",
        nargs="*",
        default=[],
        help=(
            "Optional case names to run (names are inferred from parent folder, "
            "e.g., Production, lending, cvs). If omitted, all discovered logs are used."
        ),
    )
    parser.add_argument(
        "--default-k",
        type=int,
        default=DEFAULT_K,
        help="Default Markov prefix length k for newly discovered cases (default: 2).",
    )
    parser.add_argument(
        "--ranking-mode",
        choices=["satisfied_ratio", "support_confidence"],
        default=DEFAULT_RANKING_MODE,
        help=(
            "Constraint ranking mode used during deterministic top-N selection: "
            "'satisfied_ratio' or 'support_confidence'."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help="Random seed for reproducibility. Also settable via RANDOM_SEED env.",
    )
    parser.add_argument(
        "--train-split-ratio",
        type=float,
        default=0.5,
        metavar="R",
        help=(
            "Fraction of traces for train set when train/test split is enabled (default: 0.5). "
            "Set via TRAIN_TEST_SPLIT_RATIO env when using run script."
        ),
    )
    def _parse_bool(v):
        s = str(v).lower()
        if s in ("1", "true", "yes"):
            return True
        if s in ("0", "false", "no"):
            return False
        raise ValueError(f"Expected 0/1 or true/false, got: {v}")

    parser.add_argument(
        "--use-train-test-split",
        type=_parse_bool,
        default=None,
        metavar="0|1",
        help=(
            "Use train/test split (1) or whole log (0). Default from USE_TRAIN_TEST_SPLIT_50 env."
        ),
    )
    parser.add_argument(
        "--filter-reference-by-constraints",
        type=_parse_bool,
        default=None,
        metavar="0|1",
        help=(
            "Filter 2-gram reference by constraints (1) or use unfiltered reference (0). "
            "Default from FILTER_REFERENCE_BY_CONSTRAINTS env."
        ),
    )
    args = parser.parse_args()
    seed_env = os.environ.get("RANDOM_SEED", "").strip()
    if args.seed is None and seed_env:
        args.seed = int(seed_env)
    ratio_env = os.environ.get("TRAIN_TEST_SPLIT_RATIO", "").strip()
    if ratio_env:
        args.train_split_ratio = float(ratio_env)
    split_env = os.environ.get("USE_TRAIN_TEST_SPLIT_50", "").strip()
    if args.use_train_test_split is None and split_env:
        args.use_train_test_split = split_env == "1"
    filter_env = os.environ.get("FILTER_REFERENCE_BY_CONSTRAINTS", "").strip()
    if args.filter_reference_by_constraints is None and filter_env:
        args.filter_reference_by_constraints = filter_env != "0"

    if args.n_sim <= 0:
        raise ValueError("--n-sim must be > 0")
    if args.default_k <= 0:
        raise ValueError("--default-k must be > 0")
    if args.train_split_ratio <= 0 or args.train_split_ratio >= 1:
        raise ValueError("--train-split-ratio must be strictly between 0 and 1")

    case_studies = _build_case_studies(
        data_dir=Path(args.data_dir),
        selected_cases=args.cases,
        default_k=args.default_k,
    )
    print("Discovered case studies:")
    for case_name, cfg in case_studies.items():
        print(f"  - {case_name}: {cfg['path_log']}")

    run_pipeline(
        n_sim=args.n_sim,
        output_root=Path(args.output_dir),
        ranking_mode=args.ranking_mode,
        case_studies=case_studies,
        default_k=args.default_k,
        seed=args.seed,
        train_split_ratio=args.train_split_ratio,
        use_train_test_split=args.use_train_test_split,
        filter_reference_by_constraints=args.filter_reference_by_constraints,
    )


if __name__ == "__main__":
    main()
