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
from pm4py.algo.discovery.declare import algorithm as declare_discovery
from pm4py.algo.discovery.declare.variants import classic as declare_classic
from typing import Any, Dict, List, Optional, Tuple
import os
import numpy as np
from tqdm import tqdm
from pathlib import Path
import hashlib
import json
import pickle
import pandas as pd
import random
import time


def get_top_k_mined_constraints(
    log,
    alphabet: list,
    k: int,
    log_name: str = "",
) -> List[Tuple[str, Any]]:
    """
    Mine Declare constraints from log and return top-k as [(template, activities), ...].
    Uses form_rules_table when DECLARE_USE_FORM_RULES_TABLE=1 to match percentage_declare_traces.
    """
    use_form_rules = os.getenv("DECLARE_USE_FORM_RULES_TABLE", "0").strip() == "1"
    ranking_mode = _resolve_constraint_ranking_mode()
    n_traces = len(log) if log else 0

    if not use_form_rules:
        raise ValueError("get_top_k_mined_constraints requires DECLARE_USE_FORM_RULES_TABLE=1")

    params = {declare_classic.Parameters.ACTIVITY_KEY: "concept:name"}
    rules_df = declare_classic.form_rules_table(log, parameters=params)

    rows: List[Tuple[float, int, int, str, Any]] = []
    for col_name in rules_df.columns:
        col = rules_df[col_name]
        support_count = int((col != 0).sum())
        confidence_count = int((col == 1).sum())
        satisfied_ratio = (float(confidence_count) / float(n_traces)) if n_traces > 0 else 0.0
        if support_count == 0:
            continue
        template_name, rule_key = declare_classic.__col_to_dict_rule(col_name)
        rows.append((satisfied_ratio, confidence_count, support_count, template_name, rule_key))

    if ranking_mode == "support_confidence":
        rows.sort(key=lambda x: (x[2], x[1], x[0]), reverse=True)
    else:
        rows.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

    top_k = [(template, rule_key) for (_, _, _, template, rule_key) in rows[:k]]
    return top_k


def trace_satisfies_constraint(
    trace,
    template: str,
    acts: Any,
    alphabet: list,
    nfa_cache: dict,
) -> bool:
    """
    Check if a trace satisfies one Declare constraint.
    Same logic as percentage_declare_traces.trace_satisfies_constraint.
    """
    cache_key = (str(template), repr(acts))
    if cache_key not in nfa_cache:
        candidate_nfas = _declare_template_to_nfa_list(template, acts, alphabet)
        if not candidate_nfas:
            nfa_cache[cache_key] = None
        else:
            constraint_nfa = candidate_nfas[0]
            for next_nfa in candidate_nfas[1:]:
                constraint_nfa = constraint_nfa.intersection(next_nfa)
            nfa_cache[cache_key] = constraint_nfa

    constraint_nfa = nfa_cache[cache_key]
    if constraint_nfa is None:
        return True

    from constraints.constants import END_PLACEHOLDER
    event_seq = [event["concept:name"] for event in trace]
    event_seq.append(END_PLACEHOLDER)
    return constraint_nfa.accepts_input(event_seq)


def _resolve_constraint_ranking_mode() -> str:
    """
    Resolve ranking mode used to order discovered constraints.
    Supported values:
      - satisfied_ratio: sort by (satisfied/total traces), then confidence, then support
      - support_confidence: sort by support, then confidence
    """
    raw_mode = os.getenv("DECLARE_CONSTRAINT_RANKING_MODE", "satisfied_ratio")
    mode = str(raw_mode).strip().lower()
    aliases = {
        "satisfied_ratio": "satisfied_ratio",
        "ratio": "satisfied_ratio",
        "support_confidence": "support_confidence",
        "support": "support_confidence",
    }
    if mode in aliases:
        return aliases[mode]
    print(
        f"[WARN] Unknown DECLARE_CONSTRAINT_RANKING_MODE='{raw_mode}'. "
        "Using 'satisfied_ratio'."
    )
    return "satisfied_ratio"


def _current_rss_gb() -> float:
    """Best-effort RSS in GB (Linux /proc), used for lightweight profiling."""
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    kb = float(line.split()[1])
                    return kb / (1024.0 * 1024.0)
    except Exception:
        return 0.0
    return 0.0


def _nfa_size_stats(nfa: Optional[NFA]) -> Tuple[int, int]:
    """Return (num_states, num_transitions) for profiling and guardrails."""
    if nfa is None:
        return 0, 0
    n_states = len(getattr(nfa, "states", []))
    transitions = getattr(nfa, "transitions", {}) or {}
    n_transitions = 0
    for symbol_targets in transitions.values():
        for targets in symbol_targets.values():
            n_transitions += len(targets)
    return int(n_states), int(n_transitions)


def get_log_constraints(log_name: str,alphabet: list):

    log_constraints = {

        'ds02' :
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
 
        'ds03' :
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
            
        'ds01' :
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
                
                # equivalent to the three constraints above combined
                # chain_precedence_constraint('O_Returned:complete','O_Refused_lc:complete',alphabet),
                
                # EXP2
                # response_constraint('O_Sent (online only)_lc:complete', 'O_Returned_lc:complete', alphabet),
                # response_constraint('O_Sent (mail and online)_lc:complete', 'O_Returned_lc:complete', alphabet),
            ],
            
        'ds06':
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

    
    # Unknown/new case studies should not crash fallback resolution.
    # Return an empty list so caller can continue with mined constraints
    # or produce a clear "no constraints found" error.
    return log_constraints.get(log_name, [])


def get_log_constraints_by_experiment(log_name: str, alphabet: list, experiment: str = None):
    """
    Get constraints for a specific experiment.
    
    This function attempts to extract constraints for a specific experiment by:
    1. First trying the restructured format (if available)
    2. Falling back to the original flat list format
    
    Args:
        log_name: Name of the case study
        alphabet: List of activities
        experiment: Experiment identifier (exp1, exp2, exp3, exp4) or None for all active constraints
    
    Returns:
        List of constraint NFAs for the specified experiment
    """
    # Try to import and use restructured constraints
    try:
        from constraints.constraints_per_log_restructured import _get_constraints_by_experiment
        
        constraints_dict = _get_constraints_by_experiment(alphabet)
        
        if log_name not in constraints_dict:
            # Case study not in restructured format, fall back
            pass
        else:
            # Get constraints for this case study
            if experiment:
                # Get constraints for specific experiment
                constraint_funcs = constraints_dict[log_name].get(experiment, [])
            else:
                # Get all constraints from all experiments
                constraint_funcs = []
                for exp_constraints in constraints_dict[log_name].values():
                    constraint_funcs.extend(exp_constraints)
            
            # When constraints are uncommented in the restructured file,
            # they're already NFAs (function calls return NFAs directly)
            # When commented, they're not in the list at all
            if constraint_funcs:
                return constraint_funcs
    except (ImportError, AttributeError, Exception):
        # Restructured file doesn't exist or error occurred, fall back to original
        pass
    
    # Fallback: Get all constraints from original format
    all_constraints = get_log_constraints(log_name, alphabet)
    
    # If experiment is not specified, return all active constraints
    if experiment is None:
        return all_constraints
    
    # For experiment-based selection in original format, we can't easily parse by experiment
    # Return all active constraints (user should use restructured format for experiment selection)
    return all_constraints


def _normalize_template_name(template_name: str) -> str:
    """Normalize Declare template labels so different naming styles map consistently."""
    return ''.join(ch for ch in template_name.lower() if ch.isalnum())


def _declare_template_to_nfa_list(template_name: str, rule_key: Any, alphabet: list) -> List[NFA]:
    """
    Convert one PM4Py Declare rule into one or more NFAs supported by this project.
    Returns an empty list if the template is unsupported or the involved activities are out of alphabet.
    """
    template = _normalize_template_name(template_name)
    alphabet_set = set(alphabet)

    def _valid_activity(activity: str) -> bool:
        return activity in alphabet_set

    # Unary templates
    if isinstance(rule_key, str):
        if not _valid_activity(rule_key):
            return []
        if template == 'existence':
            return [existence_constraint(rule_key, alphabet)]
        if template == 'absence':
            return [absence_constraint(rule_key, alphabet)]
        if template == 'init':
            return [init_constraint(rule_key, alphabet)]
        if template in {'exactlyone', 'existenceexactlyonce'}:
            return [existence_exactly_once_constraint(rule_key, alphabet)]
        return []

    # Binary templates
    if not isinstance(rule_key, tuple) or len(rule_key) != 2:
        return []
    event1, event2 = rule_key
    if not (_valid_activity(event1) and _valid_activity(event2)):
        return []

    if template == 'respondedexistence':
        return [responded_existence_constraint(event1, event2, alphabet)]
    if template == 'response':
        return [response_constraint(event1, event2, alphabet)]
    if template == 'alternateresponse':
        return [alternate_response_constraint(event1, event2, alphabet)]
    if template in {'chainresponse', 'chainresponce'}:
        return [chain_response_constraint(event1, event2, alphabet)]
    if template == 'precedence':
        return [precedence_constraint(event1, event2, alphabet)]
    if template == 'alternateprecedence':
        return [alternate_precedence_constraint(event1, event2, alphabet)]
    if template == 'chainprecedence':
        return [chain_precedence_constraint(event1, event2, alphabet)]
    if template == 'coexistence':
        return [co_existence_constraint(event1, event2, alphabet)]
    if template in {'noncoexistence', 'notcoexistence'}:
        return [not_co_existence_constraint(event1, event2, alphabet)]
    if template == 'choice':
        return [choice_constraint(event1, event2, alphabet)]
    if template in {'exclusivechoice', 'xorchoice'}:
        return [exclusive_choice_constraint(event1, event2, alphabet)]
    if template == 'succession':
        # Succession(A, B) = Response(A, B) AND Precedence(A, B)
        return [
            response_constraint(event1, event2, alphabet),
            precedence_constraint(event1, event2, alphabet),
        ]
    if template == 'alternatesuccession':
        return [
            alternate_response_constraint(event1, event2, alphabet),
            alternate_precedence_constraint(event1, event2, alphabet),
        ]
    if template == 'chainsuccession':
        return [
            chain_response_constraint(event1, event2, alphabet),
            chain_precedence_constraint(event1, event2, alphabet),
        ]

    return []


def _to_jsonable_rule_key(rule_key: Any) -> Any:
    """Convert rule key to a JSON-serializable structure for deterministic cache IDs."""
    if isinstance(rule_key, tuple):
        return list(rule_key)
    return rule_key


def _compute_interest_factor(
    rule_key: Any,
    support: int,
    confidence: int,
    existence_prob_map: Dict[str, float],
) -> float:
    """Interest factor used for ranking/filtering mined constraints."""
    if not support:
        return 0.0
    p_rule = confidence / support
    if isinstance(rule_key, tuple) and len(rule_key) == 2:
        consequent = rule_key[1]
        p_consequent = existence_prob_map.get(consequent)
        if p_consequent and p_consequent > 0:
            return p_rule / p_consequent
    return p_rule


def _compute_cpir(
    rule_key: Any,
    support: int,
    confidence: int,
    existence_prob_map: Dict[str, float],
) -> float:
    """
    CPIR = (P(B|A) - P(B)) / (P(B) * (1 - P(B))) for binary rules A->B.
    Returns 0.0 for unary rules or degenerate denominators.
    """
    if not isinstance(rule_key, tuple) or len(rule_key) != 2 or not support:
        return 0.0
    p_b_given_a = confidence / support
    p_b = existence_prob_map.get(rule_key[1], 0.0)
    denom = p_b * (1.0 - p_b)
    if denom <= 0:
        return 0.0
    return (p_b_given_a - p_b) / denom


def _discover_nfa_constraints_from_log(
    log,
    alphabet: list,
    max_constraints: Optional[int] = None,
    log_name: str = "",
) -> Tuple[Optional[NFA], int]:
    """
    Discover Declare rules from the input log using PM4Py and convert them to NFAs.
    Uses form_rules_table when DECLARE_USE_FORM_RULES_TABLE=1 to match percentage_declare_traces.
    Applies all top-k rules (by rule count, not component count).
    """
    min_support_ratio = float(os.getenv("DECLARE_MIN_SUPPORT_RATIO", "0.0"))
    min_confidence_ratio = float(os.getenv("DECLARE_MIN_CONFIDENCE_RATIO", "0.0"))
    ranking_mode = _resolve_constraint_ranking_mode()
    use_form_rules = os.getenv("DECLARE_USE_FORM_RULES_TABLE", "0").strip() == "1"

    ranked_rules: List[Tuple[float, int, int, float, float, str, Any]] = []
    n_traces = len(log) if log is not None else 0

    if use_form_rules:
        # Same discovery as percentage_declare_traces.py for identical constraint set/order.
        params: Dict[Any, Any] = {
            declare_classic.Parameters.ACTIVITY_KEY: "concept:name",
        }
        discovery_start = time.perf_counter()
        rules_df = declare_classic.form_rules_table(log, parameters=params)
        discovery_elapsed = time.perf_counter() - discovery_start
        print(
            f"[PROFILE] form_rules_table: {discovery_elapsed:.2f}s "
            f"(log_name={log_name}, traces={n_traces})"
        )
        for col_name in rules_df.columns:
            col = rules_df[col_name]
            support_count = int((col != 0).sum())
            confidence_count = int((col == 1).sum())
            satisfied_ratio_total = (
                (float(confidence_count) / float(n_traces)) if n_traces > 0 else 0.0
            )
            if support_count == 0:
                continue
            template_name, rule_key = declare_classic.__col_to_dict_rule(col_name)
            ranked_rules.append(
                (satisfied_ratio_total, confidence_count, support_count, 0.0, 0.0, template_name, rule_key)
            )
    else:
        params = {
            declare_classic.Parameters.ACTIVITY_KEY: "concept:name",
            declare_classic.Parameters.MIN_SUPPORT_RATIO: min_support_ratio,
            declare_classic.Parameters.MIN_CONFIDENCE_RATIO: min_confidence_ratio,
        }
        discovery_start = time.perf_counter()
        discovered_model = declare_discovery.apply(log, parameters=params)
        discovery_elapsed = time.perf_counter() - discovery_start
        print(
            f"[PROFILE] declare_discovery.apply: {discovery_elapsed:.2f}s "
            f"(log_name={log_name}, traces={n_traces})"
        )
        existence_prob_map: Dict[str, float] = {}
        for event_name, metrics in discovered_model.get("existence", {}).items():
            sup = int(metrics.get("support", 0))
            conf = int(metrics.get("confidence", 0))
            existence_prob_map[event_name] = (conf / sup) if sup else 0.0

        for template_name, rules in discovered_model.items():
            for rule_key, metrics in rules.items():
                confidence = int(metrics.get("confidence", 0))
                support = int(metrics.get("support", 0))
                satisfied_ratio_total = (
                    (float(confidence) / float(n_traces)) if n_traces > 0 else 0.0
                )
                interest_factor = _compute_interest_factor(
                    rule_key, support, confidence, existence_prob_map
                )
                cpir = _compute_cpir(rule_key, support, confidence, existence_prob_map)
                ranked_rules.append(
                    (
                        satisfied_ratio_total,
                        confidence,
                        support,
                        interest_factor,
                        cpir,
                        template_name,
                        rule_key,
                    )
                )

    support_filter_mode = os.getenv("DECLARE_SUPPORT_FILTER_MODE", "all").lower().strip()

    # Keep a copy of all mined candidates before filtering for reporting.
    all_candidate_rules = list(ranked_rules)

    # No threshold-based pre-filtering: keep all mined candidates for ranking.
    post_prefilter_rules = list(ranked_rules)

    if ranking_mode == "support_confidence":
        # Deterministic ranking by support, then confidence.
        ranked_rules.sort(key=lambda x: (x[2], x[1], x[0], x[3], x[4]), reverse=True)
    else:
        # Deterministic ranking by satisfied/total ratio, then confidence and support.
        ranked_rules.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]), reverse=True)

    # Subset selection is disabled; keep the full prefiltered set.
    if support_filter_mode != "all":
        print(
            f"Support filter mode '{support_filter_mode}' requested, "
            "but subset selection is disabled. Using full prefiltered set."
        )

    # Keep a copy of the candidate set before random simulation-level sampling.
    post_quantile_rules = list(ranked_rules)

    # Deterministic top-N selection (no random sampling).
    sample_size = int(os.getenv("DECLARE_SAMPLE_SIZE", "0"))
    sample_seed = os.getenv("DECLARE_SAMPLE_SEED", "").strip()
    max_component_constraints = int(os.getenv("DECLARE_MAX_AUTOMATA_COMPONENTS", "5"))
    profile_intersections = os.getenv("DECLARE_PROFILE_INTERSECTIONS", "1").strip() == "1"
    max_product_states = int(os.getenv("DECLARE_MAX_PRODUCT_STATES", "5000000"))
    device = os.getenv("DECLARE_INTERSECTION_DEVICE", "cpu").strip().lower()
    if device == "gpu":
        # automata-lib intersection is CPU-bound; keep explicit message to avoid silent assumptions.
        print(
            "[Intersection backend] GPU requested via DECLARE_INTERSECTION_DEVICE=gpu, "
            "but automata-lib NFA intersection runs on CPU. Using CPU with guardrails/profiling."
        )
    if sample_size > 0 and ranked_rules:
        total_candidates = len(ranked_rules)
        actual_size = min(sample_size, total_candidates)
        ranked_rules = ranked_rules[:actual_size]
        ranking_label = (
            "support/confidence"
            if ranking_mode == "support_confidence"
            else "satisfied_ratio_total_traces"
        )
        print(
            f"Selected top {len(ranked_rules)} constraints by {ranking_label} "
            f"(requested={sample_size}, available={total_candidates})."
        )
    sampled_rules = list(ranked_rules)

    # Cache progressive intersections so future runs can resume without recomputing all steps.
    cache_root_default = Path(__file__).resolve().parents[1] / "cache" / "partial_intersections"
    cache_root = Path(os.getenv("DECLARE_AUTOMATA_CACHE_DIR", str(cache_root_default)))
    cache_root.mkdir(parents=True, exist_ok=True)

    cache_payload = {
        "log_name": log_name,
        "alphabet": sorted(map(str, alphabet)),
        "max_constraints": max_constraints,
        "ranking_mode": ranking_mode,
        "support_filter_mode": support_filter_mode,
        "min_support_ratio": min_support_ratio,
        "min_confidence_ratio": min_confidence_ratio,
        "sample_size": sample_size,
        "sample_seed": sample_seed,
        "max_component_constraints": max_component_constraints,
        "ranked_rules": [
            {
                "satisfied_ratio_total_traces": float(satisfied_ratio_total),
                "confidence": int(confidence),
                "support": int(support),
                "interest_factor": float(interest_factor),
                "cpir": float(cpir),
                "template": str(template_name),
                "rule_key": _to_jsonable_rule_key(rule_key),
            }
            for (
                satisfied_ratio_total,
                confidence,
                support,
                interest_factor,
                cpir,
                template_name,
                rule_key,
            ) in ranked_rules
        ],
    }
    cache_id = hashlib.sha256(
        json.dumps(cache_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    cache_dir = cache_root / cache_id
    cache_dir.mkdir(parents=True, exist_ok=True)

    def _rules_to_df(rules: List[Tuple[float, int, int, float, float, str, Any]]) -> pd.DataFrame:
        rows = []
        for (
            satisfied_ratio_total,
            confidence,
            support,
            interest_factor,
            cpir,
            template_name,
            rule_key,
        ) in rules:
            rows.append(
                {
                    "template": str(template_name),
                    "rule_key": json.dumps(_to_jsonable_rule_key(rule_key), ensure_ascii=True),
                    "satisfied_ratio_total_traces": float(satisfied_ratio_total),
                    "support_count": int(support),
                    "confidence_count": int(confidence),
                    "support_ratio": (float(support) / float(n_traces)) if n_traces > 0 else 0.0,
                    "confidence_ratio": (float(confidence) / float(support)) if support > 0 else 0.0,
                    "interest_factor": float(interest_factor),
                    "cpir": float(cpir),
                }
            )
        return pd.DataFrame(rows)

    # Save full mined stats, post-threshold stats, subset stats, and sampled stats.
    all_candidates_csv = cache_dir / "constraints_all_candidates_stats.csv"
    post_prefilter_csv = cache_dir / "constraints_post_prefilter_stats.csv"
    post_quantile_csv = cache_dir / "constraints_post_quantile_stats.csv"
    sampled_csv = cache_dir / "constraints_sampled_stats.csv"
    _rules_to_df(all_candidate_rules).to_csv(all_candidates_csv, index=False)
    _rules_to_df(post_prefilter_rules).to_csv(post_prefilter_csv, index=False)
    _rules_to_df(post_quantile_rules).to_csv(post_quantile_csv, index=False)
    _rules_to_df(sampled_rules).to_csv(sampled_csv, index=False)
    profile_rows: List[Dict[str, Any]] = []

    cumulative_nfa: Optional[NFA] = None
    applied_constraints = 0
    start_rule_idx = 0
    applied_rule_records: List[Dict[str, Any]] = []

    # Load most advanced cached partial intersection, if available.
    for idx in range(len(ranked_rules) - 1, -1, -1):
        step_file = cache_dir / f"rule_{idx}.pkl"
        if step_file.exists():
            with open(step_file, "rb") as fh:
                cached = pickle.load(fh)
            cumulative_nfa = cached.get("nfa")
            applied_constraints = int(cached.get("applied_constraints", 0))
            applied_rule_records = cached.get("applied_rule_records", [])
            start_rule_idx = idx + 1
            print(
                f"Loaded cached partial intersection at rule {idx + 1}/{len(ranked_rules)} "
                f"(applied constraints: {applied_constraints})."
            )
            break

    # Limit by RULES (not components) to match percentage_declare_traces: apply all top sample_size rules.
    rules_applied = 0
    for rule_idx in tqdm(
        range(start_rule_idx, len(ranked_rules)),
        desc="Selecting mined constraints",
        unit="rule",
        dynamic_ncols=True,
    ):
        if sample_size > 0 and rules_applied >= sample_size:
            break
        (
            satisfied_ratio_total,
            confidence,
            support,
            interest_factor,
            cpir,
            template_name,
            rule_key,
        ) = ranked_rules[rule_idx]
        candidate_nfas = _declare_template_to_nfa_list(template_name, rule_key, alphabet)
        for component_idx, candidate_nfa in enumerate(candidate_nfas):
            cum_states_before, cum_trans_before = _nfa_size_stats(cumulative_nfa)
            cand_states, cand_trans = _nfa_size_stats(candidate_nfa)
            if cumulative_nfa is None:
                projected_product_states = cand_states
            else:
                projected_product_states = cum_states_before * cand_states

            if (
                max_product_states > 0
                and projected_product_states > max_product_states
            ):
                profile_rows.append(
                    {
                        "rule_index": int(rule_idx),
                        "template": str(template_name),
                        "component_index": int(component_idx),
                        "candidate_states": int(cand_states),
                        "candidate_transitions": int(cand_trans),
                        "cumulative_states_before": int(cum_states_before),
                        "cumulative_transitions_before": int(cum_trans_before),
                        "projected_product_states": int(projected_product_states),
                        "intersection_time_sec": 0.0,
                        "cumulative_states_after": int(cum_states_before),
                        "cumulative_transitions_after": int(cum_trans_before),
                        "accepted": 0,
                        "skip_reason": "projected_product_states_cap",
                        "rss_gb": _current_rss_gb(),
                    }
                )
                continue

            start_t = time.perf_counter()
            tentative_nfa = (
                candidate_nfa if cumulative_nfa is None else cumulative_nfa.intersection(candidate_nfa)
            )
            elapsed = time.perf_counter() - start_t
            out_states, out_trans = _nfa_size_stats(tentative_nfa)
            # Always apply constraint (no skipping), matching percentage_declare_traces.py.
            # If language becomes empty, callers will raise.
            cumulative_nfa = tentative_nfa
            applied_constraints += 1
            profile_rows.append(
                {
                    "rule_index": int(rule_idx),
                    "template": str(template_name),
                    "component_index": int(component_idx),
                    "candidate_states": int(cand_states),
                    "candidate_transitions": int(cand_trans),
                    "cumulative_states_before": int(cum_states_before),
                    "cumulative_transitions_before": int(cum_trans_before),
                    "projected_product_states": int(projected_product_states),
                    "intersection_time_sec": float(elapsed),
                    "cumulative_states_after": int(out_states),
                    "cumulative_transitions_after": int(out_trans),
                    "accepted": 1,
                    "skip_reason": "",
                    "rss_gb": _current_rss_gb(),
                }
            )
            applied_rule_records.append(
                {
                    "template": str(template_name),
                    "rule_key": json.dumps(_to_jsonable_rule_key(rule_key), ensure_ascii=True),
                    "satisfied_ratio_total_traces": float(satisfied_ratio_total),
                    "support_count": int(support),
                    "confidence_count": int(confidence),
                    "support_ratio": (float(support) / float(n_traces)) if n_traces > 0 else 0.0,
                    "confidence_ratio": (float(confidence) / float(support)) if support > 0 else 0.0,
                    "interest_factor": float(interest_factor),
                    "cpir": float(cpir),
                    "component_index": int(component_idx),
                    "component_total": int(len(candidate_nfas)),
                    "applied_order": int(applied_constraints),
                }
            )
            if max_constraints is not None and max_constraints > 0 and applied_constraints >= max_constraints:
                break

        rules_applied += 1

        step_file = cache_dir / f"rule_{rule_idx}.pkl"
        with open(step_file, "wb") as fh:
            pickle.dump(
                {
                    "nfa": cumulative_nfa,
                    "applied_constraints": applied_constraints,
                    "applied_rule_records": applied_rule_records,
                },
                fh,
            )

        if max_constraints is not None and max_constraints > 0 and applied_constraints >= max_constraints:
            break

    # Save a stable final artifact for this split/configuration.
    if cumulative_nfa is not None:
        if profile_intersections and profile_rows:
            pd.DataFrame(profile_rows).to_csv(cache_dir / "intersection_profile.csv", index=False)
        applied_csv = cache_dir / "constraints_applied_stats.csv"
        pd.DataFrame(applied_rule_records).to_csv(applied_csv, index=False)
        final_file = cache_dir / "final_intersection.pkl"
        with open(final_file, "wb") as fh:
            pickle.dump(
                {
                    "nfa": cumulative_nfa,
                    "applied_constraints": applied_constraints,
                    "applied_rule_records": applied_rule_records,
                },
                fh,
            )
        metadata = {
            "log_name": log_name,
            "ranking_mode": ranking_mode,
            "support_filter_mode": support_filter_mode,
            "min_support_ratio": min_support_ratio,
            "min_confidence_ratio": min_confidence_ratio,
            "max_constraints": max_constraints,
            "max_component_constraints": max_component_constraints,
            "max_product_states": max_product_states,
            "intersection_device": device,
            "profile_intersections": profile_intersections,
            "declare_discovery_time_sec": float(discovery_elapsed),
            "constraints_whole_count": len(all_candidate_rules),
            "constraints_post_prefilter_count": len(post_prefilter_rules),
            "ranked_rules_count": len(ranked_rules),
            "constraints_post_quantile_count": len(post_quantile_rules),
            "constraints_sampled_count": len(sampled_rules),
            "applied_constraints": applied_constraints,
            "cache_id": cache_id,
            "final_intersection_file": str(final_file),
            "constraints_all_candidates_stats": str(all_candidates_csv),
            "constraints_post_prefilter_stats": str(post_prefilter_csv),
            "constraints_post_quantile_stats": str(post_quantile_csv),
            "constraints_sampled_stats": str(sampled_csv),
            "constraints_applied_stats": str(applied_csv),
        }
        with open(cache_dir / "metadata.json", "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2)
    elif profile_intersections and profile_rows:
        pd.DataFrame(profile_rows).to_csv(cache_dir / "intersection_profile.csv", index=False)

    return cumulative_nfa, applied_constraints


def _sample_constraint_nfas(
    constraints_nfa_list: List[NFA],
    sample_size: int,
    sample_seed: str,
) -> List[NFA]:
    """Sample a subset of static/fallback constraints before intersection."""
    if sample_size <= 0 or not constraints_nfa_list:
        return constraints_nfa_list
    total = len(constraints_nfa_list)
    actual_size = min(sample_size, total)
    rng = random.Random(sample_seed if sample_seed else None)
    sampled_idx = sorted(rng.sample(range(total), k=actual_size))
    sampled = [constraints_nfa_list[i] for i in sampled_idx]
    print(
        f"Sampling fallback constraints: {len(sampled)} selected "
        f"(requested={sample_size}, available={total})"
        + (f", seed={sample_seed}" if sample_seed else "")
        + "."
    )
    return sampled


def create_nfa_constraints(
    log_name: str,
    alphabet: list,
    experiment: str = None,
    log=None,
) -> NFA:
    """
    Create NFA from constraints for a case study, optionally filtered by experiment.
    
    Args:
        log_name: Name of the case study
        alphabet: List of activities  
        experiment: Optional experiment identifier (exp1, exp2, exp3, exp4)
    
    Returns:
        NFA representing the intersection of all constraints
    """
    constraints_nfa_list: List[NFA] = []
    sample_size = int(os.getenv("DECLARE_SAMPLE_SIZE", "0"))
    sample_seed = os.getenv("DECLARE_SAMPLE_SEED", "").strip()
    max_component_constraints = int(os.getenv("DECLARE_MAX_AUTOMATA_COMPONENTS", "5"))
    max_product_states = int(os.getenv("DECLARE_MAX_PRODUCT_STATES", "5000000"))

    # Preferred path: derive constraints from PM4Py Declare mining on the provided log.
    if log is not None:
        try:
            max_constraints = int(os.getenv("DECLARE_MAX_CONSTRAINTS", "0"))
            mined_nfa, applied_constraints = _discover_nfa_constraints_from_log(
                log,
                alphabet,
                max_constraints=max_constraints if max_constraints > 0 else None,
                log_name=log_name,
            )
            if mined_nfa is not None:
                print(f"Using {applied_constraints} PM4Py-discovered Declare constraints.")
                return mined_nfa
        except Exception as exc:
            print(f"PM4Py Declare discovery failed ({exc}). Falling back to configured constraints.")

    # Fallback path: static constraints by case study / experiment.
    if not constraints_nfa_list:
        constraints_nfa_list = get_log_constraints_by_experiment(log_name, alphabet, experiment)
        constraints_nfa_list = _sample_constraint_nfas(
            constraints_nfa_list, sample_size=sample_size, sample_seed=sample_seed
        )
        if max_component_constraints > 0:
            constraints_nfa_list = constraints_nfa_list[:max_component_constraints]

    if not constraints_nfa_list:
        raise ValueError(
            f"No constraints found for {log_name}" + 
            (f" experiment {experiment}" if experiment else "") +
            ". PM4Py Declare discovery returned no usable constraints and static constraints are unavailable."
        )

    nfa_constraints = constraints_nfa_list[0]
    for next_nfa in constraints_nfa_list[1:]:
        left_states, _ = _nfa_size_stats(nfa_constraints)
        right_states, _ = _nfa_size_stats(next_nfa)
        projected = left_states * right_states
        if max_product_states > 0 and projected > max_product_states:
            raise ValueError(
                "Projected fallback-constraint product is too large "
                f"({projected} > {max_product_states}); skipping to avoid OOM."
            )
        nfa_constraints = nfa_constraints.intersection(next_nfa)
    
    return nfa_constraints