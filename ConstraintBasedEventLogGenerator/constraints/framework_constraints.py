from constraints.constraints_per_log import (
    create_nfa_constraints,
    get_top_k_mined_constraints,
    trace_satisfies_constraint,
)
from constraints.automata_tools import (build_automaton_from_ts, prune_dead_end_states,)
from constraints.utils_ts import (generate_ts_from_automaton, build_transition_system_from_log)
from pm4py.objects.log.obj import EventLog
from constraints.constants import END_PLACEHOLDER
import os
import time
from typing import Optional

# =============================================================================
# Functions to compute constrained transition systems and filter event logs
# =============================================================================


def _print_filter_stats(original_log: EventLog, filtered_log: EventLog) -> None:
    """Print trace filtering statistics."""
    orig_len = len(original_log)
    filt_len = len(filtered_log)
    removed = orig_len - filt_len
    pct = removed / orig_len * 100 if orig_len else 0
    print("\n--- Trace stats ---")
    print(f"Traces in original log : {orig_len}")
    print(f"Traces after filtering : {filt_len}")
    print(f"Removed traces         : {removed}")
    print(f"Percentage removed     : {pct:.2f}%")


def _nfa_size_stats(nfa) -> tuple[int, int]:
    if nfa is None:
        return 0, 0
    n_states = len(getattr(nfa, "states", []))
    transitions = getattr(nfa, "transitions", {}) or {}
    n_transitions = 0
    for symbol_targets in transitions.values():
        for targets in symbol_targets.values():
            n_transitions += len(targets)
    return int(n_states), int(n_transitions)


def get_prefix_proba_constrained(case_study: str, alphabet: list, event_seqs: list, k = 0, log: EventLog = None):
    
    """
    Computes the constrained transition system and the corresponding prefix probability dictionary.

    This function builds a transition system from event sequences, converts it to an NFA,
    intersects it with a constraint automaton, prunes unreachable final states, and finally
    computes a new constrained transition system.

    Args:
        case_study (str): Identifier for the specific case study or constraint set to apply.
        alphabet (List[str]): The list of activities that will be used in the NFAs.
        event_seqs (list[list[str]]): The list of event sequences.
        k (int): Prefix length for transition system generation. 

    Returns:
        tuple:
            - set: The pruned alphabet from the final automaton.
            - dict: Dictionary representing the constrained transition system with probabilities.

    Raises:
        ValueError: If the intersection of the transition system and the constraints results in
                    no valid final states, indicating overly restrictive constraints.
    """
    
    print('Working to apply the constraints...')
    print(f'   Building transition system of the log with k={k}...')
    t0 = time.perf_counter()
    tr_dict = build_transition_system_from_log(event_seqs, k)
    print(f"   [PROFILE] build_transition_system_from_log: {time.perf_counter() - t0:.2f}s")

    print('   Converting the transition system to an automaton...')
    t0 = time.perf_counter()
    nfa_ts = build_automaton_from_ts(tr_dict, alphabet,k)
    ts_states, ts_trans = _nfa_size_stats(nfa_ts)
    print(
        f"   [PROFILE] build_automaton_from_ts: {time.perf_counter() - t0:.2f}s "
        f"(states={ts_states}, transitions={ts_trans})"
    )
    
    print('   Creating contraints...')
    t0 = time.perf_counter()
    nfa_constraints = create_nfa_constraints(case_study, alphabet, log=log)
    c_states, c_trans = _nfa_size_stats(nfa_constraints)
    print(
        f"   [PROFILE] create_nfa_constraints: {time.perf_counter() - t0:.2f}s "
        f"(states={c_states}, transitions={c_trans})"
    )

    print('   Performing intersection between the transition system automaton and the constraints...')
    max_product_states = int(os.getenv("DECLARE_MAX_PRODUCT_STATES", "5000000"))
    projected_product_states = ts_states * c_states
    if max_product_states > 0 and projected_product_states > max_product_states:
        raise ValueError(
            "Projected TS x constraints product is too large "
            f"({projected_product_states} > {max_product_states}); skipping to avoid OOM."
        )
    t0 = time.perf_counter()
    nfa_intersection = nfa_ts.intersection(nfa_constraints)
    i_states, i_trans = _nfa_size_stats(nfa_intersection)
    print(
        f"   [PROFILE] TS∩constraints intersection: {time.perf_counter() - t0:.2f}s "
        f"(states={i_states}, transitions={i_trans}, projected={projected_product_states})"
    )
    
    if not nfa_intersection.final_states:
        raise ValueError(
        "Cannot perform the intersection: the constraints are too restrictive, "
        "resulting in an automaton with no acceptable paths from start to end. Try changing the constraints!"
    )
        
    print('   Removing paths to non-final states...')
    t0 = time.perf_counter()
    nfa_pruned = prune_dead_end_states(nfa_intersection, debug=False)
    p_states, p_trans = _nfa_size_stats(nfa_pruned)
    print(
        f"   [PROFILE] prune_dead_end_states: {time.perf_counter() - t0:.2f}s "
        f"(states={p_states}, transitions={p_trans})"
    )
    alphabet_pruned = nfa_pruned.input_symbols

    print('   Computing the new constrained transition system...')
    t0 = time.perf_counter()
    dict_prefix_proba = generate_ts_from_automaton(nfa_pruned, nfa_ts, event_seqs)
    print(f"   [PROFILE] generate_ts_from_automaton: {time.perf_counter() - t0:.2f}s")

    return alphabet_pruned, dict_prefix_proba



def get_filtered_log(
    log: EventLog,
    case_study: str,
    alphabet: list,
    experiment: str = None,
    mining_log: EventLog = None,
    event_seqs: Optional[list] = None,
    k: Optional[int] = None,
):
    """
    Filters an event log by removing traces that do not satisfy the constraints.

    When event_seqs and k are provided, uses the same NFA as scenario A/B: the pruned
    intersection of the transition system (from the log) with the constraints. This
    ensures traces that do not satisfy TS ∩ constraints are removed.

    When event_seqs or k are not provided, uses only the constraint NFA (less restrictive).

    Args:
        log (EventLog): The original event log to filter.
        case_study (str): Identifier for the specific case study or constraint set to apply.
        alphabet (list): The list of activities that will be used in the NFAs.
        experiment (str, optional): Experiment identifier (exp1, exp2, exp3, exp4).
        mining_log (EventLog, optional): Log for constraint discovery if different from log.
        event_seqs (list, optional): Event sequences for TS construction. Required for TS∩constraints filtering.
        k (int, optional): Prefix length for TS. Required for TS∩constraints filtering.

    Returns:
        EventLog: A new event log containing only the traces accepted by the automaton.
    """
    mining = mining_log if mining_log is not None else log
    align_pct = os.getenv("DECLARE_ALIGN_PERCENTAGE_DECLARE", "0").strip() == "1"
    top_k = int(os.getenv("DECLARE_SAMPLE_SIZE", "50"))

    if event_seqs is not None and k is not None and align_pct:
        # Per-trace filtering matching percentage_declare_traces + TS intersection
        from constraints.constants import START_PLACEHOLDER
        alphabet_full = sorted(
            set(alphabet) | {START_PLACEHOLDER, END_PLACEHOLDER}
        )
        tr_dict = build_transition_system_from_log(event_seqs, k)
        nfa_ts = build_automaton_from_ts(tr_dict, alphabet_full, k)
        constraints_list = get_top_k_mined_constraints(mining, alphabet_full, top_k, log_name=case_study)
        nfa_cache = {}
        traces_list = list(log)
        trace_flags = [True] * len(traces_list)
        for (template, acts) in constraints_list:
            for trace_idx, trace in enumerate(traces_list):
                if not trace_flags[trace_idx]:
                    continue
                if not trace_satisfies_constraint(trace, template, acts, alphabet_full, nfa_cache):
                    trace_flags[trace_idx] = False
        # TS check: trace must be in TS
        for trace_idx, trace in enumerate(traces_list):
            if not trace_flags[trace_idx]:
                continue
            event_seq = [e["concept:name"] for e in trace]
            event_seq.append(END_PLACEHOLDER)
            if not nfa_ts.accepts_input(event_seq):
                trace_flags[trace_idx] = False
        new_log = EventLog()
        for trace, keep in zip(traces_list, trace_flags):
            if keep:
                new_log.append(trace)
        print(
            f"Filtering using TS ∩ top-{top_k} constraints "
            "(percentage_declare_traces-aligned, per-trace check)."
        )
        _print_filter_stats(log, new_log)
        return new_log

    if event_seqs is not None and k is not None:
        # Use the same pruned (TS ∩ constraints) NFA as scenario A/B
        tr_dict = build_transition_system_from_log(event_seqs, k)
        nfa_ts = build_automaton_from_ts(tr_dict, alphabet, k)
        nfa_constraints = create_nfa_constraints(case_study, alphabet, experiment, log=mining)
        max_product_states = int(os.getenv("DECLARE_MAX_PRODUCT_STATES", "5000000"))
        ts_states, _ = _nfa_size_stats(nfa_ts)
        c_states, _ = _nfa_size_stats(nfa_constraints)
        if max_product_states > 0 and ts_states * c_states > max_product_states:
            raise ValueError(
                "Projected TS x constraints product is too large for filtering; "
                "use constraints-only or increase DECLARE_MAX_PRODUCT_STATES."
            )
        nfa_intersection = nfa_ts.intersection(nfa_constraints)
        if not nfa_intersection.final_states:
            raise ValueError(
                "TS ∩ constraints has no acceptable paths; cannot filter log."
            )
        filter_nfa = prune_dead_end_states(nfa_intersection, debug=False)
        print("Filtering using pruned (TS ∩ constraints) NFA (same as scenario A/B).")
    else:
        filter_nfa = create_nfa_constraints(
            case_study,
            alphabet,
            experiment,
            log=mining,
        )
    new_log = EventLog()

    exp_info = f" for {experiment}" if experiment else ""
    print(f"Filtering the log to keep only the traces that are accepted by the constraints{exp_info}...")
    accept = filter_nfa.accepts_input
    progress_every = int(os.getenv("DECLARE_FILTER_PROGRESS_EVERY", "2000"))
    start = time.perf_counter()
    
    # import ipdb; ipdb.set_trace()

    for idx, trace in enumerate(log, start=1):
        event_seq = [event['concept:name'] for event in trace]
        event_seq.append(END_PLACEHOLDER)    
        
        if accept(event_seq):
            new_log.append(trace)
        if progress_every > 0 and idx % progress_every == 0:
            elapsed = time.perf_counter() - start
            print(f"   [PROFILE] filtered {idx} traces in {elapsed:.2f}s")
    
    # import ipdb; ipdb.set_trace()

    _print_filter_stats(log, new_log)
    return new_log

