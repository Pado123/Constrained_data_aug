import pm4py
from datetime import timedelta

def discover_arrival_calendar(log, thr_h = 0.0, thr_wd = 0.0):

    N_events_per_hour = {wd: {h: 0 for h in range(24)} for wd in range(7)}

    for trace in log:
        ts = trace[0]['time:timestamp']
        N_events_per_hour[ts.weekday()][ts.hour] += 1

    N_events_per_hour_perc = {wd: {h: 0 for h in range(24)} for wd in range(7)}

    for weekday in range(7):
        for h in range(24):
            if sum(N_events_per_hour[weekday].values()):
                N_events_per_hour_perc[weekday][h] = N_events_per_hour[weekday][h] / sum(N_events_per_hour[weekday].values())
            else:
                N_events_per_hour_perc[weekday][h] = 0

    N_events_per_wd = {wd: 0 for wd in range(7)}

    for weekday in range(7):
        N_events_per_wd[weekday] += sum(N_events_per_hour[weekday].values())

    N_events_per_wd_perc = {wd: N_events_per_wd[wd]/sum(N_events_per_wd.values()) if sum(N_events_per_wd.values()) else 0 for wd in range(7)}

    calendar_wd_hour = {wd: {h: False for h in range(24)} for wd in range(7)}

    for wd in range(7):
        if N_events_per_wd_perc[wd] <= thr_wd:
            continue
        else:
            for hour in range(24):
                calendar_wd_hour[wd][hour] = N_events_per_hour_perc[wd][hour] > thr_h

    return calendar_wd_hour



def discover_res_calendars(log, thr_h = 0.0, thr_wd = 0.0):

    resources = list(pm4py.get_event_attribute_values(log, 'org:resource').keys())

    N_events_per_hour_res = {res: {wd: {h: 0 for h in range(24)} for wd in range(7)} for res in resources}

    for trace in log:
        for event in trace:
            res = event['org:resource']
            ts = event['time:timestamp']
            N_events_per_hour_res[res][ts.weekday()][ts.hour] += 1


    N_events_per_hour_res_perc = {res: {wd: {h: 0 for h in range(24)} for wd in range(7)} for res in resources}

    for res in resources:
        for weekday in range(7):
            for h in range(24):
                if sum(N_events_per_hour_res[res][weekday].values()):
                    N_events_per_hour_res_perc[res][weekday][h] = N_events_per_hour_res[res][weekday][h] / sum(N_events_per_hour_res[res][weekday].values())
                else:
                    N_events_per_hour_res_perc[res][weekday][h] = 0


    N_events_per_wd_res = {res: {wd: 0 for wd in range(7)} for res in resources}

    for res in resources:
        for weekday in range(7):
            N_events_per_wd_res[res][weekday] += sum(N_events_per_hour_res[res][weekday].values())


    N_events_per_wd_res_perc = {res: {wd: N_events_per_wd_res[res][wd]/sum(N_events_per_wd_res[res].values()) if sum(N_events_per_wd_res[res].values()) else 0 for wd in range(7)} for res in resources}

    calendar_wd_hour_res = {res: {wd: {h: False for h in range(24)} for wd in range(7)} for res in resources}

    for res in resources:
        for wd in range(7):
            if N_events_per_wd_res_perc[res][wd] <= thr_wd:
                continue
            else:
                for hour in range(24):
                    calendar_wd_hour_res[res][wd][hour] = N_events_per_hour_res_perc[res][wd][hour] > thr_h

    return calendar_wd_hour_res


def count_false_hours(calendar, start_ts, end_ts):
    false_hours_count = 0
    current_time = start_ts
    
    while current_time < end_ts:
        weekday = current_time.weekday()
        hour = current_time.hour
        
        if calendar.get(weekday, {}).get(hour) == False:
            false_hours_count += 1
            
        current_time += timedelta(hours=1)

    return false_hours_count

def add_minutes_with_calendar(start_ts, minutes_to_add, calendar):
    remaining_minutes = minutes_to_add
    current_time = start_ts

    while remaining_minutes > 0:
        weekday = current_time.weekday()
        hour = current_time.hour
        
        if calendar.get(weekday, {}).get(hour, False):
            minutes_in_current_hour = min(remaining_minutes, 60 - current_time.minute)
            
            current_time += timedelta(minutes=minutes_in_current_hour)
            remaining_minutes -= minutes_in_current_hour
        else:
            current_time = (current_time + timedelta(hours=1)).replace(minute=0)

    return current_time