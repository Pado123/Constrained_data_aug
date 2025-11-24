
from constraints.constants import END_PLACEHOLDER
from constraints.constraints_automata import (
    existence_constraint,
    absence_constraint,
    existence_exactly_once_constraint,
    init_constraint,
    last_constraint,
    
    choice_constraint,
    exclusive_choice_constraint,
    
    responded_existence_constraint,
    co_existence_constraint,
    response_constraint,
    alternate_response_constraint,
    chain_response_constraint,
    precedence_constraint,
    alternate_precedence_constraint,
    chain_precedence_constraint,
    not_responded_existence_constraint,
    not_co_existence_constraint,
    not_response_constraint,
    not_precedence_constraint,
    not_chain_response_constraint,
    not_chain_precedence_constraint,
)

alphabet = ['a', 'b', 'c', 'd', 'e', 'f',]
alphabet.append(END_PLACEHOLDER)

# Existence
nfa = existence_constraint('a', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_existence.png')

# Absence
nfa = absence_constraint('a', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_absence.png')

# Exactly once 
nfa = existence_exactly_once_constraint('a', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_existence_exactly_once.png')

# Init
nfa = init_constraint('a', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_init.png')

# End
nfa = last_constraint('a', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_last.png')

# Choice
nfa = choice_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_choice.png')

# Exclusive Choice
nfa = exclusive_choice_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_exclusive_choice.png')

# Responded Existence
nfa = responded_existence_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_responded_existence.png')

# Co-existence
nfa = co_existence_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_coexistence.png')

# Response
nfa = response_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_response.png')

# Alternate Response
nfa = alternate_response_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_alternate_response.png')

# Chain Response
nfa = chain_response_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_chain_response.png')

# Precedence
nfa = precedence_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_precedence.png')

# Alternate Precedence
nfa = alternate_precedence_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_alternate_precedence.png')

# Chain Precedence
nfa = chain_precedence_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_chain_precedence.png')

# Not Responded Existence
nfa = not_responded_existence_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_not_responded_existence.png')

# Not Co-existence
nfa = not_co_existence_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_not_coexistence.png')

# Not Response
nfa = not_response_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_not_response.png')

# Not Precedence
nfa = not_precedence_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_not_precedence.png')

# Not Chain Response
nfa = not_chain_response_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_not_chain_response.png')

# Not Chain Precedence
nfa = not_chain_precedence_constraint('a', 'b', alphabet)
nfa.show_diagram(path='constraints/constraints_plot/nfa_not_chain_precedence.png')