import pandas as pd
import numpy as np
import tqdm

import warnings
warnings.filterwarnings('ignore')

def append_row(df, row):
    return pd.concat([
                df, 
                pd.DataFrame([row], columns=row.index)]
           ).reset_index(drop=True)


def from_lifecycles_to_start_end(trace):

    # Create a new trace without the lifecycle:transitions and with two new columns: START and END
    new_trace = pd.DataFrame(columns=trace.columns)
    del new_trace['lifecycle:transition']
    del new_trace['time:timestamp']
    new_trace['start:timestamp'], new_trace['time:timestamp'] = np.zeros(len(new_trace)), np.zeros(len(new_trace))

    #Get the index of the lifecycle:transition and the time:timestamp column
    lifecycle_index, time_index = trace.columns.get_loc('lifecycle:transition'), trace.columns.get_loc('time:timestamp')

    acts = trace['concept:name'].values
    lines_to_skip = []
    for line in range(len(trace)):
        # print(lines_to_skip)
        if line in lines_to_skip:
            # print(f'{line} skipped')
            continue
        act = acts[line]
        lifecycle = trace.iloc[line]['lifecycle:transition']
        
        if lifecycle == 'complete':
            vec = trace.iloc[line].values.tolist()
            el = vec.pop(time_index)
            if time_index < lifecycle_index:
                el = vec.pop(lifecycle_index - 1)
            else:
                el = vec.pop(lifecycle_index)
            vec_to_append = pd.Series(vec+ [trace.iloc[line]['time:timestamp']] + [trace.iloc[line]['time:timestamp']], index=new_trace.columns)
            new_trace = append_row(new_trace, vec_to_append)

        elif lifecycle == 'start':
            end = None
            if 'complete' not in trace['lifecycle:transition'].values:
                vec = trace.iloc[line].values.tolist()
                el = vec.pop(time_index)
                if time_index < lifecycle_index:
                    el = vec.pop(lifecycle_index - 1)
                else:
                    el = vec.pop(lifecycle_index)
                vec_to_append = pd.Series(vec+ [trace.iloc[line]['time:timestamp']] + [trace.iloc[line]['time:timestamp']], index=new_trace.columns)
                new_trace = append_row(new_trace, vec_to_append)
                continue
            
            #Search for the next complete activity
            for next_line in range(line+1, len(trace)):
                if acts[next_line] == act and trace.iloc[next_line]['lifecycle:transition'] == 'complete':
                    end = next_line
                    res_end = trace.iloc[end]['org:resource']
                    lines_to_skip.append(end)
                    break

            if end is None:
                vec = trace.iloc[line]
                # vec['org:resource'] = trace.iloc[line]['org:resource']
                vec = vec.values.tolist()
                el = vec.pop(time_index)
                if time_index < lifecycle_index:
                    el = vec.pop(lifecycle_index - 1)
                else:
                    el = vec.pop(lifecycle_index)
                vec_to_append = pd.Series(vec+ [trace.iloc[line]['time:timestamp']] + [trace.iloc[line]['time:timestamp']], index=new_trace.columns)
                new_trace = append_row(new_trace, vec_to_append)

            else:
                vec = trace.iloc[line]#.values.tolist()
                vec['org:resource'] = res_end
                vec = vec.values.tolist()
                el = vec.pop(time_index)
                if time_index < lifecycle_index:
                    el = vec.pop(lifecycle_index - 1)
                else:
                    el = vec.pop(lifecycle_index)

                vec_to_append = pd.Series(vec+ [trace.iloc[line]['time:timestamp']] + [trace.iloc[end]['time:timestamp']], index=new_trace.columns)
                new_trace = append_row(new_trace, vec_to_append)
                
    return new_trace

def lenght_distribution(log):
    from collections import Counter
    lens = []
    for trace_id in log['case:concept:name'].unique():
        trace = log[log['case:concept:name'] == trace_id]
        lens.append(len(trace))
    print(f'The distribution of the length of the traces is: {Counter(lens)}')

def convert_log(log):

    #Filter the log in just start and complete lifecycle transitions
    log = log[log['lifecycle:transition'].isin(['start', 'complete'])]

    ret_log = pd.DataFrame(columns=log.columns)
    del ret_log['lifecycle:transition']
    del ret_log['time:timestamp']
    ret_log['start:timestamp'], ret_log['time:timestamp'] = np.zeros(len(ret_log)), np.zeros(len(ret_log))

    for trace_id in tqdm.tqdm(log['case:concept:name'].unique()):
        log_trace = log[log['case:concept:name'] == trace_id]
        ret_log = pd.concat([ret_log, from_lifecycles_to_start_end(log_trace)])

    return ret_log


def order_for_trace_start(log):

    # For each trace id, get the first timestamp
    first_timestamps = []
    for trace_id in log['case:concept:name'].unique():
        trace = log[log['case:concept:name'] == trace_id]
        first_timestamps.append((trace_id, trace['time:timestamp'].min()))
    
    # Sort the log by the first timestamp
    first_timestamps = sorted(first_timestamps, key=lambda x: x[1])

    # sort the log by trace if following first timestamp order
    log = log[log['case:concept:name'].isin([x[0] for x in first_timestamps])]
    
    return log