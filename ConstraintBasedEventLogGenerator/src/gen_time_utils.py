import pm4py
from src.distribution_utils import find_best_fit_distribution, sample_time
from src.calendar_utils import count_false_hours

def get_arrival_times(log, arrival_calendar):

    arrival_times = []
    for i in range(1, len(log)):
        time_prec = log[i-1][0]['time:timestamp']
        time_curr = log[i][0]['time:timestamp']
        ar_time = max((time_curr - time_prec).total_seconds()/60 - count_false_hours(arrival_calendar, time_prec, time_curr)*60, 0)
        arrival_times.append(ar_time)

    return arrival_times


def get_ex_times(log, res_calendars):

    ex_times = dict()
    j=0
    for trace in log:
        for i in range(1, len(trace)):
            prec_t = trace[i-1]['time:timestamp']
            cur_t = trace[i]['time:timestamp']
            prec_a = trace[i-1]['concept:name']
            cur_a = trace[i]['concept:name']
            cur_res = trace[i]['org:resource']
            calendar = res_calendars[cur_res]
            ex_t = max((cur_t - prec_t).total_seconds()/60 - count_false_hours(calendar, prec_t, cur_t)*60, 0)
            if (prec_a, cur_a) in ex_times.keys():
                ex_times[(prec_a, cur_a)].append(ex_t)
            else:
                ex_times[(prec_a, cur_a)] = [ex_t]
        j = j+1        
        if (j % 5000 == 0):
            print("get_ex_times traces done:" + str(j))

    return ex_times


def get_distr_arrival_time(log, arrival_calendar):
    
    arrival_times = get_arrival_times(log, arrival_calendar)
    distr = find_best_fit_distribution(arrival_times)
    max_t = max(arrival_times)

    return distr, max_t


def get_distr_ex_times(log, res_calendars):

    ex_times = get_ex_times(log, res_calendars)
    ex_times_distr = dict()

    acts_couples = list(ex_times.keys())
    for acts in acts_couples:
        if len(set(ex_times[acts])) > 1:
            max_t = max(ex_times[acts])
            ex_times_distr[acts] = find_best_fit_distribution(ex_times[acts]), max_t
        else:
            ex_times_distr[acts] = {'name': 'fixed', 'value': ex_times[acts][0]}, None

    return ex_times_distr


def sample_arrival_times(distr, max_t, N):

    arrival_times_sim = sample_time(distr, N)
    arrival_times_sim = [min(x, max_t) for x in arrival_times_sim]

    return arrival_times_sim


def sample_ex_times_acts(distr, max_t, acts, sim_traces):

    prev = acts[0]
    cur = acts[1]

    N = 0
    for trace in sim_traces:
        for i in range(1, len(trace)):
            if (trace[i-1][0] == prev) and (trace[i][0] == cur):
                N += 1

    if not max_t:
        ex_times_acts = [distr['value']]*N
    else:
        ex_times_acts = sample_time(distr, N)
        ex_times_acts = [min(x, max_t) for x in ex_times_acts]

    return ex_times_acts


def sample_ex_times(ex_times_distr, sim_traces):

    ex_times_sim = dict()

    acts_couples = list(ex_times_distr.keys())
    for acts in acts_couples:
        ex_times_sim[acts] = sample_ex_times_acts(ex_times_distr[acts][0], ex_times_distr[acts][1], acts, sim_traces)

    return ex_times_sim


