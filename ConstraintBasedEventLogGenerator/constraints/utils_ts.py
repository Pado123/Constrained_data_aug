
from constraints.automata_tools import get_state_sequence_per_trace
from automata.fa.nfa import NFA 
from collections import defaultdict, Counter
from constraints.constants import START_PLACEHOLDER, END_PLACEHOLDER

# =============================================================================
# Transition system dict utils
# =============================================================================

def build_transition_system_from_log(event_seqs, k=3):
    """
    Builds a transition system from a collection of traces using a sliding window of length k.  
    Each state corresponds to the last k events, and transitions record the relative frequencies
    of possible next events.

    Parameters:
        event_seqs (List[List[str]]): List of traces, where each trace is a sequence of events.
        k (int, optional): Length of the history window used to define states (default is 3).

    Returns:
        Dict[Tuple[str], Dict[str, float]]: Transition system where each state (tuple of past events)
            maps to a dictionary of next events with their corresponding probabilities.
    """
    
    transition_counts = defaultdict(Counter)

    for trace in event_seqs:
        if trace:
            transition_counts[(START_PLACEHOLDER,)][trace[0]] += 1

        full_trace = trace + [END_PLACEHOLDER]
        for i in range(len(full_trace)):
            history = trace[max(0, i - k):i]
            if history:
                state = tuple(history)
                next_act = full_trace[i]
                transition_counts[state][next_act] += 1

    transition_system = {}
    for state, next_counts in transition_counts.items():
        total = sum(next_counts.values())
        transition_system[state] = {
            act: round(count / total, 5) for act, count in next_counts.items()
        }

    return transition_system


def build_ts_from_automaton(nfa: NFA) -> dict:
    """
    Extracts a transition structure from an NFA with initial frequency counts set to 0.

    Args:
        nfa (NFA): The input automaton.

    Returns:
        Dict[Tuple, Dict[Tuple, int]]: A nested dictionary representing transitions
            between states, initialized with frequency 0.
    """
    tr = {}
    for current_state, transitions in nfa.transitions.items():
        if current_state not in tr:
            tr[current_state] = {}
            
        for transition_symbol, next_states in transitions.items(): #next_states is a frozen set of size 1
            for next_state in next_states:
                tr[current_state][next_state] = [transition_symbol, 0]

    return tr


def populate_ts_based_on_all_traces(ts_dict: dict, nfa: NFA, event_seqs:list) -> dict:
    """
    Updates a transition system dictionary by counting frequences based on all traces

    Parameters:
        ts_dict (Dict[Tuple, Dict[Tuple, int]]): Transition system
        log_name (str): Name of the log file (used to load traces).
        nfa (NFA): Automaton to evaluate traces.

    Returns:
        Dict[Tuple, Dict[Tuple, int]]: Updated transition system dictionary with frequencies.
    """
       
    # Crea una mappa da tupla activities → lista di stati che la contengono. (per ottimizzare la ricerca dopo)
    map = defaultdict(list)
    for state in ts_dict:
        acts = state[0] #prendi la tupla delle activities
        map[acts].append(state) #aggiungi lo stato completo come elemento della lista di acts

    for trace in event_seqs:
        trace.append(END_PLACEHOLDER)
    
        trace_states_sequence = get_state_sequence_per_trace(nfa, trace)

        for i in range(len(trace)):
            current_state_trace = trace_states_sequence[i]
            next_state_trace = trace_states_sequence[i + 1]

            for state in map.get(current_state_trace, []):
                for next_state in ts_dict[state]:
                    if next_state[0] == next_state_trace:
                        ts_dict[state][next_state][1] += 1
                        
    return ts_dict
    

def convert_freq_to_prob(dict_freq: dict) -> dict:
    """
    Converts transition frequencies into probabilities.

    Parameters:
        dict_freq (Dict): Struttura {current_state: {next_state: [symbol, freq]}}

    Returns:
        Dict: Struttura {current_state: {next_state: [symbol, prob]}}
    """
    dict_proba = {}

    for state, next_states in dict_freq.items():
        total = sum(freq for _, freq in next_states.values())
        if total == 0:
            continue

        dict_proba[state] = {
            next_state: [symbol, round(freq / total, 5)]
            for next_state, (symbol, freq) in next_states.items()
        }

    return dict_proba

def extract_event_seqs_and_alphabet(log) -> tuple:
    """
    Extracts traces and the activity alphabet from a log DataFrame.

    Parameters:
        log (EventLog): Event log in tabular format.

    Returns:
        Tuple[List[List[str]], List[str]]: Traces and corresponding alphabet.
    """
    event_seqs = []
    alphabet = []
    
    for trace in log:
        trace_acts = []
        
        for event in trace:
            act = event['concept:name']
            trace_acts.append(act)
            
            if act not in alphabet and act != START_PLACEHOLDER:
                alphabet.append(act)
                
        event_seqs.append(trace_acts)
            
    alphabet = sorted(alphabet)
    alphabet.append(END_PLACEHOLDER)
    return event_seqs, alphabet


def generate_ts_from_automaton(nfa_final: NFA, nfa: NFA, event_seqs: list) -> None:
    """
    Computes and saves the transition system from the accepted part of an automaton.

    Parameters:
        nfa_final (NFA): Final automaton.
        nfa (NFA): Automaton used to track state sequences.
        path (str): Path to output folder.
        log_name (str): Name of the log.
    """
    ts_dict_accepted = build_ts_from_automaton(nfa_final)
    ts_dict_freq = populate_ts_based_on_all_traces(ts_dict_accepted, nfa, event_seqs) 

    ts_dict_proba = convert_freq_to_prob(ts_dict_freq)
    return ts_dict_proba 
    
