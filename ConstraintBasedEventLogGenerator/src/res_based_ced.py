import pandas as pd
import numpy as np
from log_distance_measures.circadian_event_distribution import circadian_event_distribution_distance

def resource_based_circadian_event_distribution_distance(
    log_real, event_log_ids,  # First event log and its column id mappings
    log_sim, event_log_ids2,  # Second event log and its column id mappings
    discretize_type  # Consider both start/end timestamps of each activity instance
    ):

    distances = []

    try:
        for res in log_real['org:resource'].unique():
            real_log_r = log_real[log_real['org:resource'] == res]
            sim_log_r = log_sim[log_sim['org:resource'] == res]
            distance = circadian_event_distribution_distance(real_log_r, event_log_ids, sim_log_r, event_log_ids2, discretize_type)
            distances.append(distance)

        return np.mean(distances)
    except:
        return np.nan