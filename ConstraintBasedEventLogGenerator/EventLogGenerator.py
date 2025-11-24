from src.gen_seq_utils import get_prefix_proba
from src.gen_res_utils import get_prefix_res_proba, get_possible_prefixes_res_act
from src.gen_attr_utils import get_prefix_attr_proba, get_possible_prefixes_attr_act, get_trace_attribute_labels, get_trace_attribute_proba
from src.gen_time_utils import get_distr_arrival_time, get_distr_ex_times, sample_arrival_times, sample_ex_times
from src.prefix_utils import get_more_similar_prefix
from src.preprocess_utils import add_lc_to_act
from src.calendar_utils import discover_arrival_calendar, discover_res_calendars, add_minutes_with_calendar
import random
import pandas as pd
from tqdm import tqdm 
import pm4py
from constraints.utils_ts import extract_event_seqs_and_alphabet
from constraints.constants import START_PLACEHOLDER, END_PLACEHOLDER
from constraints.framework_constraints import get_filtered_log, get_prefix_proba_constrained

class EventLogGenerator:
    def __init__(self, log, k, label_data_attributes=[], case_study:str ='', scenario: str = ''):

        df_log = pm4py.convert_to_dataframe(log)
        df_log['time:timestamp'] = pd.to_datetime(df_log['time:timestamp'])
        df_log.index = range(len(df_log))
        self.log = pm4py.convert_to_event_log(df_log)
        self.k = k
        self.log = add_lc_to_act(self.log)
        
        
        self.label_data_attributes = label_data_attributes

        self.case_study = case_study
        self.scenario = scenario
        
        event_seqs, self.alphabet  = extract_event_seqs_and_alphabet(self.log)   
        
        if scenario == 'scenarioA':
            self.alphabet_pruned, self.prefixes_proba_next_state = get_prefix_proba_constrained(
                self.case_study, self.alphabet, event_seqs, self.k)

        elif scenario in ['scenarioB', 'scenarioE']:
            if scenario == 'scenarioB':
                self.log = get_filtered_log(self.log, self.case_study, self.alphabet)

            if label_data_attributes:
                self.trace_attribute_labels = get_trace_attribute_labels(self.log, self.label_data_attributes)
                self.event_attributes_labels = list(set(self.label_data_attributes) - set(self.trace_attribute_labels))
            return

        elif scenario in ['scenarioC', 'scenarioD']:
            if scenario == 'scenarioC':
                self.log = get_filtered_log(self.log, self.case_study, self.alphabet)

            self.prefixes_proba_next_act = get_prefix_proba(self.log, self.k)


        self.prefixes_proba_next_res = get_prefix_res_proba(self.log, k)

        if label_data_attributes:
            self.trace_attribute_labels = get_trace_attribute_labels(self.log, self.label_data_attributes)
            self.event_attributes_labels = list(set(self.label_data_attributes) - set(self.trace_attribute_labels))

            self.prob_trace_attributes = get_trace_attribute_proba(self.log, self.trace_attribute_labels)
            self.prefixes_proba_next_attr = get_prefix_attr_proba(self.log, self.event_attributes_labels, k)

        # calendars discovery
        self.arrival_calendar = discover_arrival_calendar(self.log)
        self.res_calendars = discover_res_calendars(self.log)

        # compute durations distributions
        self.arrival_times_distr = get_distr_arrival_time(self.log, self.arrival_calendar)
        self.ex_times_distr = get_distr_ex_times(self.log, self.res_calendars)


    def generate_seq_constrained(self, N_seq: int = 100) -> list:
        """
        Generates sequences of activities from a prefix-to-next-state probability dictionary.

        Args:
            N_seq (int): Number of sequences to generate.

        Returns:
            List[List[Tuple]]: A list of sequences, where each sequence is a list of state tuples.
        """
        possible_prefixes = list(self.prefixes_proba_next_state.keys())
        gen_seq_log = []
        similar_prefixes = dict()
        
        for p in possible_prefixes:
            if START_PLACEHOLDER in p[0] :
                start_prefix = p
        
        for _ in tqdm(range(N_seq)):
            prefix = start_prefix
            
            trace = []

            while True:
                if prefix not in self.prefixes_proba_next_state:
                    if prefix not in similar_prefixes:
                        similar_prefixes[prefix] = get_more_similar_prefix(prefix, possible_prefixes)
                    prefix = similar_prefixes[prefix]

                next_states_probs = self.prefixes_proba_next_state[prefix]
                next_states = list(next_states_probs.keys())
                weights = [prob for _, prob in next_states_probs.values()]

                next_state = random.choices(next_states, weights=weights)[0]
                transition_symbol, _ = next_states_probs[next_state]           

                if END_PLACEHOLDER == transition_symbol:
                    break

                trace.append(transition_symbol)
                prefix = next_state
                if prefix[0][0] == (START_PLACEHOLDER,) and len(prefix) > 1:
                    prefix = prefix[1:]

            gen_seq_log.append(trace)

        return gen_seq_log

    def generate_seq(self, N_seq=100):
        """

        This generate sequences of activities from conditional probabilities
        N_seq: number of seuqences to generate
        Output : list of activity sequences
        Output example : with N_seq=2 --> [['act_1','act_2'], ['act_1','act_2', 'act_3]]

        """
        
        if self.scenario == 'scenarioA':
            gen_seq_log = self.generate_seq_constrained(N_seq)
        else:
            possible_prefixes = list(self.prefixes_proba_next_act.keys())
            gen_seq_log = []
            similar_prefixes = dict()
            for _ in tqdm(range(N_seq)):
                prefix = ()
                trace = []
                while True:
                    if prefix not in self.prefixes_proba_next_act.keys():
                        if prefix not in similar_prefixes.keys():   
                            similar_prefixes[prefix] = get_more_similar_prefix(prefix, possible_prefixes)
                        prefix = similar_prefixes[prefix]
                    act = random.choices(list(self.prefixes_proba_next_act[prefix].keys()), weights = self.prefixes_proba_next_act[prefix].values())[0]
                    if act == '<END>':
                        break
                    trace.append(act)
                    prefix = prefix + (act,)
                    prefix = prefix[-self.k:] 
                gen_seq_log.append(trace)

        return gen_seq_log
  
    

    def generate_resources(self, log_seqs):

        possible_prefixes = get_possible_prefixes_res_act(self.prefixes_proba_next_res)
        simulated_traces_act_res = []
        similar_prefixes = dict()
        for sim_trace_act in tqdm(log_seqs):
            sim_trace_act_res = []
            prefix = tuple()
            for act in sim_trace_act:
                pref_act = (prefix, act)
                if prefix not in possible_prefixes[act]:
                    if prefix not in similar_prefixes.keys():
                        similar_prefixes[prefix] = dict()
                    if act not in similar_prefixes[prefix].keys():
                        similar_prefixes[prefix][act] = get_more_similar_prefix(prefix, possible_prefixes[act])
                    pref_act = (similar_prefixes[prefix][act], act)
                res = random.choices(list(self.prefixes_proba_next_res[pref_act].keys()), weights = self.prefixes_proba_next_res[pref_act].values())[0]
                sim_trace_act_res.append((act, res))
                prefix = prefix + ((act, res),)
                prefix = prefix[-self.k:]
            simulated_traces_act_res.append(sim_trace_act_res)  

        return simulated_traces_act_res
    

    def generate_attributes(self, log_seqs, log_seqs_res):

        possible_prefixes = get_possible_prefixes_attr_act(self.prefixes_proba_next_attr)
        simulated_traces_act_res_attr = []
        similar_prefixes = dict()
        for i, sim_trace_act in tqdm(enumerate(log_seqs), total=len(log_seqs)):
            sim_trace_act_res_attr = []
            prefix = tuple()
            for j, act in enumerate(sim_trace_act):
                pref_act = (prefix, act)
                if prefix not in possible_prefixes[act]:
                    if prefix not in similar_prefixes.keys():
                        similar_prefixes[prefix] = dict()
                    if act not in similar_prefixes[prefix].keys():
                        similar_prefixes[prefix][act] = get_more_similar_prefix(prefix, possible_prefixes[act])
                    pref_act = (similar_prefixes[prefix][act], act)
                attr = random.choices(list(self.prefixes_proba_next_attr[pref_act].keys()), weights = self.prefixes_proba_next_attr[pref_act].values())[0]
                sim_trace_act_res_attr.append((act, log_seqs_res[i][j][1], attr))
                prefix = prefix + ((act, attr),)
                prefix = prefix[-self.k:]                
            simulated_traces_act_res_attr.append(sim_trace_act_res_attr)  

        return simulated_traces_act_res_attr
    

    def generate_timestamps(self, log_seqs, start_timestamp):

        arrival_times = sample_arrival_times(self.arrival_times_distr[0], self.arrival_times_distr[1], len(log_seqs)-1)
        ex_times = sample_ex_times(self.ex_times_distr, log_seqs)

        timestamps = [[start_timestamp]]
        for i, a_t in enumerate(arrival_times):
            start_timestamp = add_minutes_with_calendar(start_timestamp, a_t, self.arrival_calendar)
            timestamps.append([start_timestamp])
        
        for i in tqdm(range(len(log_seqs))):
            for j in range(1, len(log_seqs[i])):
                prev_a = log_seqs[i][j-1][0]
                cur_a = log_seqs[i][j][0]
                res = log_seqs[i][j][1]
                t_seconds = ex_times[(prev_a, cur_a)].pop()
                t = add_minutes_with_calendar(timestamps[i][-1], t_seconds, self.res_calendars[res])
                timestamps[i].append(t)

        return timestamps
    
    def generate_lifecyle(self, df):

        df['lifecycle:transition'] = df['concept:name'].apply(lambda x: x.split('_lc:')[-1])
        df['concept:name'] = df['concept:name'].apply(lambda x: ''.join(x.split('_lc:')[:-1]))

        return df
    

    def apply(self, N, start_timestamp):

        # start_timestamp = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")

        print('Generate sequences...')
        log_seq = self.generate_seq(N)
        print('Generate resources...')
        log_seq_res = self.generate_resources(log_seq)
        if getattr(self, "trace_attribute_labels", []):
            print('Generate attributes...')
            trace_attributes = random.choices(list(self.prob_trace_attributes.keys()), weights=self.prob_trace_attributes.values(), k=N)
            log_seq = self.generate_attributes(log_seq, log_seq_res)
        else:
            log_seq = log_seq_res

        print('Generate timestamps...')
        timestamps_log = self.generate_timestamps(log_seq, start_timestamp)

        ids = [str(i) for i in range(1, len(log_seq)+1) for _ in range(len(log_seq[i-1]))]
        activities = [ev[0] for trace in log_seq for ev in trace]
        roles = [ev[1] for trace in log_seq for ev in trace]
        if self.label_data_attributes:
            attributes_dict = {l: [] for l in self.label_data_attributes}
            for i, l in enumerate(self.event_attributes_labels):
                attributes_dict[l] = [ev[2][i] for trace in log_seq for ev in trace]
            for k, l in enumerate(self.trace_attribute_labels):
                for i in range(len(trace_attributes)):
                    for _ in range(len(log_seq[i])):
                        attributes_dict[l].append(trace_attributes[i][k])
        else:
            attributes_dict = dict()
        timestamps = [t for trace in timestamps_log for t in trace]
        
        df = pd.DataFrame({'case:concept:name': ids, 'concept:name': activities, 'time:timestamp': timestamps, 'org:resource': roles} | attributes_dict)
        df = self.generate_lifecyle(df)

        return df
    
    
    def sample_traces(self, N):
        
        sampled_ids = list(range(len(self.log)))
        sampled_case_ids = random.choices(sampled_ids, k=N)
        sampled_traces = [self.log[i] for i in sampled_case_ids]


        def get_first_timestamp(trace):
            return trace[0]["time:timestamp"] 
        sampled_traces.sort(key=get_first_timestamp)

        rows = []
        for new_case_id, trace in enumerate(sampled_traces):
            for events in trace:
                row = dict(events) 
                row["case:concept:name"] = str(new_case_id+1)  # nuovo case ID
                rows.append(row)

        columns_to_keep = [
            'case:concept:name', 'concept:name', 'time:timestamp','org:resource', 
        ] 
        
        trace_attrs = getattr(self, "trace_attribute_labels", [])
        if trace_attrs:
            columns_to_keep += trace_attrs
        event_attrs = getattr(self, "event_attributes_labels", [])
        if event_attrs:
            columns_to_keep += event_attrs
            
        columns_to_keep.append('lifecycle:transition')
        
        df = pd.DataFrame(rows)
        df = df[columns_to_keep]
        df["concept:name"] = df["concept:name"].str.replace("_lc:start", "", regex=False)
        df["concept:name"] = df["concept:name"].str.replace("_lc:complete", "", regex=False)
        
        if 'lifecycle:transition' in df.columns:
            df['lifecycle:transition'] = df['lifecycle:transition'].str.lower()
        
        return df