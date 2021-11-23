import json, math, os, sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib import font_manager, rc

# default - in Window
font_name = font_manager.FontProperties(fname="C:\Windows\Fonts\H2GTRM.TTF").get_name()

# At Apple Product
# font_at_prof = '/Users/jonathan/Library/Fonts/NanumSquareB.ttf'
# font_name = font_manager.FontProperties(fname=font_at_prof).get_name()

rc('font', family=font_name)


def road_usage(event_tracer, network_road, tp_info, time_range):
    '''
    unload, 호출된 TP가 호출한 공장까지 가는 이벤트 : tp_unloaded_start
    load, tp가 블록이랑 같이 이동하는 이벤트 : tp_loaded_start
    '''

    # Select Target Events
    event_list = ["tp_unloaded_start", "tp_unloaded_finish", "tp_loaded_start", "tp_loaded_finish"]
    event_tracer['event_index'] = event_tracer['Event'].apply(lambda x: 1 if x in event_list else 0)
    event_tracer_road = event_tracer[event_tracer['event_index'] == 1]
    event_tracer_road = event_tracer_road.reset_index(drop=True)
    event_tp_group = event_tracer_road.groupby(event_tracer_road['Resource'])
    # Variables
    road_usage_dict = dict()
    total_number = 0
    daily_number = [0 for _ in range(time_range)]
    total_time = 0.0
    daily_time = [0.0 for _ in range(time_range)]

    for tp_name in tp_info:
        event_tp = event_tp_group.get_group(tp_name)
        event_tp = event_tp.reset_index(drop=True)
        for i in range(int(len(event_tp)*0.5)):
            start = event_tp.iloc[2*i]
            finish = event_tp.iloc[2*i + 1]

            from_process = start["From"]
            to_process = start["To"]
            used_road = network_road[from_process][to_process]
            start_time = start["Simulation time"]
            finish_time = finish["Simulation time"]
            each_used_time = (finish_time - start_time) * 24 / len(used_road)

            for road_id in used_road:
                object_id = road_id[0]
                if object_id not in road_usage_dict.keys():
                    road_usage_dict[object_id] = {"Tot.Number": 0, "Tot.Number_Ratio": 0.0, "Tot.Time": 0.0,
                                                  "Tot.Time_Ratio": 0.0, "Daily.Number": [0 for _ in range(time_range)],
                                                  "Daily.Number_Ratio": [0.0 for _ in range(time_range)],
                                                  "Daily.Time": [0.0 for _ in range(time_range)]}
                # 사용 횟수
                road_usage_dict[object_id]["Tot.Number"] += 1
                total_number += 1
                road_usage_dict[object_id]["Daily.Number"][int(math.floor(start_time))] += 1
                daily_number[int(start_time)] += 1
                # 사용 시간
                road_usage_dict[object_id]["Tot.Time"] += each_used_time
                total_time += each_used_time
                road_usage_dict[object_id]["Daily.Time"][int(math.floor(start_time))] += each_used_time * 60
                daily_time[int(math.floor(start_time))] += each_used_time * 60

    for road_id in road_usage_dict.keys():
        road_usage_dict[road_id]["Tot.Number_Ratio"] = (road_usage_dict[road_id]["Tot.Number"] / total_number) * 100
        road_usage_dict[road_id]["Daily.Number_Ratio"] = [
            road_usage_dict[road_id]["Daily.Number"][i] / daily_number[i] if daily_number[i] > 0 else 0 for i in
            range(len(daily_number))]
        road_usage_dict[road_id]["Tot.Time_Ratio"] = (road_usage_dict[road_id]["Tot.Time"] / total_time) * 100

    return road_usage_dict


def tp_index(event_tracer, tp_info, time_range, start_time, finish_time, result_path):  # get get tp moving distance and time each day
    # Select Target Events
    event_list = ["tp_loaded_start", "tp_loaded_finish"]
    event_tracer.loc[:, 'Date'] = pd.to_datetime(event_tracer['Date'], format='%Y-%m-%d')
    event_tracer = event_tracer[(event_tracer['Date'] <= finish_time) & (event_tracer['Date'] >= start_time)]
    event_tracer['event_index'] = event_tracer['Event'].apply(lambda x: 1 if x in event_list else 0)
    event_tracer_road = event_tracer[event_tracer['event_index'] == 1]
    event_tracer_road = event_tracer_road.reset_index(drop=True)
    event_tp_group = event_tracer_road.groupby(event_tracer_road['Resource'])
    # Variables
    tp_usage_dict = dict()
    total_number = 0
    daily_number = [0 for _ in range(time_range)]
    total_time = 0.0
    daily_time = [0.0 for _ in range(time_range)]
    time_range_list = [0.0 for _ in range(time_range)]
    time_date_list = [(start_date_time + pd.DateOffset(days=day)).date() for day in range(time_range)]
    for tp_name in tp_info.keys():
        event_tp = event_tp_group.get_group(tp_name)
        event_tp = event_tp.reset_index(drop=True)
        tp_usage_dict[tp_name] = {"Tot.Load(avg.)": 0.0, "Tot.Distance(avg.)": 0.0, "Tot.Time(avg.)": 0.0,
                                  "Daily.Load(tot.)": time_range_list, "Daily.Distance(tot.)": time_range_list,
                                  "Daily.Time(tot.)": time_range_list, "Daily.Load(avg.)": time_range_list,
                                  "Daily.Distance(avg.)": time_range_list, "Daily.Time(avg.)": time_range_list}
        total_load = 0
        total_distance = 0
        total_time = 0
        time_idx = 0
        load_list = [list() for _ in range(len(time_range_list))]
        distance_list = [list() for _ in range(len(time_range_list))]
        tot_time_list= [list() for _ in range(len(time_range_list))]

        for i in range(int(len(event_tp) * 0.5)):
            start = event_tp.iloc[2 * i]
            finish = event_tp.iloc[2 * i + 1]

            # 전체 기간
            total_load += start['Load']
            total_distance += start['Distance']
            total_time += (finish['Simulation time'] - start['Simulation time']) * 24 * 60

            # Daily
            time = int(math.floor(start['Simulation time']))
            load_list[time].append(start['Load'])
            distance_list[time].append(start['Distance'])
            tot_time_list[time].append((finish['Simulation time'] - start['Simulation time']) * 24 * 60)



        tp_usage_dict[tp_name]["Tot.Load(avg.)"] = total_load / int(len(event_tp) * 0.5)
        tp_usage_dict[tp_name]["Tot.Distance(avg.)"] = total_distance / int(len(event_tp) * 0.5)
        tp_usage_dict[tp_name]["Tot.Time(avg.)"] = total_time / int(len(event_tp) * 0.5)

        for idx in range(time_range):
            day_load = load_list[idx]
            if len(day_load) > 0:
                print(0)
            tp_usage_dict[tp_name]['Daily.Load(tot.)'][idx] = sum(day_load) if len(day_load) > 0 else 0.0
            tp_usage_dict[tp_name]['Daily.Load(avg.)'][idx] = sum(day_load) / len(day_load) if len(day_load) > 0 else 0.0

            day_distance = distance_list[idx]
            tp_usage_dict[tp_name]['Daily.Distance(tot.)'][idx] = sum(day_distance) if len(day_distance) > 0 else 0.0
            tp_usage_dict[tp_name]['Daily.Distance(avg.)'][idx] = sum(day_distance) / len(day_distance) if len(day_distance) > 0 else 0.0

            day_time = tot_time_list[idx]
            tp_usage_dict[tp_name]['Daily.Time(tot.)'][idx] = sum(day_time) if len(day_time) > 0 else 0.0
            tp_usage_dict[tp_name]['Daily.Time(avg.)'][idx] = sum(day_time) / len(day_time) if len(day_time) > 0 else 0.0

        ## Make Graphs
        if not os.path.exists(result_path + 'Transporter'):
            os.makedirs(result_path + 'Transporter')
        if not os.path.exists(result_path + 'Transporter/' + '{0} Yard'.format(tp_info[tp_name]['yard'])):
            os.makedirs(result_path + 'Transporter/' + '{0} Yard'.format(tp_info[tp_name]['yard']))

        ### Daily 부하
        fig, ax = plt.subplots()
        line = ax.plot(time_date_list, tp_usage_dict[tp_name]["Daily.Load(avg.)"], color='black', marker="o")
        line_capa = ax.plot(time_date_list, [tp_info[tp_name]['capacity'] for _ in range(time_range)], color="red")
        line_avg = ax.plot(time_date_list, [tp_usage_dict[tp_name]["Tot.Load(avg.)"] for _ in range(time_range)], color="blue")

        plt.show()
        print(0)

        # fig, ax = plt.subplots()
        # if stock == 'Stock':
        #     line = ax.plot(event_time, event_area, color="blue", marker="o")
        #     ax.set_ylabel("Area")
        #     ax.set_ylim([0, max(event_area) * 1.2])
        #     max_area_unit = math.ceil(max(event_area) / 10)
        #     area_digit_num = len(str(max_area_unit)) - 1
        #     area_digit = math.ceil(max_area_unit / math.pow(10, area_digit_num)) * math.pow(10, area_digit_num)
        #     ax.yaxis.set_major_locator(ticker.MultipleLocator(area_digit))
        # else:
        #     line = ax.plot(event_time, event_area, color="blue", marker="o")
        #     ax.set_ylabel("Ratio")
        #     ax.set_ylim([0, stock_area * 1.05])
        #     area_unit = math.ceil(stock_area / 10)
        #     ax.yaxis.set_major_locator(ticker.MultipleLocator(area_unit))
    return tp_usage_dict


def calculate_stock_occupied_area(result_path, event_tracer, input_data, stock_capacity):
    save_path_stock = result_path + '/Stock'
    if not os.path.exists(save_path_stock):
        os.makedirs(save_path_stock)

    stock_event = event_tracer[event_tracer['Process Type'] == 'Stock']
    stock_list = list(np.unique(list(stock_event['Process'].dropna())))


    stock_capacity.loc[len(stock_capacity)] = ["Stock", float("inf")]
    capacity_dict = {stock_capacity.iloc[i]['name']: stock_capacity.iloc[i]['area'] for i in range(len(stock_capacity))}
    for stock in stock_list:
        each_stock_event = stock_event[stock_event['Process'] == stock]
        stock_area = capacity_dict[stock]
        event_area = list(each_stock_event['Load'])
        if len(event_area) > 0:
            event_time = list(each_stock_event['Simulation time'])
            fig, ax = plt.subplots()
            if stock == 'Stock':
                line = ax.plot(event_time, event_area, color="blue", marker="o")
                ax.set_ylabel("Area")
                ax.set_ylim([0, max(event_area) * 1.2])
                max_area_unit = math.ceil(max(event_area) / 10)
                area_digit_num = len(str(max_area_unit)) - 1
                area_digit = math.ceil(max_area_unit / math.pow(10, area_digit_num)) * math.pow(10, area_digit_num)
                ax.yaxis.set_major_locator(ticker.MultipleLocator(area_digit))
            else:
                line = ax.plot(event_time, event_area, color="blue", marker="o")
                ax.set_ylabel("Ratio")
                ax.set_ylim([0, stock_area * 1.05])
                area_unit = math.ceil(stock_area / 10)
                ax.yaxis.set_major_locator(ticker.MultipleLocator(area_unit))

            ax.set_title("{0} occupied area".format(stock), fontsize=13, fontweight="bold")
            ax.set_xlabel("Time")

            filepath = save_path_stock + '/{0}.png'.format(stock)
            plt.savefig(filepath, dpi=600, transparent=True)
            # plt.show()
            print("### {0} ###".format(stock))


def calculate_painting_occupied_area(result_path, event_tracer, input_data, process_capacity):
    save_path_painting = result_path + '/Painting'
    if not os.path.exists(save_path_painting):
        os.makedirs(save_path_painting)

    painting_event = event_tracer[event_tracer['Process_Type'] == 'Painting']
    painting_list = list(np.unique(list(painting_event['Process'].dropna())))

    if input_data['painting_virtual']:
        painting_list.append("Painting")
        process_capacity["Painting"] = float("inf")

    for painting in painting_list:
        each_painting_event = painting_event[painting_event['Process'] == painting]
        painting_area = process_capacity[painting]
        event_area = list(each_painting_event['Area'])
        if len(event_area) > 0:
            event_time = list(each_painting_event['Time'])
            fig, ax = plt.subplots()
            if painting == 'Painting':
                line = ax.plot(event_time, event_area, color="blue", marker="o")
                ax.set_ylabel("Area")
                ax.set_ylim([0, max(event_area) * 1.2])
                max_area_unit = math.ceil(max(event_area) / 10)
                area_digit_num = len(str(max_area_unit)) - 1
                area_digit = math.ceil(max_area_unit / math.pow(10, area_digit_num)) * math.pow(10, area_digit_num)
                ax.yaxis.set_major_locator(ticker.MultipleLocator(area_digit))
            else:
                line = ax.plot(event_time, event_area, color="blue", marker="o")
                ax.set_ylabel("Ratio")
                ax.set_ylim([0, painting_area * 1.05])
                area_unit = math.ceil(painting_area / 10)
                ax.yaxis.set_major_locator(ticker.MultipleLocator(area_unit))

            ax.set_title("{0} occupied area".format(painting), fontsize=13, fontweight="bold")
            ax.set_xlabel("Time")

            filepath = save_path_painting + '/{0}.png'.format(painting)
            plt.savefig(filepath, dpi=600, transparent=True)
            # plt.show()
            print("### {0} ###".format(painting))


def calculate_shelter_occupied_area(result_path, event_tracer, input_data, process_capacity):
    save_path_shelter = result_path + '/Shelter'
    if not os.path.exists(save_path_shelter):
        os.makedirs(save_path_shelter)

    shelter_event = event_tracer[event_tracer['Process_Type'] == 'Shelter']
    shelter_list = list(np.unique(list(shelter_event['Process'].dropna())))

    if input_data['shelter_virtual']:
        shelter_list.append("Shelter")
        process_capacity["Shelter"] = float("inf")

    for shelter in shelter_list:
        each_shelter_event = shelter_event[shelter_event['Process'] == shelter]
        shelter_area = process_capacity[shelter]
        event_area = list(each_shelter_event['Area'])
        if len(event_area) > 0:
            event_time = list(each_shelter_event['Time'])
            fig, ax = plt.subplots()
            if shelter == 'Shelter':
                line = ax.plot(event_time, event_area, color="blue", marker="o")
                ax.set_ylabel("Area")
                ax.set_ylim([0, max(event_area) * 1.2])
                max_area_unit = math.ceil(max(event_area) / 10)
                area_digit_num = len(str(max_area_unit)) - 1
                area_digit = math.ceil(max_area_unit / math.pow(10, area_digit_num)) * math.pow(10, area_digit_num)
                ax.yaxis.set_major_locator(ticker.MultipleLocator(area_digit))
            else:
                line = ax.plot(event_time, event_area, color="blue", marker="o")
                ax.set_ylabel("Ratio")
                ax.set_ylim([0, shelter_area * 1.05])
                area_unit = math.ceil(shelter_area / 10)
                ax.yaxis.set_major_locator(ticker.MultipleLocator(area_unit))

            ax.set_title("{0} occupied area".format(shelter), fontsize=13, fontweight="bold")
            ax.set_xlabel("Time")

            filepath = save_path_shelter + '/{0}.png'.format(shelter)
            plt.savefig(filepath, dpi=600, transparent=True)
            # plt.show()
            print("### {0} ###".format(shelter))


if __name__ == "__main__":
    #with open(sys.argv[1], 'r') as f:
    with open('./AAAA/Result/result_path.json', 'r') as f:
        result_path = json.load(f)

    event_tracer = pd.read_csv(result_path['event_tracer'])

    with open(result_path['input_path'], 'r') as f:
        input_data = json.load(f)

    with open('./AAAA/Input/network_edge.json', 'r') as f:
        network_road = json.load(f)

    tp_list = result_path['tp_list']

    preproc_data_path = input_data['default_input'] + 'Layout_data.json'
    with open('./AAAA/Input/Layout_data.json', 'r') as f:
        preproc_data = json.load(f)

    with open('./AAAA/Result/TP.json', 'r') as f:
        tp_info = json.load(f)

    start_date_time = pd.to_datetime(preproc_data['simulation_initial_date'], format='%Y-%m-%d')
    finish_date_time = pd.to_datetime(preproc_data['simulation_finish_date'], format='%Y-%m-%d')
    post_range_days = (finish_date_time - start_date_time).days + 1
    # road_dict = road_usage(event_tracer, network_road, tp_list, post_range_days)

    tp_dict = tp_index(event_tracer, tp_info, post_range_days, start_date_time, finish_date_time, input_data['default_result'])

    columns = pd.MultiIndex.from_product([[tp_name for tp_name in tp_list], ['Load', 'Distance']])
    tp_df = pd.DataFrame(columns=columns)
    #tp_df.index = my_list
    # for tp_name in tp_list:
    #     tp_df[(tp_name, 'Load')] = tp_dict[tp_name]['Daily.Load(avg.)']
    #     tp_df[(tp_name, 'Distance')] = tp_dict[tp_name]['Daily.Distance(avg.)']
    # date_df = pd.DataFrame()
    # date_df['Date'] = my_list
    # tp_df = pd.concat([date_df, tp_df], axis=1)
    # tp_df.to_excel('../Transporter_Index.xlsx')
    # print(0)
    # stock_capacity = pd.read_excel('./data/Stockyard_area.xlsx')
    # calculate_stock_occupied_area(input_data['default_result'], event_tracer, input_data, stock_capacity)
    tp_tot = dict()
    for tp_name in tp_dict.keys():
        tp_tot[tp_name] = dict()
        for tp_key in tp_dict[tp_name].keys():
            if tp_key[:3] == "Tot":
                tp_tot[tp_name][tp_key] = tp_dict[tp_name][tp_key]

    # road_tot = dict()
    # for object_id in road_dict.keys()6
    #     road_tot[object_id] = dict()
    #     for road_key in road_dict[object_id].keys():
    #         if road_key[:3] == "Tot":
    #             road_tot[object_id][road_key] = road_dict[object_id][road_key]

    # dhl
    # road_df = pd.DataFrame(road_tot)
    # road_df = road_df.transpose()
    # road_df.to_excel(input_data['default_result'] + "Road_post.xlsx")
    print(0)
    # calculate_painting_occupied_area(input_data['default_result'], event_tracer, input_data, process_capacity)
    # calculate_shelter_occupied_area(input_data['default_result'], event_tracer, input_data, process_capacity)

