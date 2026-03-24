#!/usr/bin/env python3
"""
Evaluate CVAE-generated logs from cvae/ subfolders:
- 2-gram distance vs original log
- Prefix and trace entropy
- Percentage of traces violating constraint sets (5, 10, 25, 50)

Also evaluates Scenario C simulations from five_case_results checkpoint:
- Constraint violation % for sim_0.csv per config and case study
"""

import argparse
import os
import re
import sys
import types
from pathlib import Path

import pandas as pd
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer

ROOT = Path(__file__).resolve().parent
from data_paths import DATASET_FILES, LEGACY_CASE_TO_ID, path_for  # noqa: E402

FRAMEWORK_DIR = ROOT / "ConstraintBasedEventLogGenerator"
if str(FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_DIR))

# Expose framework constraints package
constraints_pkg = types.ModuleType("constraints")
constraints_pkg.__path__ = [str(FRAMEWORK_DIR / "constraints")]
sys.modules["constraints"] = constraints_pkg

# Match five_case_pipeline constraint discovery
os.environ.setdefault("DECLARE_USE_FORM_RULES_TABLE", "1")
os.environ.setdefault("DECLARE_CONSTRAINT_RANKING_MODE", "support_confidence")

from constraints.constants import END_PLACEHOLDER  # noqa: E402
from constraints.constraints_per_log import get_top_k_mined_constraints, trace_satisfies_constraint  # noqa: E402
from constraints.utils_ts import extract_event_seqs_and_alphabet  # noqa: E402
from src.entropies import convert_and_clean, cf_entropy_seq  # noqa: E402

def _build_case_study_mapping() -> dict[str, Path]:
    """Map CVAE folder names and legacy checkpoint case labels to log paths."""
    m: dict[str, Path] = {}
    for ds in DATASET_FILES:
        m[ds] = path_for(ds)
    for legacy in LEGACY_CASE_TO_ID:
        m[legacy] = path_for(legacy)
    return m


CVAE_TO_ORIGINAL = _build_case_study_mapping()
CASE_STUDY_TO_ORIGINAL = _build_case_study_mapping()

CONSTRAINT_SETS = [5, 10, 25, 50]


def _pick_first_existing_column(df: pd.DataFrame, candidates: list[str]):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _load_csv_log(path: Path, sep: str = ",") -> pd.DataFrame:
    """Load CSV log, normalizing to standard columns."""
    df = pd.read_csv(path, sep=sep)
    if df.empty:
        raise ValueError(f"CSV is empty: {path}")

    case_col = _pick_first_existing_column(
        df, ["case:concept:name", "case:variant", "case_id", "caseid", "case", "Case ID"]
    )
    act_col = _pick_first_existing_column(
        df, ["concept:name", "activity", "Activity", "event", "event_name", "task"]
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
    # Drop rows with missing case or activity
    work_df = work_df[
        work_df["case:concept:name"].notna() & (work_df["case:concept:name"] != "nan")
    ].copy()
    work_df = work_df[work_df["concept:name"].notna() & (work_df["concept:name"] != "")].copy()

    if ts_col is not None:
        work_df["time:timestamp"] = pd.to_datetime(work_df[ts_col], errors="coerce", utc=True)
        if work_df["time:timestamp"].isna().all():
            ts_col = None

    if ts_col is None:
        work_df["__event_order"] = work_df.groupby("case:concept:name").cumcount()
        base_ts = pd.Timestamp("2000-01-01 00:00:00", tz="UTC")
        work_df["time:timestamp"] = base_ts + pd.to_timedelta(work_df["__event_order"], unit="s")
        work_df = work_df.drop(columns=["__event_order"])

    return work_df


def _load_event_log(path: Path):
    """Load XES or CSV into PM4Py EventLog."""
    suffix = path.suffix.lower()
    if suffix == ".xes":
        return xes_importer.apply(str(path))
    if suffix == ".csv":
        with open(path, encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
        sep = ";" if first_line.count(";") >= first_line.count(",") else ","
        df = _load_csv_log(path, sep=sep)
        df = pm4py.format_dataframe(
            df,
            case_id="case:concept:name",
            activity_key="concept:name",
            timestamp_key="time:timestamp",
        )
        return pm4py.convert_to_event_log(df)
    raise ValueError(f"Unsupported format: {path}")


def _prepare_for_distance(df: pd.DataFrame, filter_complete: bool = True):
    """Ensure df has case:concept:name, concept:name, time:timestamp."""
    work = df.copy()
    if filter_complete and "lifecycle:transition" in work.columns:
        work = work[work["lifecycle:transition"] == "complete"].copy()
    out = work[["case:concept:name", "concept:name"]].copy()
    if "time:timestamp" in work.columns:
        out["time:timestamp"] = pd.to_datetime(work["time:timestamp"], errors="coerce")
    else:
        out["time:timestamp"] = (
            pd.Timestamp("2000-01-01 00:00:00", tz="UTC")
            + pd.to_timedelta(out.groupby("case:concept:name").cumcount(), unit="s")
        )
    return out


def _compute_two_gram_distance(gen_df: pd.DataFrame, orig_df: pd.DataFrame) -> float:
    from log_distance_measures.n_gram_distribution import n_gram_distribution_distance
    from log_distance_measures.config import EventLogIDs

    event_log_ids = EventLogIDs(
        case="case:concept:name",
        activity="concept:name",
        start_time="time:timestamp",
        end_time="time:timestamp",
    )
    gen_prep = _prepare_for_distance(gen_df)
    orig_prep = _prepare_for_distance(orig_df)
    # Normalize _lc:complete if present
    if "concept:name" in orig_prep.columns:
        orig_prep = orig_prep.copy()
        orig_prep["concept:name"] = orig_prep["concept:name"].astype(str).str.replace("_lc:complete", "", regex=False)
    return n_gram_distribution_distance(gen_prep, event_log_ids, orig_prep, event_log_ids, n=2)


def _compute_entropy(df: pd.DataFrame) -> dict:
    """Return prefix_entropy and trace_entropy (same logic as five_case_pipeline)."""
    act_col = _pick_first_existing_column(df, ["concept:name", "activity", "Activity"])
    case_col = _pick_first_existing_column(df, ["case:concept:name", "case:variant", "case_id"])
    if not act_col or not case_col:
        return {"prefix_entropy": float("nan"), "trace_entropy": float("nan")}
    work = df[[case_col, act_col]].copy()
    work.columns = ["case:concept:name", "concept:name"]
    work["case:concept:name"] = work["case:concept:name"].astype(str)
    if "lifecycle:transition" in df.columns and (df["lifecycle:transition"] == "complete").any():
        work = df.loc[df["lifecycle:transition"] == "complete", [case_col, act_col]].copy()
        work.columns = ["case:concept:name", "concept:name"]
        work["case:concept:name"] = work["case:concept:name"].astype(str)
    prefix_entropy = cf_entropy_seq(work, prefix=True)
    trace_entropy = cf_entropy_seq(work, prefix=False)
    return {"prefix_entropy": prefix_entropy, "trace_entropy": trace_entropy}


def _trace_to_events(trace: list) -> list:
    """Convert list of activity names to list of event dicts for trace_satisfies_constraint."""
    return [{"concept:name": act} for act in trace]


def _compute_violation_pct(gen_log, orig_log, k: int, alphabet: list) -> float:
    """
    Compute percentage of traces in gen_log that violate at least one of the top-k constraints
    mined from orig_log.
    """
    constraints_list = get_top_k_mined_constraints(orig_log, alphabet, k)
    if not constraints_list:
        return float("nan")

    nfa_cache = {}
    traces_list = list(gen_log)
    violating_count = 0

    for trace in traces_list:
        trace_events = _trace_to_events([e["concept:name"] for e in trace])
        violates_any = False
        for (template, acts) in constraints_list:
            if not trace_satisfies_constraint(trace_events, template, acts, alphabet, nfa_cache):
                violates_any = True
                break
        if violates_any:
            violating_count += 1

    n_traces = len(traces_list)
    return 100.0 * (violating_count / n_traces) if n_traces > 0 else float("nan")


def discover_cvae_logs(cvae_root: Path) -> dict[str, list[Path]]:
    """Discover generated logs per cvae subfolder. Returns {folder_name: [gen1.csv, gen2.csv, ...]}."""
    result = {}
    for subdir in sorted(cvae_root.iterdir()):
        if not subdir.is_dir():
            continue
        gen_dir = subdir / "generated_datasets"
        if not gen_dir.exists():
            continue
        logs = []
        for f in sorted(gen_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in (".csv", ".xes"):
                logs.append(f)
        if logs:
            result[subdir.name] = logs
    return result


def discover_scenario_c_logs(scenario_c_root: Path) -> list[tuple[str, str, Path]]:
    """
    Discover Scenario C sim_0.csv files under five_case_results structure.
    Path pattern: {root}/constraints_{n}_k_{m}/simulations/{case_study}/scenarioC/sim_0.csv

    Returns: [(config_name, case_study, sim_path), ...]
    """
    found = []
    config_match = re.compile(r"^constraints_(\d+)_k_(\d+)$")
    for config_dir in sorted(scenario_c_root.iterdir()):
        if not config_dir.is_dir():
            continue
        m = config_match.match(config_dir.name)
        if not m:
            continue
        sims_dir = config_dir / "simulations"
        if not sims_dir.exists():
            continue
        for case_dir in sorted(sims_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            scenario_c_dir = case_dir / "scenarioC"
            sim_path = scenario_c_dir / "sim_0.csv"
            if sim_path.exists():
                found.append((config_dir.name, case_dir.name, sim_path))
    return found


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate CVAE-generated logs: 2-gram distance, entropy, constraint violation %."
    )
    parser.add_argument(
        "--cvae-dir",
        default=str(ROOT / "cvae"),
        help="Root folder containing CVAE subfolders (e.g. cvae/ds01).",
    )
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "data"),
        help="Root folder for original logs.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "cvae_evaluation_results.csv"),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--map",
        nargs="*",
        default=[],
        help="Override mappings as 'cvae_folder:path/to/original.xes' (e.g. myfolder:data/My/log.xes).",
    )
    parser.add_argument(
        "--scenario-c-dir",
        default=str(ROOT / "five_case_results checkpoint"),
        help="Root folder for Scenario C sims (e.g. five_case_results checkpoint). Evaluates sim_0.csv for constraint violation.",
    )
    parser.add_argument(
        "--case-studies",
        nargs="*",
        default=["ds06"],
        help="Restrict to these case studies only (e.g. ds06). CVAE folder name or pipeline case study name.",
    )
    args = parser.parse_args()

    cvae_root = Path(args.cvae_dir)
    if not cvae_root.exists():
        print(f"Error: cvae dir does not exist: {cvae_root}")
        sys.exit(1)

    scenario_c_root = Path(args.scenario_c_dir).resolve() if args.scenario_c_dir else None

    # Build mapping (default + overrides)
    mapping = dict(CVAE_TO_ORIGINAL)
    for spec in args.map:
        if ":" in spec:
            cvae_name, orig_path = spec.split(":", 1)
            mapping[cvae_name.strip()] = Path(orig_path.strip())

    # Resolve original paths relative to data_dir if needed
    data_dir = Path(args.data_dir)
    for k, v in list(mapping.items()):
        if not v.is_absolute():
            mapping[k] = ROOT / v
        if not mapping[k].exists():
            mapping[k] = data_dir / v

    case_studies_filter = set(args.case_studies) if args.case_studies else None

    discovered = discover_cvae_logs(cvae_root)
    rows = []
    if discovered:
        for cvae_name, gen_paths in discovered.items():
            if case_studies_filter and cvae_name not in case_studies_filter:
                continue
            if cvae_name not in mapping:
                print(f"Skipping {cvae_name}: no mapping to original log. Add with --map {cvae_name}:path/to/log.xes")
                continue

            orig_path = mapping[cvae_name]
            if not orig_path.exists():
                print(f"Skipping {cvae_name}: original log not found: {orig_path}")
                continue

            print(f"\nEvaluating {cvae_name} -> {orig_path.name}")
            orig_log = _load_event_log(orig_path)
            orig_df = pm4py.convert_to_dataframe(orig_log)
            event_seqs, alphabet = extract_event_seqs_and_alphabet(orig_log)
            from constraints.constants import START_PLACEHOLDER

            alphabet_full = sorted(set(alphabet) | {START_PLACEHOLDER, END_PLACEHOLDER})

            for gen_path in gen_paths:
                try:
                    gen_log = _load_event_log(gen_path)
                    gen_df = pm4py.convert_to_dataframe(gen_log)
                except Exception as e:
                    print(f"  Error loading {gen_path.name}: {e}")
                    continue

                # Extend alphabet with any activities from generated log
                gen_activities = set()
                for trace in gen_log:
                    gen_activities.update(e["concept:name"] for e in trace)
                alphabet_for_gen = sorted(set(alphabet_full) | gen_activities)

                two_gram = _compute_two_gram_distance(gen_df, orig_df)
                ent = _compute_entropy(gen_df)

                violation_pcts = {}
                for k in CONSTRAINT_SETS:
                    violation_pcts[f"pct_violating_top_{k}"] = _compute_violation_pct(
                        gen_log, orig_log, k, alphabet_for_gen
                    )

                rows.append({
                    "case_study": cvae_name,
                    "generated_log": gen_path.name,
                    "source": "cvae",
                    "config": "",
                    "two_gram_distance": two_gram,
                    "prefix_entropy": ent["prefix_entropy"],
                    "trace_entropy": ent["trace_entropy"],
                    **violation_pcts,
                })
                print(
                    f"  {gen_path.name}: 2-gram={two_gram:.4f}, "
                    f"prefix_ent={ent['prefix_entropy']:.4f}, trace_ent={ent['trace_entropy']:.4f}, "
                    f"violating_5={violation_pcts['pct_violating_top_5']:.1f}%, "
                    f"violating_10={violation_pcts['pct_violating_top_10']:.1f}%, "
                    f"violating_25={violation_pcts['pct_violating_top_25']:.1f}%, "
                    f"violating_50={violation_pcts['pct_violating_top_50']:.1f}%"
                )

    # Scenario C: evaluate sim_0.csv constraint violation
    if scenario_c_root and scenario_c_root.exists():
        from constraints.constants import START_PLACEHOLDER

        discovered_sc = discover_scenario_c_logs(scenario_c_root)
        print(f"\n--- Scenario C: found {len(discovered_sc)} sim_0.csv files ---")
        data_dir = Path(args.data_dir)

        for config_name, case_study, sim_path in discovered_sc:
            if case_studies_filter and case_study not in case_studies_filter:
                continue
            if case_study not in CASE_STUDY_TO_ORIGINAL:
                print(f"  Skipping {config_name}/{case_study}: no mapping. Add to CASE_STUDY_TO_ORIGINAL.")
                continue
            orig_path = CASE_STUDY_TO_ORIGINAL[case_study]
            if not orig_path.is_absolute():
                orig_path = ROOT / orig_path
            if not orig_path.exists():
                orig_path = data_dir / orig_path
            if not orig_path.exists():
                print(f"  Skipping {config_name}/{case_study}: original log not found: {orig_path}")
                continue

            try:
                orig_log = _load_event_log(orig_path)
                sim_log = _load_event_log(sim_path)
                sim_df = pm4py.convert_to_dataframe(sim_log)
            except Exception as e:
                print(f"  Error loading {config_name}/{case_study}: {e}")
                continue

            event_seqs, alphabet = extract_event_seqs_and_alphabet(orig_log)
            alphabet_full = sorted(set(alphabet) | {START_PLACEHOLDER, END_PLACEHOLDER})
            sim_activities = set()
            for trace in sim_log:
                sim_activities.update(e["concept:name"] for e in trace)
            alphabet_for_sim = sorted(set(alphabet_full) | sim_activities)

            orig_df = pm4py.convert_to_dataframe(orig_log)
            two_gram = _compute_two_gram_distance(sim_df, orig_df)
            ent = _compute_entropy(sim_df)
            violation_pcts = {}
            for k in CONSTRAINT_SETS:
                violation_pcts[f"pct_violating_top_{k}"] = _compute_violation_pct(
                    sim_log, orig_log, k, alphabet_for_sim
                )

            rows.append({
                "case_study": case_study,
                "generated_log": f"{config_name}/scenarioC/sim_0.csv",
                "source": "scenario_c",
                "config": config_name,
                "two_gram_distance": two_gram,
                "prefix_entropy": ent["prefix_entropy"],
                "trace_entropy": ent["trace_entropy"],
                **violation_pcts,
            })
            print(
                f"  {config_name}/{case_study}: 2-gram={two_gram:.4f}, "
                f"prefix_ent={ent['prefix_entropy']:.4f}, trace_ent={ent['trace_entropy']:.4f}, "
                f"violating_5={violation_pcts['pct_violating_top_5']:.1f}%, "
                f"violating_10={violation_pcts['pct_violating_top_10']:.1f}%, "
                f"violating_25={violation_pcts['pct_violating_top_25']:.1f}%, "
                f"violating_50={violation_pcts['pct_violating_top_50']:.1f}%"
            )

    if not rows:
        print("No evaluations completed.")
        sys.exit(0)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
