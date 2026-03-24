import argparse
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from pm4py.algo.conformance.declare import algorithm as declare_conformance
from pm4py.algo.discovery.declare import algorithm as declare_discovery
from pm4py.algo.discovery.declare.variants import classic as declare_classic
from pm4py.objects.log.importer.xes import importer as xes_importer


def _count_rules(model: Dict[str, Dict[Any, Dict[str, int]]]) -> int:
    """Count mined Declare rules in the discovered model."""
    return sum(len(rules) for rules in model.values())


def _normalize_threshold(value: float, name: str) -> float:
    """
    Accept threshold as ratio (0..1) or percentage (0..100).
    Returns the normalized ratio in 0..1.
    """
    if 0.0 <= value <= 1.0:
        return value
    if 1.0 < value <= 100.0:
        return value / 100.0
    raise ValueError(f"{name} must be in [0,1] (ratio) or [0,100] (percentage). Got: {value}")


def _threshold_to_token(value: float) -> str:
    """Convert ratio threshold to a filesystem-safe token."""
    return f"{value:.4f}".replace(".", "p")


def _process_log(
    log_path: Path,
    min_support: float,
    min_confidence: float,
) -> Dict[str, Any]:
    """Load one event log, mine Declare constraints, and verify traces."""
    log = xes_importer.apply(str(log_path))

    parameters = {
        declare_classic.Parameters.MIN_SUPPORT_RATIO: min_support,
        declare_classic.Parameters.MIN_CONFIDENCE_RATIO: min_confidence,
        declare_classic.Parameters.ACTIVITY_KEY: "concept:name",
    }
    # Mine and verify on the same event log only (no cross-log constraints reuse).
    mined_model_for_this_log = declare_discovery.apply(log, parameters=parameters)
    conformance = declare_conformance.apply(log, mined_model_for_this_log)

    fit_trace_indexes = [idx for idx, result in enumerate(conformance) if result.get("is_fit")]
    first_fit_trace_index = fit_trace_indexes[0] if fit_trace_indexes else None

    return {
        "dataset": str(log_path),
        "num_traces": len(log),
        "num_constraints": _count_rules(mined_model_for_this_log),
        "fit_traces_count": len(fit_trace_indexes),
        "exists_trace_satisfying_all_constraints": bool(fit_trace_indexes),
        "first_fit_trace_index": first_fit_trace_index,
    }


def process_all_datasets(
    base_dir: Path,
    min_support: float,
    min_confidence: float,
) -> pd.DataFrame:
    """Apply mining + per-trace verification to all XES datasets in a folder."""
    if not base_dir.exists():
        raise FileNotFoundError(f"Directory not found: {base_dir}")

    def _is_split_log(path: Path) -> bool:
        """Exclude train/test split logs and keep only full logs."""
        stem = path.stem.lower()
        return stem in {"logtrain", "logtest", "train", "test"}

    xes_files = sorted(path for path in base_dir.rglob("*.xes") if not _is_split_log(path))
    if not xes_files:
        raise FileNotFoundError(
            f"No full .xes datasets found in: {base_dir} (train/test splits are excluded)."
        )

    rows: List[Dict[str, Any]] = []
    for dataset in xes_files:
        print(f"\n=== Processing {dataset} ===")
        row = _process_log(
            log_path=dataset,
            min_support=min_support,
            min_confidence=min_confidence,
        )
        rows.append(row)
        print(
            "constraints={num_constraints} traces={num_traces} fit_traces={fit_traces_count} "
            "exists_fit_trace={exists_trace_satisfying_all_constraints}".format(**row)
        )

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "For each XES dataset, mine Declare constraints with PM4Py and verify "
            "whether at least one trace satisfies all mined constraints."
        )
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Base folder containing datasets (.xes files). Default: data",
    )
    parser.add_argument(
        "--min-support",
        type=float,
        default=0.0,
        help="Minimum support threshold: ratio [0,1] or percentage [0,100]. Default: 0.0",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence threshold: ratio [0,1] or percentage [0,100]. Default: 0.0",
    )
    parser.add_argument(
        "--output-dir",
        default="check_declare_outputs",
        help="Dedicated folder where result CSV files are saved. Default: check_declare_outputs",
    )
    parser.add_argument(
        "--output-prefix",
        default="check_declare_results",
        help="Base filename prefix. Threshold tokens are appended automatically.",
    )
    args = parser.parse_args()

    try:
        min_support = _normalize_threshold(args.min_support, "--min-support")
        min_confidence = _normalize_threshold(args.min_confidence, "--min-confidence")
    except ValueError as exc:
        parser.error(str(exc))

    print(
        f"Using thresholds -> min_support={min_support:.4f}, min_confidence={min_confidence:.4f}"
    )

    results = process_all_datasets(
        base_dir=Path(args.data_dir),
        min_support=min_support,
        min_confidence=min_confidence,
    )

    print("\n=== Summary ===")
    print(
        results[
            [
                "dataset",
                "num_traces",
                "num_constraints",
                "fit_traces_count",
                "exists_trace_satisfying_all_constraints",
                "first_fit_trace_index",
            ]
        ].to_string(index=False)
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = (
        f"{args.output_prefix}"
        f"_support_{_threshold_to_token(min_support)}"
        f"_confidence_{_threshold_to_token(min_confidence)}.csv"
    )
    output_path = output_dir / output_name
    results.to_csv(output_path, index=False)
    print(f"\nSaved results to: {output_path}")


if __name__ == "__main__":
    main()
