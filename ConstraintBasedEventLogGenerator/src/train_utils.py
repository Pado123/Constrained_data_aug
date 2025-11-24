import pm4py
import numpy as np
import pandas as pd

def splitEventLog(log, train_size=0.7, split_temporal=True, save_to=''):
    """
    Split event log in train and test set
    """

    df_real = pm4py.convert_to_dataframe(log)
    df_real['time:timestamp'] = pd.to_datetime(df_real['time:timestamp'])

    grouped = df_real.groupby('case:concept:name', sort=False)

    trace_dict = {case: trace_df for case, trace_df in grouped}

    if split_temporal:
        sorted_case_ids = sorted(trace_dict.keys(), key=lambda cid: trace_dict[cid]['time:timestamp'].min())
    else:
        np.random.seed(72)
        sorted_case_ids = list(trace_dict.keys())
        np.random.shuffle(sorted_case_ids)

    n_train = int(train_size * len(sorted_case_ids))
    train_case_ids = sorted_case_ids[:n_train]
    test_case_ids = sorted_case_ids[n_train:]

    df_train = pd.concat([trace_dict[cid] for cid in train_case_ids], ignore_index=True)
    df_test = pd.concat([trace_dict[cid] for cid in test_case_ids], ignore_index=True)

    real_train = pm4py.convert_to_event_log(df_train)
    real_test = pm4py.convert_to_event_log(df_test)

    if save_to:
        pm4py.write_xes(real_train, save_to + '/logTrain.xes')
        pm4py.write_xes(real_test, save_to + '/logTest.xes')

    return real_train, real_test
