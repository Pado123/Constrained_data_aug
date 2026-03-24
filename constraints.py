import argparse
import pandas as pd
from pathlib import Path
import sys
import time
import warnings
import types
from tqdm import tqdm

from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.discovery.declare import algorithm as declare_miner
from pm4py.algo.discovery.declare.variants import classic as declare_classic

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
from data_paths import path_for  # noqa: E402


def _rel_log(ds: str) -> str:
    return str(path_for(ds).relative_to(ROOT))


CASE_STUDY_CONFIG = {
    "bpi12": {
        "path_log": "data/bpi12/BPI_Challenge_2012.xes",
        "save_split_to": "data/bpi12",
        "save_simulations_to": "simulations/bpi12",
        "label_data_attributes": [],
        "k": 3,
    },
    "bpi12a": {
        "path_log": "data/bpi12a/bpi12a_pp.xes",
        "save_split_to": "data/bpi12a",
        "save_simulations_to": "simulations/bpi12a",
        "label_data_attributes": ["AMOUNT_REQ"],
        "k": 3,
    },
    "bpi12o": {
        "path_log": "data/bpi12o/bpi12o_pp.xes",
        "save_split_to": "data/bpi12o",
        "save_simulations_to": "simulations/bpi12o",
        "label_data_attributes": ["AMOUNT_REQ"],
        "k": 3,
    },
    "bpi17": {
        "path_log": "data/bpi17/BPI Challenge 2017 - Offer log.xes",
        "save_split_to": "data/bpi17",
        "save_simulations_to": "simulations/bpi17",
        "label_data_attributes": [],
        "k": 3,
    },
    "bpi17o": {
        "path_log": "data/bpi17o/bpi17o_pp.xes",
        "save_split_to": "data/bpi17o",
        "save_simulations_to": "simulations/bpi17o",
        "label_data_attributes": ["MonthlyCost", "OfferedAmount"],
        "k": 3,
    },
    "ds01": {
        "path_log": _rel_log("ds01"),
        "save_split_to": "data/ds01",
        "save_simulations_to": "simulations/ds01",
        "label_data_attributes": [],
        "k": 3,
    },
    "ds02": {
        "path_log": _rel_log("ds02"),
        "save_split_to": "data/ds02",
        "save_simulations_to": "simulations/ds02",
        "label_data_attributes": [],
        "k": 3,
    },
    "ds03": {
        "path_log": _rel_log("ds03"),
        "save_split_to": "data/ds03",
        "save_simulations_to": "simulations/ds03",
        "label_data_attributes": [
            "ATTR_1",
            "ATTR_2",
            "ATTR_3",
            "ATTR_4",
            "ATTR_5",
            "ATTR_6",
            "ATTR_7",
        ],
        "k": 3,
    },
    "ds04": {
        "path_log": _rel_log("ds04"),
        "save_split_to": "data/ds04",
        "save_simulations_to": "simulations/ds04",
        "label_data_attributes": [],
        "k": 3,
    },
    "ds05": {
        "path_log": _rel_log("ds05"),
        "save_split_to": "data/ds05",
        "save_simulations_to": "simulations/ds05",
        "label_data_attributes": [],
        "k": 3,
    },
    "ds06": {
        "path_log": _rel_log("ds06"),
        "save_split_to": "data/ds06",
        "save_simulations_to": "simulations/ds06",
        "label_data_attributes": ["ATTR_WAIT_TIME", "ATTR_URGENCY", "ATTR_ARRIVAL_MODE"],
        "k": 3,
    },
}


def _compute_interest_factor(
    activities,
    support_count: float,
    confidence_count: float,
    existence_prob_map: dict,
):
    """
    Compute an interest score for a discovered Declare rule.
    - Unary constraints: IF = confidence/support (coverage ratio).
    - Binary constraints (A,B): IF ~ lift-like ratio = P(rule) / P(B),
      where P(B) is estimated from mined Existence(B).
    """
    if not support_count:
        return 0.0
    p_rule = confidence_count / support_count
    if isinstance(activities, tuple) and len(activities) == 2:
        consequent = activities[1]
        p_consequent = existence_prob_map.get(consequent)
        if p_consequent and p_consequent > 0:
            return p_rule / p_consequent
    return p_rule


def _compute_cpir(
    activities,
    support_count: float,
    confidence_count: float,
    existence_prob_map: dict,
):
    """
    Compute CPIR (Conditional-Probability Increment Ratio):
        (P(B|A) - P(B)) / (P(B) * (1 - P(B)))
    for binary rules A -> B.
    For unary rules or degenerate denominators, returns 0.0.
    """
    if not isinstance(activities, tuple) or len(activities) != 2 or not support_count:
        return 0.0
    p_b_given_a = confidence_count / support_count
    p_b = existence_prob_map.get(activities[1], 0.0)
    denom = p_b * (1.0 - p_b)
    if denom <= 0:
        return 0.0
    return (p_b_given_a - p_b) / denom


def mine_declare_constraints(log_path, min_support=0, min_confidence=0):
    """
    Mine Declare constraints from an event log.

    Parameters:
        log_path (str): Path to XES event log
        min_support (float): Minimum support ratio (0-1)
        min_confidence (float): Minimum confidence ratio (0-1)

    Returns:
        constraints_df (pd.DataFrame): DataFrame of discovered constraints
    """

    # Load event log
    print(f"Loading log: {log_path}")
    log = xes_importer.apply(log_path)

    print("Running Declare miner...")

    # Apply Declare miner
    parameters = {
        declare_classic.Parameters.MIN_SUPPORT_RATIO: min_support,
        declare_classic.Parameters.MIN_CONFIDENCE_RATIO: min_confidence,
        declare_classic.Parameters.ACTIVITY_KEY: "concept:name",
    }

    model = declare_miner.apply(log, parameters=parameters)
    n_traces = len(log)

    constraints_data = []

    # Estimate event marginal probabilities from mined existence constraints.
    existence_prob_map = {}
    existence_rules = model.get("existence", {})
    for event_name, metrics in existence_rules.items():
        sup = metrics.get("support", 0) or 0
        conf = metrics.get("confidence", 0) or 0
        existence_prob_map[event_name] = (conf / sup) if sup else 0.0

    total_rules = sum(len(rules) for rules in model.values())
    # PM4Py returns: {template_name: {activity_or_pair: {"support": ..., "confidence": ...}}}
    with tqdm(
        total=total_rules,
        desc="Processing mined constraints",
        unit="rule",
        file=sys.stdout,
        dynamic_ncols=True,
        disable=False,
    ) as pbar:
        for template_name, rules in model.items():
            for activities, metrics in rules.items():
                if isinstance(activities, tuple):
                    activities_repr = ", ".join(activities)
                else:
                    activities_repr = activities
                support_count = metrics.get("support", 0) or 0
                confidence_count = metrics.get("confidence", 0) or 0
                support_pct = (support_count / n_traces * 100) if n_traces else 0.0
                confidence_pct = (confidence_count / n_traces * 100) if n_traces else 0.0
                interest_factor = _compute_interest_factor(
                    activities,
                    support_count,
                    confidence_count,
                    existence_prob_map,
                )
                cpir = _compute_cpir(
                    activities,
                    support_count,
                    confidence_count,
                    existence_prob_map,
                )

                constraints_data.append({
                    "template": template_name,
                    "activities": activities_repr,
                    "support": round(support_pct, 2),
                    "confidence": round(confidence_pct, 2),
                    "interest_factor": round(interest_factor, 6),
                    "cpir": round(cpir, 6),
                })
                pbar.update(1)

    constraints_df = pd.DataFrame(constraints_data)

    print(f"\nDiscovered {len(constraints_df)} constraints\n")

    return constraints_df


def save_constraints_for_log(log_path, output_path, min_support=0.7, min_confidence=0.7):
    """Mine Declare constraints for one log and save them to CSV."""
    constraints = mine_declare_constraints(
        str(log_path),
        min_support=min_support,
        min_confidence=min_confidence
    )
    print(constraints)
    constraints.to_csv(output_path, index=False)
    print(f"\nResults saved to {output_path}")


def process_all_logs(base_directory="data", output_directory="declare_constraints_all", min_support=0.7, min_confidence=0.7):
    """Apply Declare mining to all XES logs under a directory."""
    base_path = Path(base_directory)
    if not base_path.exists():
        raise FileNotFoundError(f"Directory not found: {base_directory}")

    xes_logs = sorted(base_path.rglob("*.xes"))
    if not xes_logs:
        raise FileNotFoundError(f"No .xes files found in: {base_directory}")

    out_dir = Path(output_directory)
    out_dir.mkdir(parents=True, exist_ok=True)

    for log_path in tqdm(
        xes_logs,
        desc="Mining constraints",
        unit="log",
        file=sys.stdout,
        dynamic_ncols=True,
        disable=False,
    ):
        tqdm.write(f"\n=== Processing {log_path} ===")
        output_name = str(log_path.relative_to(base_path)).replace("/", "__").replace(".xes", ".csv")
        output_path = out_dir / output_name
        save_constraints_for_log(log_path, output_path, min_support, min_confidence)

    print(f"\nCompleted! Processed {len(xes_logs)} logs.")
    print(f"All files saved in: {out_dir}")


def print_time(execution_time, outpath):
    """Store scenario execution time in execution_time.txt."""
    hours = int(execution_time // 3600)
    minutes = int((execution_time % 3600) // 60)
    seconds = execution_time % 60
    with open(outpath / "execution_time.txt", "w") as f:
        f.write(
            f"Execution Time: {hours} hours, {minutes} minutes, {seconds:.6f} seconds"
        )


def _load_framework_modules(project_root: Path):
    """Import framework modules used by run_framework.py from project root."""
    framework_dir = project_root / "ConstraintBasedEventLogGenerator"
    if str(framework_dir) not in sys.path:
        sys.path.insert(0, str(framework_dir))
    # Avoid collision with this script filename (constraints.py) when importing
    # the framework package `constraints.*`.
    constraints_pkg = types.ModuleType("constraints")
    constraints_pkg.__path__ = [str(framework_dir / "constraints")]
    sys.modules["constraints"] = constraints_pkg
    from src.train_utils import splitEventLog  # noqa: WPS433
    from EventLogGenerator import EventLogGenerator  # noqa: WPS433

    return splitEventLog, EventLogGenerator


def run_generation_framework(
    case_studies,
    n_sim=10,
    exp=" exp10",
    scenarios=("A", "B", "C", "D", "E"),
    project_root=None,
    output_root="results",
):
    """
    Run the same generation flow implemented in ConstraintBasedEventLogGenerator/run_framework.py.
    """
    project_root = Path(project_root) if project_root else Path(__file__).resolve().parent
    splitEventLog, EventLogGenerator = _load_framework_modules(project_root)

    scenario_set = set(scenarios)

    for case_study in case_studies:
        if case_study not in CASE_STUDY_CONFIG:
            raise ValueError(f"Unknown case study: {case_study}")

        print("*********************************")
        print("*********************************\n")
        print(f"\n*********************************\n{case_study}\n*********************************")

        cfg = CASE_STUDY_CONFIG[case_study]
        path_log = project_root / cfg["path_log"]
        save_split_to = project_root / cfg["save_split_to"]
        save_simulations_to = cfg["save_simulations_to"]
        label_data_attributes = cfg["label_data_attributes"]
        k = cfg["k"]

        start_time = time.time()
        log = xes_importer.apply(str(path_log))
        save_split_to.mkdir(parents=True, exist_ok=True)
        train_log, test_log = splitEventLog(
            log,
            train_size=0.8,
            split_temporal=True,
            save_to=str(save_split_to),
        )

        start_timestamp = test_log[0][0]["time:timestamp"]
        preprocessing_time = time.time() - start_time

        if "A" in scenario_set:
            start_time = time.time()
            outpath = project_root / output_root / f"{save_simulations_to}{exp}" / "scenarioA"
            outpath.mkdir(parents=True, exist_ok=True)
            print("\n*********************************\nSCENARIO A\n*********************************")
            generator = EventLogGenerator(
                train_log,
                k=k,
                label_data_attributes=label_data_attributes,
                case_study=case_study,
                scenario="scenarioA",
            )
            for i in range(n_sim):
                simulated_traces = generator.apply(
                    N=len(test_log), start_timestamp=start_timestamp
                )
                simulated_traces.to_csv(outpath / f"sim_{i}.csv", index=False)
                print(f"{case_study} simulation {i} with SCENARIO A done!")
            execution_time = time.time() - start_time + preprocessing_time
            print_time(execution_time, outpath)

        if "B" in scenario_set:
            start_time = time.time()
            outpath = project_root / output_root / f"{save_simulations_to}{exp}" / "scenarioB"
            outpath.mkdir(parents=True, exist_ok=True)
            print("\n*********************************\nSCENARIO B\n*********************************")
            generator = EventLogGenerator(
                train_log,
                k=50, #50 set as infinity
                label_data_attributes=label_data_attributes,
                case_study=case_study,
                scenario="scenarioB",
            )
            for i in range(n_sim):
                simulated_traces = generator.sample_traces(N=len(test_log))
                simulated_traces.to_csv(outpath / f"sim_{i}.csv", index=False)
                print(f"{case_study} simulation {i} with SCENARIO B done!")
            execution_time = time.time() - start_time + preprocessing_time
            print_time(execution_time, outpath)

        if "C" in scenario_set:
            start_time = time.time()
            outpath = project_root / output_root / f"{save_simulations_to}{exp}" / "scenarioC"
            outpath.mkdir(parents=True, exist_ok=True)
            print("\n*********************************\nSCENARIO C\n*********************************")
            generator = EventLogGenerator(
                train_log,
                k=k,
                label_data_attributes=label_data_attributes,
                case_study=case_study,
                scenario="scenarioC",
            )
            for i in range(n_sim):
                simulated_traces = generator.apply(
                    N=len(test_log), start_timestamp=start_timestamp
                )
                simulated_traces.to_csv(outpath / f"sim_{i}.csv", index=False)
                print(f"{case_study} simulation {i} with SCENARIO C done!")
            execution_time = time.time() - start_time + preprocessing_time
            print_time(execution_time, outpath)

        if "D" in scenario_set:
            start_time = time.time()
            outpath = project_root / output_root / f"{save_simulations_to}{exp}" / "scenarioD"
            outpath.mkdir(parents=True, exist_ok=True)
            print("\n*********************************\nSCENARIO D\n*********************************")
            generator = EventLogGenerator(
                train_log,
                k=k,
                label_data_attributes=label_data_attributes,
                case_study=case_study,
                scenario="scenarioD",
            )
            for i in range(n_sim):
                simulated_traces = generator.apply(
                    N=len(test_log), start_timestamp=start_timestamp
                )
                simulated_traces.to_csv(outpath / f"sim_{i}.csv", index=False)
                print(f"{case_study} simulation {i} with SCENARIO D done!")
            execution_time = time.time() - start_time + preprocessing_time
            print_time(execution_time, outpath)

        if "E" in scenario_set:
            start_time = time.time()
            outpath = project_root / output_root / f"{save_simulations_to}{exp}" / "scenarioE"
            outpath.mkdir(parents=True, exist_ok=True)
            print("\n*********************************\nSCENARIO E\n*********************************")
            generator = EventLogGenerator(
                train_log,
                k=50, #50 set as to infinity
                label_data_attributes=label_data_attributes,
                case_study=case_study,
                scenario="scenarioE",
            )
            for i in range(n_sim):
                simulated_traces = generator.sample_traces(N=len(test_log))
                simulated_traces.to_csv(outpath / f"sim_{i}.csv", index=False)
                print(f"{case_study} simulation {i} with SCENARIO E done!")
            execution_time = time.time() - start_time + preprocessing_time
            print_time(execution_time, outpath)


def _run_mine_mode(cli_args):
    """CLI entry point for declare mining mode."""
    parser = argparse.ArgumentParser(
        description="Mine PM4Py Declare constraints from one log or from all logs in a directory."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="data",
        help="Path to a .xes file or directory. Default: data",
    )
    parser.add_argument(
        "--min-support",
        type=float,
        default=0.7,
        help="Minimum support ratio in [0, 1]. Default: 0.7",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.7,
        help="Minimum confidence ratio in [0, 1]. Default: 0.7",
    )
    parser.add_argument(
        "--output-dir",
        default="declare_constraints_all",
        help="Output directory for batch mode. Default: declare_constraints_all",
    )
    args = parser.parse_args(cli_args)

    if not (0.0 <= args.min_support <= 1.0):
        parser.error("--min-support must be between 0 and 1.")
    if not (0.0 <= args.min_confidence <= 1.0):
        parser.error("--min-confidence must be between 0 and 1.")

    target = Path(args.target)
    if target.is_dir():
        process_all_logs(
            base_directory=str(target),
            output_directory=args.output_dir,
            min_support=args.min_support,
            min_confidence=args.min_confidence,
        )
    else:
        if not target.exists():
            parser.error(f"file or directory not found: {target}")
        save_constraints_for_log(
            target,
            "declare_constraints.csv",
            min_support=args.min_support,
            min_confidence=args.min_confidence,
        )


def _run_generate_mode(cli_args):
    """CLI entry point for generation mode (run_framework equivalent)."""
    parser = argparse.ArgumentParser(
        description="Run full event-log generation workflow (equivalent to run_framework.py)."
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        default=['ds02'],
        choices=sorted(CASE_STUDY_CONFIG.keys()),
        help="Case studies to run (e.g. ds01).",
    )
    parser.add_argument(
        "--n-sim",
        type=int,
        default=2,
        help="Number of simulations per scenario. Default: 10",
    )
    parser.add_argument(
        "--exp",
        default=" exp10",
        help="Experiment suffix appended to output folder path. Default: ' exp10'",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=["A", "B", "C"],
        choices=["A", "B", "C"],
        help="Scenarios to run. Default: A B C",
    )
    parser.add_argument(
        "--output-root",
        default="results",
        help="Root output folder for generated simulations. Default: results",
    )
    args = parser.parse_args(cli_args)

    if args.n_sim < 0:
        parser.error("--n-sim must be >= 0.")

    run_generation_framework(
        case_studies=args.cases,
        n_sim=args.n_sim,
        exp=args.exp,
        scenarios=args.scenarios,
        output_root=args.output_root,
    )


if __name__ == "__main__":
    # Keep backward compatibility:
    # - `python constraints.py ...` => mining mode
    # - `python constraints.py generate ...` => run_framework-equivalent generation mode
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        _run_generate_mode(sys.argv[2:])
    else:
        _run_mine_mode(sys.argv[1:])
