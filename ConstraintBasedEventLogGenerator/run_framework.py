from pm4py.objects.log.importer.xes import importer as xes_importer
from src.train_utils import splitEventLog
from EventLogGenerator import EventLogGenerator
import os
import warnings
import time

warnings.filterwarnings('ignore')

# CHANGE THESE PARAMETERS AND COMMENT/UNCOMMMENT IN constraints_per_log.py

case_studies = [
    'ds02',
    'ds03',
    'ds01',
    'bpi12',
    'bpi17',
]

# N_SIM = 1000000000000
# exp = ' exp10' 


def print_time(execution_time, outpath):
    hours = int(execution_time // 3600)  
    minutes = int((execution_time % 3600) // 60) 
    seconds = execution_time % 60 
    with open(outpath + '/execution_time.txt', 'w') as f:
        f.write(f"Execution Time: {hours} hours, {minutes} minutes, {seconds:.6f} seconds")
    

if __name__ == '__main__':
    for case_study in case_studies:
            print('*********************************')
            print('*********************************\n')
            print(f'\n*********************************\n{case_study}\n*********************************')
        
            # Start time
            start_time = time.time()

            if case_study == 'bpi12':
                path_log = 'data/bpi12/bpi12w.xes'
                save_split_to = 'data/bpi12'
                save_simulations_to = 'simulations/bpi12'
                label_data_attributes=['AMOUNT_REQ']
                k = 3
            
            if case_study == 'bpi12a':
                path_log = 'data/bpi12a/bpi12a_pp.xes'
                save_split_to = 'data/bpi12a'
                save_simulations_to = 'simulations/bpi12a'
                label_data_attributes=['AMOUNT_REQ']
                k = 3
            if case_study == 'bpi12o':
                path_log = 'data/bpi12o/bpi12o_pp.xes'
                save_split_to = 'data/bpi12o'
                save_simulations_to = 'simulations/bpi12o'
                label_data_attributes=['AMOUNT_REQ']
                k = 3
            if case_study == 'bpi17':
                path_log = 'data/bpi17/bpi17w.xes'
                save_split_to = 'data/bpi17'
                save_simulations_to = 'simulations/bpi17'
                label_data_attributes=['LoanGoal', 'ApplicationType', 'RequestedAmount']
                k = 3
                
            if case_study == 'bpi17o':
                path_log = 'data/bpi17o/bpi17o_pp.xes'
                save_split_to = 'data/bpi17o'
                save_simulations_to = 'simulations/bpi17o'
                label_data_attributes=[ "MonthlyCost",  "OfferedAmount",]
                k = 3
              
            if case_study == 'ds06':
                path_log = 'data/ds06/log.xes'
                save_split_to = 'data/ds06'
                save_simulations_to = 'simulations/ds06'
                label_data_attributes = ['ATTR_WAIT_TIME', 'ATTR_URGENCY', 'ATTR_ARRIVAL_MODE']
                k = 3

            if case_study == 'ds01':
                path_log = 'data/ds01/log.xes'
                save_split_to = 'data/ds01'
                save_simulations_to = 'simulations/ds01'
                label_data_attributes = []
                k = 3

            if case_study == 'ds03':
                path_log = 'data/ds03/log.xes'
                save_split_to = 'data/ds03'
                save_simulations_to = 'simulations/ds03'
                label_data_attributes = ['ATTR_1', 'ATTR_2', 'ATTR_3', 'ATTR_4', 'ATTR_5', 'ATTR_6', 'ATTR_7']
                k = 3

            if case_study == 'ds02':
                path_log = 'data/ds02/log.xes'
                save_split_to = 'data/ds02'
                save_simulations_to = 'simulations/ds02'
                label_data_attributes = []
                k = 3
            
            
            log = xes_importer.apply(path_log)

            os.makedirs(save_split_to, exist_ok=True)
            train_log, test_log = splitEventLog(log, train_size = 0.8, split_temporal = True, save_to = save_split_to)

            start_timestamp = test_log[0][0]['time:timestamp']
            
            end_time = time.time()
            preprocessing_time = end_time - start_time
            
            
            ######################
            ##### SCENARIO A #####
            ###################### 
            start_time = time.time()
            outpath_A = f'results/{save_simulations_to}{exp}/scenarioA' 
            os.makedirs(outpath_A, exist_ok=True)
            print('\n*********************************\nSCENARIO A\n*********************************')
            generator = EventLogGenerator(train_log, k=k, label_data_attributes=label_data_attributes, 
                                            case_study=case_study, scenario='scenarioA')
            for i in range(N_SIM):
                simulated_traces = generator.apply(N=len(test_log), start_timestamp = start_timestamp)
                simulated_traces.to_csv(outpath_A + f'/sim_{i}.csv', index=False)
                print(f'{case_study} simulation {i} with SCENARIO A done!')
            end_time = time.time()
            execution_time = end_time - start_time + preprocessing_time
            print_time(execution_time, outpath_A)
            
            # ######################
            # ##### SCENARIO B #####
            # ######################            
            start_time = time.time() 
            outpath_B = f'results/{save_simulations_to}{exp}/scenarioB'  
            os.makedirs(outpath_B, exist_ok=True) 
            print('\n*********************************\nSCENARIO B\n*********************************')
            generator = EventLogGenerator(train_log, k=50, label_data_attributes=label_data_attributes, 
                                            case_study=case_study, scenario='scenarioB')
            for i in range(N_SIM):
                simulated_traces = generator.sample_traces(N=len(test_log))
                simulated_traces.to_csv(outpath_B + f'/sim_{i}.csv', index=False)
                print(f'{case_study} simulation {i} with SCENARIO B done!')
            end_time = time.time()
            execution_time = end_time - start_time + preprocessing_time
            print_time(execution_time, outpath_B)
            
            # ######################
            # ##### SCENARIO C #####
            # ######################
            start_time = time.time()      
            outpath_C = f'results/{save_simulations_to}{exp}/scenarioC'
            os.makedirs(outpath_C, exist_ok=True)
            print('\n*********************************\nSCENARIO C\n*********************************')
            generator = EventLogGenerator(train_log, k=k, label_data_attributes=label_data_attributes, 
                                            case_study=case_study, scenario='scenarioC')
            for i in range(N_SIM):
                simulated_traces = generator.apply(N=len(test_log), start_timestamp = start_timestamp)
                simulated_traces.to_csv(outpath_C + f'/sim_{i}.csv', index=False)
                print(f'{case_study} simulation {i} with SCENARIO C done!')
            end_time = time.time()
            execution_time = end_time - start_time + preprocessing_time
            print_time(execution_time, outpath_C)
            
            # ######################
            # ##### SCENARIO D #####
            # ######################    
            start_time = time.time()              
            outpath_D = f'results/{save_simulations_to}{exp}/scenarioD'
            os.makedirs(outpath_D, exist_ok=True)     
            print('\n*********************************\nSCENARIO D\n*********************************')
            generator = EventLogGenerator(train_log, k=k, label_data_attributes=label_data_attributes, 
                                            case_study=case_study, scenario='scenarioD')
            for i in range(N_SIM):
                simulated_traces = generator.apply(N=len(test_log), start_timestamp = start_timestamp)
                simulated_traces.to_csv(outpath_D + f'/sim_{i}.csv', index=False)
                print(f'{case_study} simulation {i} with SCENARIO D done!')
            end_time = time.time()
            execution_time = end_time - start_time + preprocessing_time
            print_time(execution_time, outpath_D)

            # ######################
            # ##### SCENARIO E #####
            # ######################
            start_time = time.time() 
            outpath_E= f'results/{save_simulations_to}{exp}/scenarioE'
            os.makedirs(outpath_E, exist_ok=True)
            print('\n*********************************\nSCENARIO E\n*********************************')
            generator = EventLogGenerator(train_log, k=50, label_data_attributes=label_data_attributes, 
                                            case_study=case_study, scenario='scenarioE')
            for i in range(N_SIM):
                simulated_traces = generator.sample_traces(N=len(test_log))
                simulated_traces.to_csv(outpath_E + f'/sim_{i}.csv', index=False)
                print(f'{case_study} simulation {i} with SCENARIO E done!')
            end_time = time.time()
            execution_time = end_time - start_time + preprocessing_time
            print_time(execution_time, outpath_E)
