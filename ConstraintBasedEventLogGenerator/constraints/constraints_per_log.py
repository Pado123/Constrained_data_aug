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
from automata.fa.nfa import NFA 


def get_log_constraints(log_name: str,alphabet: list):

    log_constraints = {

        'Purchasing' :
            [                
                # EXP1
                # init_constraint('Create Purchase Requisition_lc:start', alphabet),
                
                # EXP2
                # chain_response_constraint('Create Purchase Requisition_lc:complete', 'Create Request for Quotation_lc:start', alphabet)
                
                # EXP3
                # response_constraint('Create Quotation comparison Map_lc:complete', 'Analyze Quotation Comparison Map_lc:start', alphabet)
                
                # EXP4
                # init_constraint('Create Purchase Requisition_lc:start', alphabet),
                # chain_response_constraint('Create Purchase Requisition_lc:complete', 'Create Request for Quotation_lc:start', alphabet),
                # response_constraint('Create Quotation comparison Map_lc:complete', 'Analyze Quotation Comparison Map_lc:start', alphabet)                
            ],
 
        'Production' :
            [               
                # EXP1
                # init_constraint('Turning & Milling_lc:start', alphabet), 
                
                # EXP2
                # chain_response_constraint('Final Inspection Q.C._lc:complete', 'Packing_lc:start', alphabet)
                
                # EXP3
                # response_constraint('Turning & Milling_lc:complete', 'Turning & Milling Q.C._lc:start', alphabet),
                # existence_constraint('Grinding Rework_lc:start', alphabet),
                # existence_constraint('Grinding Rework_lc:complete', alphabet),
                # init_constraint('Turning & Milling_lc:start', alphabet), 
                # chain_response_constraint('Final Inspection Q.C._lc:complete', 'Packing_lc:start', alphabet)
                
                # EXP4
                # response_constraint('Turning & Milling_lc:complete', 'Turning & Milling Q.C._lc:start', alphabet),
                # existence_constraint('Grinding Rework_lc:start', alphabet),
                # existence_constraint('Grinding Rework_lc:complete', alphabet),
                # existence_constraint('Turning & Milling_lc:start', alphabet),
                # existence_constraint('Turning & Milling_lc:complete', alphabet),                
                # chain_response_constraint('Final Inspection Q.C._lc:complete', 'Packing_lc:start', alphabet)
            ],
            
        'Consulta' :
            [ 
                # EXP1
                # existence_constraint('Validacion final_lc:start', alphabet),
                # existence_constraint('Validacion final_lc:complete', alphabet),
                
                # EXP2
                # init_constraint('Start_lc:start', alphabet), 
                
                # # EXP3
                # chain_response_constraint('Cancelar Solicitud_lc:complete', 'Notificacion estudiante cancelacion soli_lc:start', alphabet),
                
                # #  EXP4
                # existence_constraint('Validacion final_lc:start', alphabet),
                # existence_constraint('Validacion final_lc:complete', alphabet),
                # init_constraint('Start_lc:start', alphabet), 
                # chain_response_constraint('Cancelar Solicitud_lc:complete', 'Notificacion estudiante cancelacion soli_lc:start', alphabet),
                # response_constraint('Validacion final_lc:complete', 'Visto Bueno Cierre Proceso_lc:start', alphabet),
                # existence_exactly_once_constraint('Transferir creditos homologables_lc:start', alphabet),
                # existence_exactly_once_constraint('Transferir creditos homologables_lc:complete', alphabet),

            ],

        'bpi12' :
            [
                # EXP1
                # existence_constraint('W_Nabellen incomplete dossiers_lc:start', alphabet),
                # existence_constraint('W_Nabellen incomplete dossiers_lc:complete', alphabet)
                
                # EXP2
                # init_constraint('W_Afhandelen leads_lc:start', alphabet), 
                
                # EXP3
                # existence_constraint('W_Valideren aanvraag_lc:start', alphabet),
                # existence_constraint('W_Valideren aanvraag_lc:complete', alphabet),                
                # existence_constraint('W_Nabellen incomplete dossiers_lc:start', alphabet),
                # existence_constraint('W_Nabellen incomplete dossiers_lc:complete', alphabet),
                # init_constraint('W_Afhandelen leads_lc:start', alphabet),           
                
                # EXP4
                # init_constraint('W_Afhandelen leads_lc:start', alphabet),      
                # chain_response_constraint('W_Completeren aanvraag_lc:complete','W_Nabellen offertes_lc:start', alphabet),
                # chain_response_constraint('W_Nabellen offertes_lc:complete','W_Valideren aanvraag_lc:start', alphabet), 
                # existence_constraint('W_Nabellen incomplete dossiers_lc:start', alphabet),
                # existence_constraint('W_Nabellen incomplete dossiers_lc:complete', alphabet),             
                
            ],
            
        'bpi12a' :
            [
                # EXP1
                # chain_response_constraint('A_ACCEPTED_lc:complete', 'A_FINALIZED_lc:complete',alphabet),
                # chain_response_constraint('A_FINALIZED_lc:complete','A_APPROVED_lc:complete', alphabet),
                # chain_precedence_constraint('A_APPROVED_lc:complete','A_REGISTERED_lc:complete',alphabet),
                
                #EXP 2
                # chain_response_constraint('A_PREACCEPTED_lc:complete', 'A_DECLINED_lc:complete', alphabet)
                
                #EXP 3
                # chain_response_constraint('A_PREACCEPTED_lc:complete', 'A_DECLINED_lc:complete', alphabet),
                # existence_constraint('A_PREACCEPTED_lc:complete', alphabet)
            ],

        'bpi12o' :
            [
                # EXP1
                # chain_response_constraint('O_SELECTED_lc:complete', 'O_CREATED_lc:complete',alphabet),
                # not_chain_response_constraint('O_SENT_lc:complete', 'O_SELECTED_lc:complete',alphabet),
                # not_chain_response_constraint('O_SENT_BACK_lc:complete', 'O_SELECTED_lc:complete',alphabet),
                
                # # EXP2
                # chain_response_constraint('O_SELECTED_lc:complete', 'O_CREATED_lc:complete',alphabet),
                # not_chain_response_constraint('O_SENT_lc:complete', 'O_SELECTED_lc:complete',alphabet),
                # not_chain_response_constraint('O_SENT_BACK_lc:complete', 'O_SELECTED_lc:complete',alphabet),
                # existence_constraint('O_SENT_BACK_lc:complete',alphabet)
                

            ],
            
        'bpi17' :
            [               
                # EXP1
                # existence_constraint('W_Call incomplete files_lc:start', alphabet),
                # existence_constraint('W_Call incomplete files_lc:complete', alphabet)
                
                
                # EXP2
                # init_constraint('W_Complete application_lc:start', alphabet)
                
                # EXP3
                # existence_constraint('W_Validate application_lc:start', alphabet),
                # existence_constraint('W_Validate application_lc:complete', alphabet)
                
                # EXP4
                # init_constraint('W_Complete application_lc:start', alphabet),
                # existence_exactly_once_constraint('W_Validate application_lc:start',alphabet),
                # existence_exactly_once_constraint('W_Validate application_lc:complete',alphabet),
                  
            ],
            
        'bpi17o' :
            [
                # EXP1                
                
                # exclusive_choice_constraint('O_Sent (online only)_lc:complete','O_Sent (mail and online)_lc:complete', alphabet),
                # not_chain_precedence_constraint('O_Created_lc:complete', 'O_Refused_lc:complete',alphabet),
                # not_chain_precedence_constraint('O_Sent (online only)_lc:complete', 'O_Refused_lc:complete',alphabet),
                # not_chain_precedence_constraint('O_Sent (mail and online)_lc:complete', 'O_Refused_lc:complete',alphabet),
                
                # i tre qua sopra in realta' sono questo
                # chain_precedence_constraint('O_Returned:complete','O_Refused_lc:complete',alphabet),
                
                # EXP2
                # response_constraint('O_Sent (online only)_lc:complete', 'O_Returned_lc:complete', alphabet),
                # response_constraint('O_Sent (mail and online)_lc:complete', 'O_Returned_lc:complete', alphabet),
            ],
            
        'hospital':
            [
                
                # EXP1
                # precedence_constraint('DIMISSIONE_lc:complete','USCITA_lc:start', alphabet),
                
                # EXP2
                # chain_response_constraint('ACCESSO_lc:complete', 'TRIAGE_lc:start', alphabet),
                                
                # not_co_existence_constraint('CONSULENZA: Pediatria_lc:start', 'CONSULENZA: Oculistica_lc:start', alphabet),
                # precedence_constraint('CONSULENZA: Pediatria_lc:complete', 'OSSERVAZIONE: OBI Pediatrica OSPEDALE_lc:start', alphabet),

                # chain_response_constraint('RADIOLOGIA RICHIESTA: RX_lc:start', 'RADIOLOGIA RICHIESTA: RX_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: RX_lc:complete', 'RADIOLOGIA ACCETTAZIONE: RX_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RX_lc:start', 'RADIOLOGIA ACCETTAZIONE: RX_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RX_lc:complete', 'RADIOLOGIA ESECUZIONE: RX_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RX_lc:start', 'RADIOLOGIA ESECUZIONE: RX_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RX_lc:complete', 'RADIOLOGIA REFERTAZIONE: RX_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: RX_lc:start', 'RADIOLOGIA REFERTAZIONE: RX_lc:complete', alphabet), 
                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: ECO_lc:start', 'RADIOLOGIA RICHIESTA: ECO_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: ECO_lc:complete', 'RADIOLOGIA ACCETTAZIONE: ECO_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: ECO_lc:start', 'RADIOLOGIA ACCETTAZIONE: ECO_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: ECO_lc:complete', 'RADIOLOGIA ESECUZIONE: ECO_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: ECO_lc:start', 'RADIOLOGIA ESECUZIONE: ECO_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: ECO_lc:complete', 'RADIOLOGIA REFERTAZIONE: ECO_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: ECO_lc:start', 'RADIOLOGIA REFERTAZIONE: ECO_lc:complete', alphabet), 
                
                # chain_response_constraint('DIMISSIONE_lc:complete','USCITA_lc:start', alphabet),      
                    
                
                # #EXP3
                # init_constraint('ACCESSO_lc:start', alphabet),
                # chain_response_constraint('ACCESSO_lc:complete', 'TRIAGE_lc:start', alphabet),
                
                # chain_response_constraint('TRIAGE_lc:complete', 'VISITA_lc:start', alphabet),
                
                # chain_response_constraint('VISITA_lc:start', 'VISITA_lc:complete',alphabet),
                
                # responded_existence_constraint('PRELIEVO ARTERIOSO_lc:complete', 'EMOGASANALISI_lc:complete', alphabet),
                # responded_existence_constraint('EMOGASANALISI_lc:complete', 'PRELIEVO ARTERIOSO_lc:complete',  alphabet),
                                
                # not_co_existence_constraint('CONSULENZA: Pediatria_lc:start', 'CONSULENZA: Oculistica_lc:start', alphabet),
                
                # precedence_constraint('CONSULENZA: Pediatria_lc:complete', 'OSSERVAZIONE: OBI Pediatrica OSPEDALE_lc:start', alphabet),

                # chain_response_constraint('RADIOLOGIA RICHIESTA: RX_lc:start', 'RADIOLOGIA RICHIESTA: RX_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: RX_lc:complete', 'RADIOLOGIA ACCETTAZIONE: RX_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RX_lc:start', 'RADIOLOGIA ACCETTAZIONE: RX_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RX_lc:complete', 'RADIOLOGIA ESECUZIONE: RX_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RX_lc:start', 'RADIOLOGIA ESECUZIONE: RX_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RX_lc:complete', 'RADIOLOGIA REFERTAZIONE: RX_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: RX_lc:start', 'RADIOLOGIA REFERTAZIONE: RX_lc:complete', alphabet), 
                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: ECO_lc:start', 'RADIOLOGIA RICHIESTA: ECO_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: ECO_lc:complete', 'RADIOLOGIA ACCETTAZIONE: ECO_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: ECO_lc:start', 'RADIOLOGIA ACCETTAZIONE: ECO_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: ECO_lc:complete', 'RADIOLOGIA ESECUZIONE: ECO_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: ECO_lc:start', 'RADIOLOGIA ESECUZIONE: ECO_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: ECO_lc:complete', 'RADIOLOGIA REFERTAZIONE: ECO_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: ECO_lc:start', 'RADIOLOGIA REFERTAZIONE: ECO_lc:complete', alphabet), 
                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: TAC_lc:start', 'RADIOLOGIA RICHIESTA: TAC_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: TAC_lc:complete', 'RADIOLOGIA ACCETTAZIONE: TAC_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: TAC_lc:start', 'RADIOLOGIA ACCETTAZIONE: TAC_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: TAC_lc:complete', 'RADIOLOGIA ESECUZIONE: TAC_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: TAC_lc:start', 'RADIOLOGIA ESECUZIONE: TAC_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: TAC_lc:complete', 'RADIOLOGIA REFERTAZIONE: TAC_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: TAC_lc:start', 'RADIOLOGIA REFERTAZIONE: TAC_lc:complete', alphabet),  
                
                # precedence_constraint('RADIOLOGIA REFERTAZIONE: TAC_lc:complete','RADIOLOGIA RICHIESTA: Angio_lc:start', alphabet),
                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: Angio_lc:start', 'RADIOLOGIA RICHIESTA: Angio_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: Angio_lc:complete', 'RADIOLOGIA ACCETTAZIONE: Angio_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: Angio_lc:start', 'RADIOLOGIA ACCETTAZIONE: Angio_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: Angio_lc:complete', 'RADIOLOGIA ESECUZIONE: Angio_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: Angio_lc:start', 'RADIOLOGIA ESECUZIONE: Angio_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: Angio_lc:complete', 'RADIOLOGIA REFERTAZIONE: Angio_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: Angio_lc:start', 'RADIOLOGIA REFERTAZIONE: Angio_lc:complete', alphabet),                     
                
                # precedence_constraint('RADIOLOGIA REFERTAZIONE: TAC_lc:complete', 'RADIOLOGIA RICHIESTA: RMN_lc:start', alphabet),
                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: RMN_lc:start', 'RADIOLOGIA RICHIESTA: RMN_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: RMN_lc:complete', 'RADIOLOGIA ACCETTAZIONE: RMN_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RMN_lc:start', 'RADIOLOGIA ACCETTAZIONE: RMN_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RMN_lc:complete', 'RADIOLOGIA ESECUZIONE: RMN_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RMN_lc:start', 'RADIOLOGIA ESECUZIONE: RMN_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RMN_lc:complete', 'RADIOLOGIA REFERTAZIONE: RMN_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: RMN_lc:start', 'RADIOLOGIA REFERTAZIONE: RMN_lc:complete', alphabet),    
                
                # chain_response_constraint('DIMISSIONE_lc:complete','USCITA_lc:start', alphabet),    
                
                # not_response_constraint('DIMISSIONE_lc:complete', 'CONSULENZA: Ortopedia e traumatologia_lc:start',alphabet) ,     
                            
                
                #EXP4
                # init_constraint('ACCESSO_lc:start', alphabet),
                # chain_response_constraint('ACCESSO_lc:complete', 'TRIAGE_lc:start', alphabet),
                
                # chain_response_constraint('TRIAGE_lc:complete', 'VISITA_lc:start', alphabet),
                
                # chain_response_constraint('VISITA_lc:start', 'VISITA_lc:complete',alphabet),
                
                # precedence_constraint('CONSULENZA: Pediatria_lc:complete', 'OSSERVAZIONE: OBI Pediatrica OSPEDALE_lc:start', alphabet),

                # chain_response_constraint('RADIOLOGIA RICHIESTA: RX_lc:start', 'RADIOLOGIA RICHIESTA: RX_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: RX_lc:complete', 'RADIOLOGIA ACCETTAZIONE: RX_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RX_lc:start', 'RADIOLOGIA ACCETTAZIONE: RX_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RX_lc:complete', 'RADIOLOGIA ESECUZIONE: RX_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RX_lc:start', 'RADIOLOGIA ESECUZIONE: RX_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RX_lc:complete', 'RADIOLOGIA REFERTAZIONE: RX_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: RX_lc:start', 'RADIOLOGIA REFERTAZIONE: RX_lc:complete', alphabet), 
                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: ECO_lc:start', 'RADIOLOGIA RICHIESTA: ECO_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: ECO_lc:complete', 'RADIOLOGIA ACCETTAZIONE: ECO_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: ECO_lc:start', 'RADIOLOGIA ACCETTAZIONE: ECO_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: ECO_lc:complete', 'RADIOLOGIA ESECUZIONE: ECO_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: ECO_lc:start', 'RADIOLOGIA ESECUZIONE: ECO_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: ECO_lc:complete', 'RADIOLOGIA REFERTAZIONE: ECO_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: ECO_lc:start', 'RADIOLOGIA REFERTAZIONE: ECO_lc:complete', alphabet), 
                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: TAC_lc:start', 'RADIOLOGIA RICHIESTA: TAC_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: TAC_lc:complete', 'RADIOLOGIA ACCETTAZIONE: TAC_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: TAC_lc:start', 'RADIOLOGIA ACCETTAZIONE: TAC_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: TAC_lc:complete', 'RADIOLOGIA ESECUZIONE: TAC_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: TAC_lc:start', 'RADIOLOGIA ESECUZIONE: TAC_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: TAC_lc:complete', 'RADIOLOGIA REFERTAZIONE: TAC_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: TAC_lc:start', 'RADIOLOGIA REFERTAZIONE: TAC_lc:complete', alphabet),  
                
                # precedence_constraint('RADIOLOGIA REFERTAZIONE: TAC_lc:complete','RADIOLOGIA RICHIESTA: Angio_lc:start', alphabet),
                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: Angio_lc:start', 'RADIOLOGIA RICHIESTA: Angio_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: Angio_lc:complete', 'RADIOLOGIA ACCETTAZIONE: Angio_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: Angio_lc:start', 'RADIOLOGIA ACCETTAZIONE: Angio_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: Angio_lc:complete', 'RADIOLOGIA ESECUZIONE: Angio_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: Angio_lc:start', 'RADIOLOGIA ESECUZIONE: Angio_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: Angio_lc:complete', 'RADIOLOGIA REFERTAZIONE: Angio_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: Angio_lc:start', 'RADIOLOGIA REFERTAZIONE: Angio_lc:complete', alphabet),                     
                
                # precedence_constraint('RADIOLOGIA REFERTAZIONE: TAC_lc:complete', 'RADIOLOGIA RICHIESTA: RMN_lc:start', alphabet),
                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: RMN_lc:start', 'RADIOLOGIA RICHIESTA: RMN_lc:complete', alphabet),                
                # chain_response_constraint('RADIOLOGIA RICHIESTA: RMN_lc:complete', 'RADIOLOGIA ACCETTAZIONE: RMN_lc:start', alphabet),
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RMN_lc:start', 'RADIOLOGIA ACCETTAZIONE: RMN_lc:complete', alphabet),  
                # chain_response_constraint('RADIOLOGIA ACCETTAZIONE: RMN_lc:complete', 'RADIOLOGIA ESECUZIONE: RMN_lc:start', alphabet),    
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RMN_lc:start', 'RADIOLOGIA ESECUZIONE: RMN_lc:complete', alphabet),             
                # chain_response_constraint('RADIOLOGIA ESECUZIONE: RMN_lc:complete', 'RADIOLOGIA REFERTAZIONE: RMN_lc:start', alphabet),                  
                # chain_response_constraint('RADIOLOGIA REFERTAZIONE: RMN_lc:start', 'RADIOLOGIA REFERTAZIONE: RMN_lc:complete', alphabet),    
                
                # chain_response_constraint('DIMISSIONE_lc:complete','USCITA_lc:start', alphabet),    
                
            ]

    }

    
    return log_constraints[log_name]


def create_nfa_constraints(log_name: str,alphabet: list) -> NFA :
    constraints_nfa_list = get_log_constraints(log_name,alphabet)

    nfa_constraints = constraints_nfa_list[0]
    for next_nfa in constraints_nfa_list[1:]:
        nfa_constraints = nfa_constraints.intersection(next_nfa)
    
    return nfa_constraints