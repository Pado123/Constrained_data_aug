"""
Restructured constraints organized by experiment.

This file provides experiment-based constraint organization for automatic filtering.
Constraints are organized as: {case_study: {exp1: [...], exp2: [...], ...}}

Note: All constraints are currently enabled (uncommented) and ready to use.
"""

from constraints.constraints_automata import (
    existence_constraint,
    responded_existence_constraint,
    response_constraint,
    alternate_response_constraint,
    chain_response_constraint,
    precedence_constraint,
    alternate_precedence_constraint,
    chain_precedence_constraint,
    not_responded_existence_constraint,
    not_response_constraint,
    not_precedence_constraint,
    not_chain_response_constraint,
    not_chain_precedence_constraint,
    absence_constraint,
    existence_exactly_once_constraint,
    co_existence_constraint,
    not_co_existence_constraint,
    choice_constraint,
    exclusive_choice_constraint,
    init_constraint,
    last_constraint,
)


def _get_constraints_by_experiment(alphabet: list):
    """
    Returns constraints organized by case study and experiment.
    
    Structure: {case_study: {exp1: [constraints], exp2: [constraints], ...}}
    All constraints are currently enabled (uncommented).
    """
    return {
        'ds02': {
            'exp1': [
                init_constraint('Create Purchase Requisition_lc:start', alphabet),
            ],
            'exp2': [
                chain_response_constraint('Create Purchase Requisition_lc:complete', 'Create Request for Quotation_lc:start', alphabet)
            ],
            'exp3': [
                response_constraint('Create Quotation comparison Map_lc:complete', 'Analyze Quotation Comparison Map_lc:start', alphabet)
            ],
            'exp4': [
                init_constraint('Create Purchase Requisition_lc:start', alphabet),
                chain_response_constraint('Create Purchase Requisition_lc:complete', 'Create Request for Quotation_lc:start', alphabet),
                response_constraint('Create Quotation comparison Map_lc:complete', 'Analyze Quotation Comparison Map_lc:start', alphabet)
            ],
        },
        
        'ds03': {
            'exp1': [
                init_constraint('Turning & Milling_lc:start', alphabet),
            ],
            'exp2': [
                chain_response_constraint('Final Inspection Q.C._lc:complete', 'Packing_lc:start', alphabet)
            ],
            'exp3': [
                response_constraint('Turning & Milling_lc:complete', 'Turning & Milling Q.C._lc:start', alphabet),
                existence_constraint('Grinding Rework_lc:start', alphabet),
                existence_constraint('Grinding Rework_lc:complete', alphabet),
                init_constraint('Turning & Milling_lc:start', alphabet),
                chain_response_constraint('Final Inspection Q.C._lc:complete', 'Packing_lc:start', alphabet)
            ],
            'exp4': [
                response_constraint('Turning & Milling_lc:complete', 'Turning & Milling Q.C._lc:start', alphabet),
                existence_constraint('Grinding Rework_lc:start', alphabet),
                existence_constraint('Grinding Rework_lc:complete', alphabet),
                existence_constraint('Turning & Milling_lc:start', alphabet),
                existence_constraint('Turning & Milling_lc:complete', alphabet),
                chain_response_constraint('Final Inspection Q.C._lc:complete', 'Packing_lc:start', alphabet)
            ],
        },
        
        'ds01': {
            'exp1': [
                existence_constraint('ACT_FINAL_VALIDATION_lc:start', alphabet),
                existence_constraint('ACT_FINAL_VALIDATION_lc:complete', alphabet),
            ],
            'exp2': [
                init_constraint('Start_lc:start', alphabet),
            ],
            'exp3': [
                chain_response_constraint('ACT_CANCEL_REQUEST_lc:complete', 'ACT_NOTIFY_STUDENT_lc:start', alphabet),
            ],
            'exp4': [
                existence_constraint('ACT_FINAL_VALIDATION_lc:start', alphabet),
                existence_constraint('ACT_FINAL_VALIDATION_lc:complete', alphabet),
                init_constraint('Start_lc:start', alphabet),
                chain_response_constraint('ACT_CANCEL_REQUEST_lc:complete', 'ACT_NOTIFY_STUDENT_lc:start', alphabet),
                response_constraint('ACT_FINAL_VALIDATION_lc:complete', 'ACT_APPROVE_CLOSE_lc:start', alphabet),
                existence_exactly_once_constraint('ACT_TRANSFER_CREDITS_lc:start', alphabet),
                existence_exactly_once_constraint('ACT_TRANSFER_CREDITS_lc:complete', alphabet),
            ],
        },
        
        'bpi12': {
            'exp1': [
                existence_constraint('W_Nabellen incomplete dossiers_lc:start', alphabet),
                existence_constraint('W_Nabellen incomplete dossiers_lc:complete', alphabet)
            ],
            'exp2': [
                init_constraint('W_Afhandelen leads_lc:start', alphabet),
            ],
            'exp3': [
                existence_constraint('W_Valideren aanvraag_lc:start', alphabet),
                existence_constraint('W_Valideren aanvraag_lc:complete', alphabet),
                existence_constraint('W_Nabellen incomplete dossiers_lc:start', alphabet),
                existence_constraint('W_Nabellen incomplete dossiers_lc:complete', alphabet),
                init_constraint('W_Afhandelen leads_lc:start', alphabet),
            ],
            'exp4': [
                init_constraint('W_Afhandelen leads_lc:start', alphabet),
                chain_response_constraint('W_Completeren aanvraag_lc:complete','W_Nabellen offertes_lc:start', alphabet),
                chain_response_constraint('W_Nabellen offertes_lc:complete','W_Valideren aanvraag_lc:start', alphabet),
                existence_constraint('W_Nabellen incomplete dossiers_lc:start', alphabet),
                existence_constraint('W_Nabellen incomplete dossiers_lc:complete', alphabet),
            ],
        },
        
        'bpi12a': {
            'exp1': [
                chain_response_constraint('A_ACCEPTED_lc:complete', 'A_FINALIZED_lc:complete', alphabet),
                chain_response_constraint('A_FINALIZED_lc:complete','A_APPROVED_lc:complete', alphabet),
                chain_precedence_constraint('A_APPROVED_lc:complete','A_REGISTERED_lc:complete', alphabet),
            ],
            'exp2': [
                chain_response_constraint('A_PREACCEPTED_lc:complete', 'A_DECLINED_lc:complete', alphabet)
            ],
            'exp3': [
                chain_response_constraint('A_PREACCEPTED_lc:complete', 'A_DECLINED_lc:complete', alphabet),
                existence_constraint('A_PREACCEPTED_lc:complete', alphabet)
            ],
        },
        
        'bpi12o': {
            'exp1': [
                chain_response_constraint('O_SELECTED_lc:complete', 'O_CREATED_lc:complete', alphabet),
                not_chain_response_constraint('O_SENT_lc:complete', 'O_SELECTED_lc:complete', alphabet),
                not_chain_response_constraint('O_SENT_BACK_lc:complete', 'O_SELECTED_lc:complete', alphabet),
            ],
            'exp2': [
                chain_response_constraint('O_SELECTED_lc:complete', 'O_CREATED_lc:complete', alphabet),
                not_chain_response_constraint('O_SENT_lc:complete', 'O_SELECTED_lc:complete', alphabet),
                not_chain_response_constraint('O_SENT_BACK_lc:complete', 'O_SELECTED_lc:complete', alphabet),
                existence_constraint('O_SENT_BACK_lc:complete', alphabet)
            ],
        },
        
        'bpi17': {
            'exp1': [
                existence_constraint('W_Call incomplete files_lc:start', alphabet),
                existence_constraint('W_Call incomplete files_lc:complete', alphabet)
            ],
            'exp2': [
                init_constraint('W_Complete application_lc:start', alphabet)
            ],
            'exp3': [
                existence_constraint('W_Validate application_lc:start', alphabet),
                existence_constraint('W_Validate application_lc:complete', alphabet)
            ],
            'exp4': [
                init_constraint('W_Complete application_lc:start', alphabet),
                existence_exactly_once_constraint('W_Validate application_lc:start', alphabet),
                existence_exactly_once_constraint('W_Validate application_lc:complete', alphabet),
            ],
        },
        
        'bpi17o': {
            'exp1': [
                exclusive_choice_constraint('O_Sent (online only)_lc:complete','O_Sent (mail and online)_lc:complete', alphabet),
                not_chain_precedence_constraint('O_Created_lc:complete', 'O_Refused_lc:complete', alphabet),
                not_chain_precedence_constraint('O_Sent (online only)_lc:complete', 'O_Refused_lc:complete', alphabet),
                not_chain_precedence_constraint('O_Sent (mail and online)_lc:complete', 'O_Refused_lc:complete', alphabet),
                chain_precedence_constraint('O_Returned:complete','O_Refused_lc:complete', alphabet),
            ],
            'exp2': [
                response_constraint('O_Sent (online only)_lc:complete', 'O_Returned_lc:complete', alphabet),
                response_constraint('O_Sent (mail and online)_lc:complete', 'O_Returned_lc:complete', alphabet),
            ],
        },
        
        'ds06': {
            'exp1': [
                precedence_constraint('ACT_DISCHARGE_lc:complete', 'ACT_EXIT_lc:start', alphabet),
            ],
            'exp2': [
                chain_response_constraint('ACT_INTAKE_lc:complete', 'ACT_TRIAGE_lc:start', alphabet),
                not_co_existence_constraint('ACT_CONSULT_A_lc:start', 'ACT_CONSULT_B_lc:start', alphabet),
                precedence_constraint('ACT_CONSULT_A_lc:complete', 'ACT_OBSERVATION_lc:start', alphabet),
                chain_response_constraint('RAD_REQ_RX_lc:start', 'RAD_REQ_RX_lc:complete', alphabet),
                chain_response_constraint('RAD_REQ_RX_lc:complete', 'RAD_ACC_RX_lc:start', alphabet),
                chain_response_constraint('RAD_ACC_RX_lc:start', 'RAD_ACC_RX_lc:complete', alphabet),
                chain_response_constraint('RAD_ACC_RX_lc:complete', 'RAD_EXEC_RX_lc:start', alphabet),
                chain_response_constraint('RAD_EXEC_RX_lc:start', 'RAD_EXEC_RX_lc:complete', alphabet),
                chain_response_constraint('RAD_EXEC_RX_lc:complete', 'RAD_REP_RX_lc:start', alphabet),
                chain_response_constraint('RAD_REP_RX_lc:start', 'RAD_REP_RX_lc:complete', alphabet),
                chain_response_constraint('RAD_REQ_US_lc:start', 'RAD_REQ_US_lc:complete', alphabet),
                chain_response_constraint('RAD_REQ_US_lc:complete', 'RAD_ACC_US_lc:start', alphabet),
                chain_response_constraint('RAD_ACC_US_lc:start', 'RAD_ACC_US_lc:complete', alphabet),
                chain_response_constraint('RAD_ACC_US_lc:complete', 'RAD_EXEC_US_lc:start', alphabet),
                chain_response_constraint('RAD_EXEC_US_lc:start', 'RAD_EXEC_US_lc:complete', alphabet),
                chain_response_constraint('RAD_EXEC_US_lc:complete', 'RAD_REP_US_lc:start', alphabet),
                chain_response_constraint('RAD_REP_US_lc:start', 'RAD_REP_US_lc:complete', alphabet),
                chain_response_constraint('ACT_DISCHARGE_lc:complete', 'ACT_EXIT_lc:start', alphabet),
            ],
            'exp3': [
                init_constraint('ACT_INTAKE_lc:start', alphabet),
                chain_response_constraint('ACT_INTAKE_lc:complete', 'ACT_TRIAGE_lc:start', alphabet),
                chain_response_constraint('ACT_TRIAGE_lc:complete', 'ACT_VISIT_lc:start', alphabet),
                chain_response_constraint('ACT_VISIT_lc:start', 'ACT_VISIT_lc:complete', alphabet),
                responded_existence_constraint('ACT_BLOOD_DRAW_lc:complete', 'ACT_BLOOD_TEST_lc:complete', alphabet),
                responded_existence_constraint('ACT_BLOOD_TEST_lc:complete', 'ACT_BLOOD_DRAW_lc:complete', alphabet),
                not_co_existence_constraint('ACT_CONSULT_A_lc:start', 'ACT_CONSULT_B_lc:start', alphabet),
                precedence_constraint('ACT_CONSULT_A_lc:complete', 'ACT_OBSERVATION_lc:start', alphabet),
                chain_response_constraint('ACT_DISCHARGE_lc:complete', 'ACT_EXIT_lc:start', alphabet),
                not_response_constraint('ACT_DISCHARGE_lc:complete', 'ACT_ORTHO_CONSULT_lc:start', alphabet),
            ],
            'exp4': [
                init_constraint('ACT_INTAKE_lc:start', alphabet),
                chain_response_constraint('ACT_INTAKE_lc:complete', 'ACT_TRIAGE_lc:start', alphabet),
                chain_response_constraint('ACT_TRIAGE_lc:complete', 'ACT_VISIT_lc:start', alphabet),
                chain_response_constraint('ACT_VISIT_lc:start', 'ACT_VISIT_lc:complete', alphabet),
                precedence_constraint('ACT_CONSULT_A_lc:complete', 'ACT_OBSERVATION_lc:start', alphabet),
                chain_response_constraint('ACT_DISCHARGE_lc:complete', 'ACT_EXIT_lc:start', alphabet),
            ],
        },
    }


def get_log_constraints_by_experiment(log_name: str, alphabet: list, experiment: str = None):
    """
    Get constraints (NFAs) for a specific experiment from the restructured format.
    
    Args:
        log_name: Name of the case study
        alphabet: List of activities
        experiment: Experiment identifier (exp1, exp2, exp3, exp4) or None for all experiments
    
    Returns:
        List of constraint NFAs (only uncommented constraints will be in the list)
    """
    constraints_dict = _get_constraints_by_experiment(alphabet)
    
    if log_name not in constraints_dict:
        return []
    
    if experiment:
        # Return constraints for specific experiment
        # When constraints are uncommented, they're already NFAs
        # When commented, they're not in the list at all
        return constraints_dict[log_name].get(experiment, [])
    else:
        # Return all constraints from all experiments (flat list)
        all_constraints = []
        for exp_constraints in constraints_dict[log_name].values():
            all_constraints.extend(exp_constraints)
        return all_constraints

