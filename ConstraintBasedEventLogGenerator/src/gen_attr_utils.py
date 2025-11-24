import pm4py
import random

def get_prefix_attr_freq(log, data_attr_labels, k = 0):

    prefixes_freq_next_attr = dict()
    for trace in log:
        prefix = tuple()
        for event in trace:
            act = event['concept:name']
            attr = []
            for l in data_attr_labels:
                attr.append(event[l])
            attr = tuple(attr)
            pref_act = (prefix, act)
            if pref_act in prefixes_freq_next_attr.keys():
                if attr in prefixes_freq_next_attr[pref_act].keys():
                    prefixes_freq_next_attr[pref_act][attr] += 1
                else:
                    prefixes_freq_next_attr[pref_act][attr] = 1
            else:
                prefixes_freq_next_attr[pref_act] = {attr: 1}
            prefix = prefix + ((act, attr),)
            prefix = prefix[-k:]

    return prefixes_freq_next_attr


def get_prefix_attr_proba(log, data_attr_labels, k = 0):
    """
    
    Returns a dictionary: {'prefix': {'attr': probability to execute 'attr' after 'prefix'}}
    'prefix' is a list of (act, attr)

    """

    prefixes_freq_next_attr = get_prefix_attr_freq(log, data_attr_labels, k)
    prefixes_act = prefixes_freq_next_attr.keys()
    prefixes_proba_next_attr = prefixes_freq_next_attr.copy()
    for prefix_act in prefixes_act:
        N_freq = sum(prefixes_freq_next_attr[prefix_act].values())
        for attr in prefixes_proba_next_attr[prefix_act].keys():
            prefixes_proba_next_attr[prefix_act][attr] /= N_freq

    return prefixes_proba_next_attr


def get_possible_prefixes_attr_act(prefixes_proba_next_attr):

    possible_prefixes_act = list(prefixes_proba_next_attr.keys())
    possible_prefixes = dict()
    for p in possible_prefixes_act:
        cur_act = p[1]
        pref = p[0]
        if cur_act in possible_prefixes.keys():
            possible_prefixes[cur_act].append(pref)
        else:
            possible_prefixes[cur_act] = [pref]

    return possible_prefixes


def get_trace_attribute_labels(log, data_attr_labels):

    trace_attributes = []
    df_log = pm4py.convert_to_dataframe(log)

    for a in data_attr_labels:
        if df_log[a].dtype == float:
            if df_log[["case:concept:name"]+data_attr_labels].groupby("case:concept:name")[a].std().mean() == 0:
                trace_attributes.append(a)
        else:
            if df_log[["case:concept:name"]+data_attr_labels].groupby("case:concept:name")[a].unique().apply(lambda x: len(x)).mean() == 1:
                trace_attributes.append(a)

    return trace_attributes


def get_trace_attribute_proba(log, trace_attribute_labels):
    
    trace_attribute_proba = dict()

    for trace in log:
        for l in trace_attribute_labels:
            attr = tuple(trace[0][l] for l in trace_attribute_labels) 
            if attr not in trace_attribute_proba.keys():
                trace_attribute_proba[attr] = 1
            else:
                trace_attribute_proba[attr] += 1

    return trace_attribute_proba