import pm4py
import pandas as pd
import numpy as np
from pm4py.objects.log.importer.xes import importer as xes_importer

def add_lc_to_act(log):
    
    for i in range(len(log)):
        for j in range(len(log[i])):
            log[i][j]['concept:name'] = log[i][j]['concept:name'] + '_lc:' + str.lower(log[i][j]['lifecycle:transition'])

    return log


def add_start_end_times(log_path):

    # Check if the log is .xes file
    if log_path[-4:] == ".xes":
        xes_log = xes_importer.apply(log_path)
        log_df = pm4py.convert_to_dataframe(xes_log)

    else:
        log_df = pd.read_csv(log_path)

    # If there is only one type of lifecycle:transition in the log, or no lifeclcle:transition column, return the log
    if "lifecycle:transition" not in log_df.columns:
        return log_df  
    
    if len(log_df["lifecycle:transition"].unique()) == 1:

        # Only keep times, resources, activity and case ids
        log_df = log_df[["time:timestamp", "concept:name", "org:resource", "case:concept:name"]]

        return log_df

    # Filter in two sublogs for start and complete timestamps
    start_log = log_df[log_df["lifecycle:transition"] == "start"]
    complete_log = log_df[log_df["lifecycle:transition"] == "complete"]

    # sort them for timestamp and activity (to handle cases with same timestamp) and then concatenate them
    start_log = start_log.sort_values(by=["time:timestamp", "concept:name"]).reset_index(drop=True)
    complete_log = complete_log.sort_values(by=["time:timestamp", "concept:name"]).reset_index(drop=True)

    #Remove the lifecycle:transition columns
    start_log = start_log.drop(columns=["lifecycle:transition"])
    complete_log = complete_log.drop(columns=["lifecycle:transition"])

    # Rename the timestamp columns in start_timestamp and complete_timestamp
    start_log = start_log.rename(columns={"time:timestamp": "start:timestamp"})
    complete_log = complete_log.rename(columns={"time:timestamp": "end:timestamp"})

    #Remove the case:concept:name columns from a log
    start_log = start_log.drop(columns=["case:concept:name"])
    
    # Concatenate the two logs to have a start-complete pair
    log_df = pd.concat([start_log, complete_log], axis=1)

    # Remove the columns that have the same name in the two logs
    log_df = log_df[["case:concept:name", "start:timestamp", "end:timestamp", 'concept:name','org:resource']]

    # Check the column names that are repeated
    repeated_columns = [col for col in log_df.columns if sum(log_df.columns == col) > 1]

    # Keep just one the repeated columns
    log_df = log_df.loc[:, ~log_df.columns.duplicated()]

    # Sort the log by case:concept:name and start_timestamp
    log_df = log_df.sort_values(by=["case:concept:name", "start:timestamp"]).reset_index(drop=True)

    # make the case:concept:name column as a string
    log_df["case:concept:name"] = log_df["case:concept:name"].astype(str)

    return log_df


def pareto_traces(log_path):

    # If the the log is in .xes format, import it and cast to dataframe
    if log_path[-4:] == ".xes":
        xes_log = xes_importer.apply(log_path)
        log_df = pm4py.convert_to_dataframe(xes_log)

    else:
        log_df = pd.read_csv(log_path)

    # Return the lenght of the traces in the log
    trace_lengths = log_df.groupby('case:concept:name').size()

    # For each trace in the log, append the length of the trace in the log
    # for index in log_df["case:concept:name"].unique():
    #     l.append(len(log_df[log_df["case:concept:name"] == index]))

    # Return the first quantile of the trace lengths
    # q = np.percentile(trace_lengths, 10)
    q = np.median(trace_lengths)

    return q