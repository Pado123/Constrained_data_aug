from automata.fa.nfa import NFA 
from collections import defaultdict, deque
from constraints.constants import START_PLACEHOLDER, END_PLACEHOLDER

# =============================================================================
# Functions to manage NFAs
# =============================================================================

def build_automaton_from_ts(ts_dict: dict, alphabet: list, k: int) -> NFA:
    """
    Builds a non-deterministic finite automaton (NFA) from a transition dictionary.

    Args:
        ts_dict (Dict[Tuple, Dict[str, float]]): A dictionary where each state maps to
            activities and their corresponding probabilities or frequencies.
        alphabet (List[str]): List of allowed symbols (activities).
        k (int): memory window.

    Returns:
        NFA: A non-deterministic finite automaton object.
    """
    transitions = {}
    states = set()
    final_states = set()

    initial_state = (START_PLACEHOLDER,)
    states.add(initial_state)
    transitions[initial_state] = {}

    for prefix, next_moves in ts_dict.items(): 
        transitions.setdefault(prefix, {})
        states.add(prefix)

        for act, prob in next_moves.items():  

            if act == END_PLACEHOLDER:
                end_state = prefix + (act,)
                transitions[prefix].setdefault(act, set()).add(end_state)
                states.add(end_state)
                final_states.add(end_state)
            else:
                if prefix == (START_PLACEHOLDER,):
                    next_state = (act,)
                else:
                    if len(prefix) < k:
                        next_state = prefix + (act,)
                    else:
                        next_state = prefix[1:] + (act,)
                states.add(next_state)
                transitions[prefix].setdefault(act, set()).add(next_state)
                
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=initial_state,
        final_states=final_states
    )


def prune_dead_end_states(nfa: NFA, debug: bool = False) -> NFA:
    """
    Removes states and transitions from the NFA that do not lead to any final state.

    Args:
        nfa (NFA): The input automaton to prune.
        debug (bool): If True, prints debugging information.

    Returns:
        NFA: A pruned NFA that only contains paths leading to final states.
    """

    incoming_transitions = defaultdict(set)  # Backward transitions (target -> src)
    updated_transitions = {}

    # Build updated transitions and compute incoming mapping
    for src, trans in nfa.transitions.items():
        updated_transitions[src] = {}
        for symbol, targets in trans.items():
            targets_set = set(targets)  # Ensure it's a mutable set
            updated_transitions[src][symbol] = targets_set
            for tgt in targets_set:
                incoming_transitions[tgt].add(src)

    # Backward traversal from final states
    # Start from all final states, and find all states that can reach them (directly or indirectly)
    reachable_from_final = set(nfa.final_states)
    queue = deque(nfa.final_states)

    while queue:
        current = queue.popleft()
        # Look at all states that transition to 'current'
        for predecessor in incoming_transitions.get(current, []):
            if predecessor not in reachable_from_final:
                # Mark the predecessor as reachable and continue the search
                reachable_from_final.add(predecessor)
                queue.append(predecessor)

    if nfa.initial_state not in reachable_from_final:
        raise ValueError("Initial state cannot reach any final state — no accepting paths remain.\nChange Constraints!")
    
    if debug:
        # Any state not in reachable_from_final cannot reach a final state → dead-end
        dead_states = set(nfa.states) - reachable_from_final
        print("States that do NOT lead to any final state (dead-ends):")
        print('\n'.join(map(str, sorted(dead_states))) if dead_states else 'None')

    # Prune dead-end states and their transitions 
    pruned_transitions = {}
    for state in updated_transitions:
        # Skip states that cannot reach any final state
        if state not in reachable_from_final:
            continue

        pruned_transitions[state] = {}
        for symbol, targets in updated_transitions[state].items():
            # Keep only the transitions to states that are still considered valid
            filtered_targets = targets & reachable_from_final
            if filtered_targets:
                pruned_transitions[state][symbol] = filtered_targets
    
    # Extract the new alphabet            
    used_symbols = {sym for trans in pruned_transitions.values() for sym in trans}

    # Construct and return the cleaned NFA
    return NFA(
        states=reachable_from_final,  # Keep only reachable states
        input_symbols=used_symbols, 
        transitions=pruned_transitions,
        initial_state=nfa.initial_state ,
        final_states=nfa.final_states & reachable_from_final  
    )


def get_state_sequence_per_trace(nfa: NFA, trace: list) -> list:
    """
    Returns the sequence of states visited by the NFA for a given trace.

    Args:
        nfa (NFA): The automaton to simulate.
        trace (List[str]): A list of input symbols (activities).

    Returns:
        List[Tuple]: The sequence of visited states.
    """
    state_sequence = []
    try:
        for step_states in nfa.read_input_stepwise(trace):
            [state] = step_states #assume the NFA is deterministic at runtime (only one state active per step)
            state_sequence.append(state)
    except Exception:
        # print(state_sequence)
        return state_sequence

    return state_sequence
