from automata.fa.nfa import NFA
from constraints.constants import END_PLACEHOLDER

def handle_end_placeholder(transitions: set, final_states: set) -> set:
    """
    Add the transition of the END placeholder only in the final states (the transition stays in the same state)

    Args:
        transitions (set): the set of sets representing all transitions
        final_states (set): the set of the final states where the placeholder needs to be added

    Returns:
        set: the updated transitions set to handle the placeholder
    """
    
    for state in final_states:
        transitions[state][END_PLACEHOLDER] = {state}
    
    return transitions

#############################
### EXISTENCE CONSTRAINTS ###
#############################

def existence_constraint(event1: str, alphabet: list) -> NFA:
    """
    Existence: Eventually, event1 will happen.
    
    Args:
        event1 (str): the event that must eventually happen
        alphabet (list): the list of all possible events (input symbols)
    
    Returns:
        NFA: The NFA representing the existence constraint
    """
    q0 = 'q0'
    q1 = 'q1'

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states = {q1}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
        else:
            transitions[q0][symbol] = {q0}
        transitions[q1][symbol] = {q1}

    transitions = handle_end_placeholder(transitions, final_states)

    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states= final_states
    )

def absence_constraint(event: str, alphabet: list) -> NFA:
    """
    Absence constraint: Globally, event must never occur.
    
    Parameters:
        event: The event that must not occur (string).
        alphabet: The list of all possible events (input symbols)
        
    Returns:
        NFA: The NFA representing the absence constraint.    
    """
    q0 = 'q0'
    
    states = {q0}
    transitions = {q0: {}}
    final_states={q0}

    for symbol in alphabet[:-1]:
        if symbol != event:
            transitions[q0][symbol] = {q0}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )


def existence_exactly_once_constraint(event: str, alphabet: list) -> NFA:
    """
    Exactly-once constraint: the event must occur exactly once in the entire trace.
    
    Parameters:
        event: The event that must occur exactly once (string).
        alphabet: The list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the existence exactly once constraint.
    """
    q0 = 'q0' 
    q1 = 'q1' 

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q1} 

    for symbol in alphabet[:-1]:
        if symbol == event:
            transitions[q0][symbol] = {q1}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q1}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )
    

def init_constraint(event: str, alphabet: list) -> NFA:
    """
    Init constraint: event has to happen at the beginning.
    
    Parameters:
        event: The event required at the beginning (string).
        alphabet: The list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the init constraint.
    """
    q0 = 'q0' 
    q1 = 'q1' 

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q1} 

    for symbol in alphabet[:-1]:
        if symbol == event:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
        else:
            transitions[q1][symbol] = {q1}
    
    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )
    
def last_constraint(event: str, alphabet: list) -> NFA:
    """
    End constraint: the event can only happen last, and nothing else can happen after.
    
    Parameters:
        event: The event that can only happen at the end (string).
        alphabet: The list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the init constraint.
    """
    q0 = 'q0' 
    q1 = 'q1' 

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q1} 

    for symbol in alphabet[:-1]:
        if symbol == event:
            transitions[q0][symbol] = {q1}
        else:
            transitions[q0][symbol] = {q0}
    
    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )

############################
#### CHOICE CONSTRAINTS ####
############################


def choice_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Choice constraint: At least one of event1 or event2 must eventually occur.
    
    Parameters:
        event1: First optional event (string).
        event2: Second optional event (string).
        alphabet: The list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the choice constraint.
    """
    q0 = 'q0'  
    q1 = 'q1'  
    q2 = 'q2'  
    q3 = 'q3'  

    states = {q0, q1, q2, q3}
    transitions = {q0: {}, q1: {}, q2: {}, q3: {}}
    final_states={q1, q2, q3} 

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
            transitions[q2][symbol] = {q3}
        elif symbol == event2:
            transitions[q0][symbol] = {q2}
            transitions[q1][symbol] = {q3}
            transitions[q2][symbol] = {q2}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q1}
            transitions[q2][symbol] = {q2}

        transitions[q3][symbol] = {q3}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )

def exclusive_choice_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Exclusive Choice constraint: Exactly one of event1 or event2 must eventually occur — but not both
    
    Parameters:
        event1: First exclusive event (string).
        event2: Second exclusive event (string).
        alphabet: The list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the exclusive choice constraint.
    """
    q0 = 'q0'
    q1 = 'q1'  
    q2 = 'q2'  
    
    states = {q0, q1, q2}
    transitions = {q0: {}, q1: {}, q2: {}}
    final_states={q1, q2}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
        elif symbol == event2:
            transitions[q0][symbol] = {q2}
            transitions[q2][symbol] = {q2}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q1}
            transitions[q2][symbol] = {q2}

    transitions = handle_end_placeholder(transitions, final_states)

    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )

##############################
#### RELATION CONSTRAINTS ####
##############################


def responded_existence_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Responded existence: Globally, if event1 occurs, then event2 must have already occurred or will occur somewhere.
    
    Args:
        event1 (str): the triggering event
        event2 (str): the responding event that must occur before or after event1
        alphabet (list): the list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the responded existence constraint
    """
    q0 = 'q0' 
    q1 = 'q1'
    q2 = 'q2'  

    states = {q0, q1, q2}
    transitions = {q0: {}, q1: {}, q2: {}}
    final_states={q0, q2}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
        elif symbol == event2:
            transitions[q0][symbol] = {q2}
            transitions[q1][symbol] = {q2}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q1}

        transitions[q2][symbol] = {q2}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )
    
def co_existence_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Co-existence constraint: Both event1 and event2 must eventually occur at some point in the trace.
    
    Parameters:
        event1: First required event (string).
        event2: Second required event (string).
        alphabet: The list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the co-existence constraint.
    """
    q0 = 'q0' 
    q1 = 'q1' 
    q2 = 'q2' 
    q3 = 'q3'

    states = {q0, q1, q2, q3}
    transitions = {q0: {}, q1: {}, q2: {}, q3: {}}
    final_states={q3}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q2][symbol] = {q3}
            transitions[q1][symbol] = {q1}
            transitions[q3][symbol] = {q3}
        elif symbol == event2:
            transitions[q0][symbol] = {q2}
            transitions[q1][symbol] = {q3}
            transitions[q2][symbol] = {q2}
            transitions[q3][symbol] = {q3}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q1}
            transitions[q2][symbol] = {q2}
            transitions[q3][symbol] = {q3}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )

def response_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Response: Globally, whenever event1 occurs, event2 must eventually occur after.
    
    Args:
        event1 (str): the triggering event
        event2 (str): the event that must eventually occur after event1
        alphabet (list): the list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the response constraint
    """
    q0 = 'q0'
    q1 = 'q1'
    q2 = 'q2'

    states = {q0, q1, q2}
    transitions = {q0: {}, q1: {}, q2: {}}
    final_states={q0, q2}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
            transitions[q2][symbol] = {q1}
        elif symbol == event2:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q2}
            transitions[q2][symbol] = {q2}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q1}
            transitions[q2][symbol] = {q2}
    
    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )

def alternate_response_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Alternate response: Globally, whenever event1 occurs, then starting from the next event, 
                        there must be a sequence of events without any event1, until event2 occurs.

    Args:
        event1 (str): the triggering event that activates the alternate response
        event2 (str): the event that must occur eventually after event1, without intermediate event1
        alphabet (list): the list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the alternate response constraint
    """
    q0 = 'q0'
    q1 = 'q1'

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q0}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
        else:
            transitions[q0][symbol] = {q0}

        if symbol == event2:
            transitions[q1][symbol] = {q0}
        elif symbol != event1:
            transitions[q1][symbol] = {q1}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )


def chain_response_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Chain response: Globally, if event1 occurs, event2 must occur immediately in the next step.
    
    Args:
        event1 (str): the triggering event
        event2 (str): the event that must immediately follow event1
        alphabet (list): the list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the chain response constraint
    """
    q0 = 'q0'
    q1 = 'q1'

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q0}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
        elif symbol == event2:
            transitions[q1][symbol] = {q0}
            transitions[q0][symbol] = {q0}
        else:
            transitions[q0][symbol] = {q0}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )


def precedence_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Precedence: Globally, if event2 occurs, then event1 must have already happened sometime in the past.
    
    Args:
        event1 (str): the event that must have occurred before event2
        event2 (str): the event whose occurrence is constrained by event1's past occurrence
        alphabet (list): the list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the precedence constraint
    """
    q0 = 'q0'
    q1 = 'q1'

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q0,q1}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
        elif symbol == event2:
            transitions[q1][symbol] = {q1}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q1}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )


def alternate_precedence_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Alternate precedence: Globally, If event2 occurs, then event1 must have happened before it, 
                            and no other event2 happened in between event1 and this event2.
    
    Args:
        event1 (str): the event that must precede event2 without any intermediate event2
        event2 (str): the event that must be preceded by event1 
        alphabet (list): the list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the alternate precedence constraint
    """
    q0 = 'q0'
    q1 = 'q1'

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q0,q1}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
        elif symbol != event2:
            transitions[q0][symbol] = {q0}

        if symbol == event2:
            transitions[q1][symbol] = {q0}
        else:
            transitions[q1][symbol] = {q1}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )


def chain_precedence_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Chain precedence: Globally, if event2 occurs, event1 must occur immediately before event2.
    
    Args:
        event1 (str): the event that must immediately precede event2
        event2 (str): the event constrained to be immediately after event1
        alphabet (list): the list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the chain precedence constraint
    """
    q0 = 'q0'
    q1 = 'q1'

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q0,q1}
    
    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q0,q1}
        elif symbol == event2:
            transitions[q1][symbol] = {q0}
        else:
            transitions[q0][symbol] = {q0}

    transitions = handle_end_placeholder(transitions, final_states)

    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )


##################################
#### NEG RELATION CONSTRAINTS ####
##################################

def not_responded_existence_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Not responded existence: Globally, if event1 occurs, then event2 must NOT occur before or after event1.
    
    Parameters:
        event1: The triggering event (string).
        event2: The forbidden event (string).
        alphabet: the list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the not responded existence constraint.
    """
    q0 = 'q0'
    q1 = 'q1'
    q2 = 'q2'

    states = {q0, q1, q2}
    transitions = {q0: {}, q1: {}, q2: {}}
    final_states={q0, q1, q2}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
        elif symbol == event2:
            transitions[q0][symbol] = {q2}
        else:
            transitions[q0][symbol] = {q0}

        if symbol != event2:
            transitions[q1][symbol] = {q1}
        
        if symbol != event1:
            transitions[q2][symbol] = {q2}        

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )
    

def not_co_existence_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Not Co-existence constraint: event1 and event2 cannot happen both (they both can also not happen).
    
    Parameters:
        event1: First mutually exclusive event (string).
        event2: Second mutually exclusive event (string).
        alphabet: The list of all possible events (input symbols)
        
    Returns:
        NFA: The NFA representing the not co-existence constraint.
    """
    q0 = 'q0'
    q1 = 'q1' 
    q2 = 'q2' 

    states = {q0, q1, q2}
    transitions = {q0: {}, q1: {}, q2: {}}
    final_states={q0, q1, q2}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
        elif symbol == event2:
            transitions[q0][symbol] = {q2}
            transitions[q2][symbol] = {q2}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q1}
            transitions[q2][symbol] = {q2}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )

def not_response_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Not response: Globally, if event1 occurs, then event2 must not occur at any point afterward.
    
    Parameters:
        event1: The triggering event (string).
        event2: The forbidden event following event1 (string).
        alphabet: The list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the not response constraint.
    """
    q0 = 'q0'
    q1 = 'q1'

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q0, q1}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
        else:
            transitions[q0][symbol] = {q0}

        if symbol != event2:
            transitions[q1][symbol] = {q1}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )


def not_precedence_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Not precedence: Globally, if event2 occurs, then event1 must not have occurred at any point before.
    
    Parameters:
        event1: The forbidden preceding event (string).
        event2: The event that triggers the constraint (string).
        alphabet: The list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the not precedence constraint.
    """
    q0 = 'q0'
    q1 = 'q1'
    q2 = 'q2'

    states = {q0, q1, q2}
    transitions = {q0: {}, q1: {}, q2: {}}
    final_states={q0,q1,q2}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
            transitions[q2][symbol] = {q1}
        elif symbol == event2:
            transitions[q0][symbol] = {q2}
            transitions[q2][symbol] = {q2}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q1}
            transitions[q2][symbol] = {q2}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )


def not_chain_response_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Not chain response: Globally, if event1 occurs, then event2 must not occur immediately after it.
    
    Parameters:
        event1: The triggering event (string).
        event2: The forbidden immediate successor event (string).
        alphabet: The list of all possible events (input symbols)

    Returns:
        NFA: The NFA representing the not chain response constraint.    
    """
    q0 = 'q0'
    q1 = 'q1'

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q0, q1}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
        elif symbol == event2:
            transitions[q0][symbol] = {q0}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q0}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )


def not_chain_precedence_constraint(event1: str, event2: str, alphabet: list) -> NFA:
    """
    Not chain precedence: Globally, if event2 occurs, then event1 must not have occurred in the immediately previous step.
    
    Parameters:
        event1: The forbidden immediate predecessor event (string).
        event2: The event that triggers the constraint (string).
        alphabet: The list of all possible events (input symbols)
        
    Returns:
        NFA: The NFA representing the not chain precedence constraint.    
    """
    q0 = 'q0'
    q1 = 'q1'

    states = {q0, q1}
    transitions = {q0: {}, q1: {}}
    final_states={q0,q1}

    for symbol in alphabet[:-1]:
        if symbol == event1:
            transitions[q0][symbol] = {q1}
            transitions[q1][symbol] = {q1}
        elif symbol == event2:
            transitions[q0][symbol] = {q0}
        else:
            transitions[q0][symbol] = {q0}
            transitions[q1][symbol] = {q0}

    transitions = handle_end_placeholder(transitions, final_states)
    
    return NFA(
        states=states,
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=q0,
        final_states=final_states
    )