import simpy, time, sys

from network import *
from Sim_Kernel import *
from Preprocessing import *
from Postprocessing import *


def read_process_info(path):
    process_info_data = pd.read_excel(path)
    process_info = {}
    inout = {}

    for i in range(len(process_info_data)):
        temp = process_info_data.iloc[i]
        name = temp['name']
        process_type = temp['type']
        if process_type not in process_info.keys():
            process_info[process_type] = {}
        process_info[process_type][name] = {}
        process_info[process_type][name]['capacity'] = temp['Capacity']
        process_info[process_type][name]['unit'] = temp['unit']

        inout[name] = [temp['in'], temp['out']]

    virtual_list = ['Stock', 'Shelter', 'Painting']
    for virtual in virtual_list:
        if virtual == "Stock":
            process_info['Stockyard'][virtual] = {'capacity' : float('inf'), 'unit': 'm2'}
        elif virtual == 'Shelter':
            process_info['Shelter'][virtual] = {'capacity' : float('inf'), 'unit': 'm2'}
        else:
            process_info['Painting'][virtual] = {'capacity' : float('inf'), 'unit': 'm2'}

        inout[virtual]= [virtual, virtual]

    return process_info, inout


def read_converting(path):
    converting_df = pd.read_excel(path)
    converting_dict = dict()
    for idx in range(len(converting_df)):
        department = converting_df.iloc[idx]['Department']
        if department not in converting_dict.keys():
            converting_dict[department] = converting_df.iloc[idx]['Factory']
        else:
            factory = converting_dict[department]
            if type(factory) == str:
                converting_dict[department] = [factory]
            converting_dict[department].append(converting_df.iloc[idx]['Factory'])
    return converting_dict


def read_dock_series(path: object) -> object:
    data = pd.read_excel(path)
    dock_series_mapping = {data.iloc[i]['호선']: data.iloc[i]['도크'] for i in range(len(data))}

    return dock_series_mapping


def read_road(path_distance, path_objectid, data_path):
    network_distance = convert_to_json_road(path_distance, path_objectid, data_path)

    return network_distance

'''
Modeling
* monitor -> repetitive action of every simulation => no module 
* Resource -> need modeling just once => no modeling module, but hv resource_information module
- Part
- Process 
- Stock yard 
'''


def modeling_TP(path_tp):
    tp_info = pd.read_excel(path_tp)
    tps = dict()
    tp_minmax = dict()
    for i in range(len(tp_info)):
        temp = tp_info.iloc[i]
        yard = temp['운영구역'][0]
        if yard in ["1", "2"]:
            tp_name = temp['장비번호']
            tp_name = tp_name if tp_name not in tps.keys() else '{0}_{1}'.format(tp_name, 0)
            capacity = temp['최대 적재가능 블록중량(톤)']
            v_loaded = temp['만차 이동 속도(km/h)'] * 24 * 1000
            v_unloaded = temp['공차 이동 속도(km/h)'] * 24 * 1000
            yard = int(yard)
            tps[tp_name] = Transporter(tp_name, yard, capacity, v_loaded, v_unloaded)
            if yard not in tp_minmax.keys():
                tp_minmax[yard] = {"min": 1e8, "max": 0}

            tp_minmax[yard]["min"] = capacity if capacity < tp_minmax[yard]["min"] else tp_minmax[yard]["min"]
            tp_minmax[yard]["max"] = capacity if capacity > tp_minmax[yard]["max"] else tp_minmax[yard]["max"]

    return tps, tp_minmax


def modeling_parts(environment, data, process_dict, monitor_class, resource_class=None, distance_matrix=None,
                   stock_dict=None, inout=None, convert_dict=None, dock_dict=None, tp_minmax=None):
    part_dict = dict()
    blocks = dict()
    for part in data:
        part_data = data[part]
        series = part[:5]
        yard = 1 if dock_dict[series] in [1, 2, 3, 4, 5] else 2
        part_weight = part_data['weight'] if part_data['weight'] < tp_minmax[yard]['max'] else tp_minmax[yard]['max']
        block = Block(part, part_data['area'], part_data['size'], part_weight, part_data['data'])
        blocks[block.name] = block
        part_dict[part] = Part(part, environment, part_data['data'], process_dict, monitor_class,
                               resource=resource_class, network=distance_matrix, block=block, blocks=blocks,
                               child=part_data['child_block'], parent=part_data['parent_block'], stocks=stock_dict,
                               Inout=inout, convert_to_process=convert_dict, dock=dock_dict[series],
                               source_location=part_data['source_location'])

    return part_dict


def modeling_processes(process_dict, stock_dict, process_info, environment, parts, monitor_class, machine_num,
                       resource_class, convert_process):
    # 1. Stockyard
    stockyard_info = process_info['Stockyard']
    for stock in stockyard_info.keys():
        stock_dict[stock] = StockYard(environment, stock, parts, monitor_class,
                                      capacity=stockyard_info[stock]['capacity'], unit=stockyard_info[stock]['unit'])
    # 2. Shelter
    shelter_info = process_info['Shelter']
    for shelter in shelter_info.keys():
        process_dict[shelter] = Process(environment, shelter, machine_num, process_dict, parts, monitor,
                                        resource=resource_class, capacity=shelter_info[shelter]['capacity'],
                                        convert_dict=convert_process, unit=shelter_info[shelter]['unit'],
                                        process_type="Shelter")

    # 3. Painting
    painting_info = process_info['Painting']
    for painting in painting_info.keys():
        process_dict[painting] = Process(environment, painting, machine_num, process_dict, parts, monitor,
                                        resource=resource_class, capacity=painting_info[painting]['capacity'],
                                        convert_dict=convert_process, unit=painting_info[painting]['unit'],
                                        process_type="Painting")

    # 4. Factory
    factory_info = process_info['Factory']
    for factory in factory_info.keys():
        process_dict[factory] = Process(environment, factory, machine_num, process_dict, parts, monitor,
                                        resource=resource_class, capacity=factory_info[factory]['capacity'],
                                        convert_dict=convert_process, unit=factory_info[factory]['unit'],
                                        process_type="Factory")
    process_dict['Sink'] = Sink(environment, process_dict, parts, monitor_class)

    return process_dict, stock_dict


if __name__ == "__main__":
    start = time.time()
    # print(sys.argv[1])
    # 1. read input data
    with open('./result/Trial/input_data.json', 'r') as f:
        input_data = json.load(f)
    # with open(sys.argv[1], 'r') as f:
    #     input_data = json.load(f)

    process_info, inout = read_process_info(input_data['path_process_info'])
    converting = read_converting(input_data['path_converting_data'])
    dock = read_dock_series(input_data['path_dock_series_data'])

    # if need to preprocess with activity and bom
    if input_data['use_prior_process']:
        with open(input_data['path_preprocess'], 'r') as f:
            sim_data = json.load(f)
        print("Finish data loading at ", time.time() - start)
    else:
        print("Start combining Activity and BOM data at ", time.time() - start)
        data_path = processing_with_activity_N_bom(input_data, dock, converting)

        print("Finish data preprocessing at ", time.time() - start)

        with open(data_path, 'r') as f:
            sim_data = json.load(f)
        print("Finish data loading at ", time.time() - start)

    initial_date = sim_data['simulation_initial_date']
    block_data = sim_data['block_info']

    network_distance = read_road(input_data['path_distance'], input_data['path_road'], input_data['default_input'])

    # define simulation environment
    env = simpy.Environment()

    # Modeling
    stock_yard = dict()
    processes = dict()

    # 0. Monitor
    monitor = Monitor(input_data['default_result'], input_data['project_name'], pd.to_datetime(initial_date))

    # 1. Resource
    tps, tp_minmax = modeling_TP(input_data['path_transporter'])
    resource = Resource(env, processes, stock_yard, monitor, tps=tps, tp_minmax=tp_minmax, network=network_distance,
                        inout=inout)

    # 2. Block
    parts = modeling_parts(env, block_data, processes, monitor, resource_class=resource, distance_matrix=network_distance,
                           stock_dict=stock_yard, inout=inout, convert_dict=converting, dock_dict=dock, tp_minmax=tp_minmax)

    # 3. Process and StockYard
    processes, stock_yard = modeling_processes(processes, stock_yard, process_info, env, parts, monitor,
                                               input_data['machine_num'], resource, converting)

    start_sim = time.time()
    env.run()
    finish_sim = time.time()

    print("Execution time:", finish_sim - start_sim)
    # path_event_tracer, path_tp_info, path_road_info = monitor.save_information()
    path_event_tracer = monitor.save_information()
    print("number of part created = ", monitor.created)
    print("number of completed = ", monitor.completed)

    output_path = dict()
    output_path['input_path'] = './result/Trial/input_data.json'
    output_path['event_tracer'] = path_event_tracer
    output_path['tp_list'] = list(tps.keys())
    # output_path['tp_info'] = path_tp_info
    # output_path['road_info'] = path_road_info

    with open(input_data['default_result'] + 'result_path.json', 'w') as f:
        json.dump(output_path, f)
    print("Finish")

    # with open(input_data['default_result'] + 'Post.bat', 'w') as f:
    #     go_to_venv = "cd " + "C:/Users/sohyon/source/repos/HiApplication-SNU/env_simulation" + ' \n'
    #     f.write(go_to_venv)
    #     execute_post = "call " + "python Postprocessing.py " + "C:/Users/sohyon/source/repos/HiApplication-SNU/env_simulation" + input_data['default_result'][1:] + "Post.bat" + "\n"
    #     f.write(execute_post)
    # with open(input_data['default_result'] + 'post_processing.bat', 'w') as f:
    #     f.write("call conda env list \n")
    #     f.write("call conda activate env_sim \n")
    #     f.write("cd C:/Users/sohyon/PycharmProjects/Simulation_Module \n")
    #     f.write("call python Postprocessing.py {0} \n".format(input_data['default_result'] + 'result_path.json'))
    #     f.write("\npause")
