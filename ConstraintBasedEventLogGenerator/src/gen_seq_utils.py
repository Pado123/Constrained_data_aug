import pm4py

def get_prefix_freq(log, k=0):
    """

    Returns a dictionary: {'prefix': {'actitivity': frequency of 'activity' after 'prefix'}}

    """

    activities = pm4py.get_event_attribute_values(log, "concept:name").keys()
    prefixes_freq_next_act = dict()
    for trace in log:
        prefix = tuple()
        for event in trace:
            act = event['concept:name']
            if prefix in prefixes_freq_next_act.keys():
                prefixes_freq_next_act[prefix][act] += 1
            else:
                prefixes_freq_next_act[prefix] = {a: 0 for a in activities} | {'<END>': 0}
                prefixes_freq_next_act[prefix][act] += 1
            prefix = prefix + (act,)
            prefix = prefix[-k:]
        if prefix in prefixes_freq_next_act.keys():
            prefixes_freq_next_act[prefix]['<END>'] += 1
        else:
            prefixes_freq_next_act[prefix] = {a: 0 for a in activities} | {'<END>': 1}

    return prefixes_freq_next_act


def get_prefix_proba(log, k = 0):
    """
    
    Returns a dictionary: {'prefix': {'actitivity': probability to execute 'activity' after 'prefix'}}

    """
    
    print(f'Building transition system of the log with k={k}...')
    prefixes_freq_next_act = get_prefix_freq(log, k=k)
    prefixes = prefixes_freq_next_act.keys()
    prefixes_proba_next_act = prefixes_freq_next_act.copy()
    for prefix in prefixes:
        N_freq = sum(prefixes_freq_next_act[prefix].values())
        for act in prefixes_proba_next_act[prefix].keys():
            prefixes_proba_next_act[prefix][act] /= N_freq

    return prefixes_proba_next_act
