from constraints.constraints_per_log import create_nfa_constraints
from constraints.automata_tools import (build_automaton_from_ts, prune_dead_end_states,)
from constraints.utils_ts import (generate_ts_from_automaton, build_transition_system_from_log)
from pm4py.objects.log.obj import EventLog
from constraints.constants import END_PLACEHOLDER

# =============================================================================
# Functions to compute constrained transition systems and filter event logs
# =============================================================================


def get_prefix_proba_constrained(case_study: str, alphabet: list, event_seqs: list, k = 0):
    
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
    tr_dict = build_transition_system_from_log(event_seqs, k) 

    print('   Converting the transition system to an automaton...')
    nfa_ts = build_automaton_from_ts(tr_dict, alphabet,k)
    
    print('   Creating contraints...')
    nfa_constraints = create_nfa_constraints(case_study, alphabet)

    print('   Performing intersection between the transition system automaton and the constraints...')
    nfa_intersection = nfa_ts.intersection(nfa_constraints)
    
    if not nfa_intersection.final_states:
        raise ValueError(
        "Cannot perform the intersection: the constraints are too restrictive, "
        "resulting in an automaton with no acceptable paths from start to end. Try changing the constraints!"
    )
        
    print('   Removing paths to non-final states...')
    nfa_pruned = prune_dead_end_states(nfa_intersection, debug=False)
    alphabet_pruned = nfa_pruned.input_symbols

    print('   Computing the new constrained transition system...')
    dict_prefix_proba = generate_ts_from_automaton(nfa_pruned, nfa_ts, event_seqs)    

    return alphabet_pruned, dict_prefix_proba



def get_filtered_log(log: EventLog, case_study: str, alphabet: list):
    """
    Filters an event log by removing traces that do not satisfy a set of constraints.

    For each trace in the log, the corresponding event sequence is checked against
    a constraint NFA. If the sequence is accepted, it is included in the new log.

    Args:
        log (EventLog): The original event log to filter.
        case_study (str): Identifier for the specific case study or constraint set to apply.
        alphabet (list): The list of activities that will be used in the NFAs.

    Returns:
        EventLog: A new event log containing only the traces accepted by the constraint automaton.
    """
    
    constraints_nfa = create_nfa_constraints(case_study, alphabet)
    new_log = EventLog()
    
    print('Filtering the log to keep only the traces that are accepted by the constraints...')
    for trace in log:
        event_seq = [event['concept:name'] for event in trace]
        event_seq.append(END_PLACEHOLDER)
        
        if constraints_nfa.accepts_input(event_seq):
            new_log.append(trace)
    
    original_len = len(log)
    filtered_len = len(new_log)
    removed_traces = original_len - filtered_len
    removed_pct = removed_traces / original_len * 100

    print('\n--- Trace stats ---')
    print(f'Traces in original log : {original_len}')
    print(f'Traces after filtering : {filtered_len}')
    print(f'Removed traces         : {original_len-filtered_len}')
    print(f'Percentage removed     : {removed_pct:.2f}%')
    

    return new_log

