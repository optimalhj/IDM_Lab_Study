import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from collections import deque
import random
import math
from copy import deepcopy

from dataset import find_dataset
from olds.Predictive_Mobile_Refueling_for_Agricultural_Machines import InitialStudyRegion

am_additional = "corn_harvestor_"

class CentralRequestDispatcher(nn.Module):
    def __init__(self, in_dim_crd, hidden1_dim_crd, hidden2_dim_crd, hidden3_dim_crd, hidden4_dim_crd, out_dim_crd):
        super(CentralRequestDispatcher, self).__init__()
        self.layer1 = nn.Linear(in_dim_crd, hidden1_dim_crd)
        self.layer2 = nn.Linear(hidden1_dim_crd, hidden2_dim_crd)
        self.layer3 = nn.Linear(hidden2_dim_crd, hidden3_dim_crd)
        self.layer4 = nn.Linear(hidden3_dim_crd, hidden4_dim_crd)
        self.layer5 = nn.Linear(hidden4_dim_crd, out_dim_crd)

    def forward(self, x):
        x = self.layer1(x)
        x = F.relu(x)
        x = self.layer2(x)
        x = F.relu(x)
        x = self.layer3(x)
        x = F.relu(x)
        x = self.layer4(x)
        x = F.relu(x)
        x = self.layer5(x)
        x = x.t().squeeze()
        x = F.softmax(x, dim=0)
        return x

class TankerRepositionScheduler(nn.Module):
    def __init__(self, in_dim_trs, embed_dim_trs, num_heads_dim_trs, hidden1_dim_trs, hidden2_dim_trs, out_dim_trs, w_d):
        super(TankerRepositionScheduler, self).__init__()
        self.layer1 = nn.Linear(in_dim_trs, embed_dim_trs)
        self.layer2 = nn.MultiheadAttention(embed_dim_trs, num_heads_dim_trs, batch_first=True)
        self.layer3 = nn.Linear(embed_dim_trs, hidden1_dim_trs)

        self.layer4 = nn.Linear(1, hidden2_dim_trs)
        self.layer5 = nn.Linear(hidden2_dim_trs, 1)

        self.w_d = w_d
    def forward(self, x):
        x = self.layer1(x)
        x = F.relu(x)
        x, _ = self.layer2(x, x, x)
        x = torch.mean(x, dim=0, keepdim=True)
        x = self.layer3(x)
        length = torch.sum(torch.abs(x),dim=1).unsqueeze(0).t()
        length = self.layer4(length)
        length = F.relu(length)
        length = self.layer5(length)
        x = torch.concatenate([x @ torch.tensor([[-1, 0], [0, 1], [1, 0], [0, -1]], dtype=torch.float).t(), length], dim=1)
        x = F.softmax(x, dim=1)
        return x

class ReplayMemory:
    def __init__(self, max_len, sample_size):
        self.memory = deque(maxlen=max_len)
        self.sample_size = sample_size
    def add_buffer(self, buffer):
        self.memory.append(buffer)
    def sample(self):
        s_lst, a_lst, r_lst, s_prime_lst = [], [], [], []
        for idx in random.sample(list(range(len(self.memory))), min(len(self.memory), self.sample_size)):
            s, a, r, s_prime = self.memory[idx]
            s_lst.append(s)
            a_lst.append(a)
            r_lst.append(r)
            s_prime_lst.append(s_prime)
        return torch.tensor(s_lst, dtype=torch.float), torch.tensor(a_lst), torch.tensor(r_lst, dtype=torch.float), torch.tensor(s_prime_lst, dtype=torch.float)

def crd_transformer_encoder(rts, ams, t):
    entire_state = []
    for rt in rts:
        rt_id = [int(rt.replace("rt", ""))]
        current_location = rts[rt].location
        assignment_state = [rts[rt].assignment_state]
        if assignment_state[0]: intended_destination = rts[rt].destination
        else: intended_destination = current_location
        rt_t = rt_id + current_location + assignment_state + intended_destination

        for am in ams:
            am_id = [int(am.replace(am_additional, ""))]
            current_location = [int(loc) for loc in ams[am].location()]
            historical_record = [ams[am].accumulated_working_time, ams[am].last_refueling_time, ams[am].refueling_amount]
            request_state = [ams[am].request]
            am_t = am_id + current_location + historical_record + request_state

            total_path = abs(rts[rt].location[0] - int(ams[am].location()[0])) + abs(rts[rt].location[1] - int(ams[am].location()[1]))
            extra_path = 0
            mi_t = [total_path, extra_path]
            batch = rt_t + am_t + mi_t + [t]
            entire_state.append(batch)
    return entire_state

def tks_transformer_encoder(rts, ams, t):
    entire_state = []

    assignment_state = [rts.assignment_state]
    if assignment_state[0]: intended_destination = rts.destination
    else: intended_destination = [0, 0]
    ot_t = assignment_state + intended_destination

    x, y = rts.location
    for am in ams:
        am_id = [int(am.replace(am_additional, ""))]
        relative_location = [int(ams[am].location()[0]) - x, int(ams[am].location()[1]) - y]
        historical_record = [ams[am].accumulated_working_time, ams[am].last_refueling_time, ams[am].refueling_amount]
        request_state = [ams[am].request]
        am_t_prime = am_id + relative_location + historical_record + request_state

        batch = ot_t + am_t_prime + [t]
        entire_state.append(batch)
    return entire_state

def assign_rt_am(rt, am, rts, ams, study_region, t, refueling_list):
    contact = rts.crd_move(ams, study_region=study_region)
    print(f"Contact:{contact}", end="")
    if contact and (rt, am) not in refueling_list:
        refueling_list.append((rt, am))
        print(tuple(rts.location), end="")

def refuel_process(rts, ams,t, refueling_list):
    done_list = []
    for (rt, am) in refueling_list:
        done = ams[am].refuel(rts[rt], t)
        print(f"{rt} -- {am} : {done}({ams[am].fuel}/{ams[am].max_fuel}),Refueled:{rts[rt].charging_rate}")
        if done:
            rts[rt].stop_assign(contact=True)
            ams[am].refueling = False
            done_list.append((rt, am))
    for assign_set in done_list:
        refueling_list.remove(assign_set)

def calculate_distance(location1, location2):
    (x1, y1), (x2, y2) = location1, location2
    return math.exp(abs(x1 - x2) + abs(y1 - y2))

def predictive_mobile_refuel(rts, ams_total, study_region, params, max_day):
    crd = CentralRequestDispatcher(params["in_dim_crd"], params["hidden1_dim_crd"], params["hidden2_dim_crd"], params["hidden3_dim_crd"], params["hidden4_dim_crd"], params["out_dim_crd"])
    crd_target = deepcopy(crd)
    trs = {rt: TankerRepositionScheduler(params["in_dim_trs"], params["embed_dim_trs"], params["num_heads_dim_trs"], params["hidden1_dim_trs"], params["hidden2_dim_trs"], params["out_dim_trs"], params["w_d"]) for rt in rts.keys()}
    trs_target = deepcopy(trs)
    crd_target.load_state_dict(crd.state_dict())
    crd_target.eval()
    for rt in rts.keys():
        trs_target[rt].load_state_dict(trs[rt].state_dict())
        trs_target[rt].eval()
    crd_optimizer, crd_memory = optim.Adam(crd.parameters(), lr=params["crd_lr"]), ReplayMemory(max_len=params["max_len_crd"], sample_size=params["mini_batch_crd"])
    trs_optimizer, trs_memory = {}, {}
    for rt in rts.keys():
        trs_optimizer[rt], trs_memory[rt] = optim.Adam(trs[rt].parameters(), lr=params["trs_lr"]), ReplayMemory(max_len=params["max_len_trs"], sample_size=params["mini_batch_trs"])
    print("\n----------Start----------")
    initial_study_region = deepcopy(study_region)

    for epoch in range(1, max_day + 1):
        ams = ams_total[epoch]
        for rt in rts.keys():
            print(f"{rt} : {rts[rt].location}")
        print()
        for am in ams.keys():
            print(f"{am} : {ams[am].location()}")

        refueling_list = []
        for t in range(1, params["time_period"] + 1):
            print(f"\n---------- Time : {t:2} ----------")
            # print("Now Refueling :", refueling_list)
            requests = []
            print("Moving Agricultural Machines")
            for am in [am for am in ams if not ams[am].refueling]:
                print("\t", am)
                ams[am].move(study_region_idx=study_region)
                if ams[am].request >= 0:
                    requests.append(am)
            able_rts = [rt for rt in rts.keys() if not rts[rt].refueling]

            print("Able_rts :", able_rts)
            print("Requests :", requests)

            for am in requests:
                print(am, ":", ams[am].request, end="   ")

            print("\n\nPaired :")
            while len(able_rts) and len(requests):
                entire_state_assign = crd_transformer_encoder({rt: rts[rt] for rt in able_rts}, {am: ams[am] for am in requests}, t)
                state_tensor = torch.tensor(entire_state_assign, dtype=torch.float)
                # print(state_tensor)
                with torch.no_grad():
                    q_result = crd(state_tensor)
                    action = q_result.argmax().item()
                # print(q_result, "-->", action)
                chosen_rt = f"rt{entire_state_assign[action][0]}"
                chosen_am = am_additional + f"{entire_state_assign[action][6]}"
                print(f"{chosen_rt}{tuple(rts[chosen_rt].location)} -- {chosen_am}{tuple(ams[chosen_am].location())}", end="  :  ")
                able_rts.remove(chosen_rt)
                requests.remove(chosen_am)
                assign_rt_am(chosen_rt, chosen_am, rts[chosen_rt], ams[chosen_am], study_region, t, refueling_list)
                print()

            print("\nCharging State :")
            refuel_process(rts, ams, t, refueling_list)
            print()

            minus1_requests = (am for am in ams.keys() if ams[am].request == -1 and ams[am].location != ('0', '0'))
            for rt in able_rts:
                p_t_env_rt = params["w_s"] * rts[rt].total_fuel_supply - params["w_c"] * rts[rt].moving_cost - params["w_waiting"] * sum((ams[am].request + 1) for am in ams.keys())
                ams_potential_energy_prior = {am: math.exp(-params["w_d"] * (abs(int(ams[am].location()[0]) - rts[rt].location[0]) + abs(int(ams[am].location()[1]) - rts[rt].location[1]))) for am in minus1_requests}
                potential_energy_prior = sum(ams_potential_energy_prior.values())
                entire_state_unassign = tks_transformer_encoder(rts[rt], ams, t)
                state_tensor = torch.tensor(entire_state_unassign, dtype=torch.float)
                with torch.no_grad():
                    q_result = trs[rt](state_tensor)
                    action = q_result.argmax().item()
                rts[rt].tks_move(action=action, study_region=study_region)
                ams_potential_energy_next = {am: math.exp(-params["w_d"] * (abs(int(ams[am].location()[0]) - rts[rt].location[0]) + abs(int(ams[am].location()[1]) - rts[rt].location[1]))) for am in minus1_requests}
                potential_energy_next = sum(ams_potential_energy_next.values())

                r_t_pe_rt = potential_energy_next - potential_energy_prior
                reward_t_r_rt = p_t_env_rt + params["w_r"] * r_t_pe_rt
                buffer = (entire_state_unassign, action, reward_t_r_rt, tks_transformer_encoder(rts[rt], ams, t))
                trs_memory[rt].add_buffer(buffer)

                if len(trs_memory[rt].memory) == params["max_len_trs"]:
                    s_batch, a_batch, r_batch, s_prime_batch = trs_memory[rt].sample()
                    with torch.no_grad():
                        max_q_prime = trs_target[rt](s_prime_batch).max(1)[0].unsqueeze(1)
                        target = r_batch + params["gamma"] * max_q_prime
                    q_a = trs[rt](s_batch).gather(1, a_batch)
                    log_probs = torch.log(q_a + 1e-8)

                    loss = -torch.sum(log_probs, target)
                    trs_optimizer[rt].zero_grad()
                    loss.backward()
                    trs_optimizer[rt].step()

                if t % 5 == 0:
                    trs_target[rt].load_state_dict(trs[rt].state_dict())

            print("\nMoved to :")
            for rt in rts.keys():
                print(f"{rt} : {rts[rt].location}")
            print()
            for am in ams.keys():
                print(f"{am} : {ams[am].location()}, {ams[am].fuel}({round(ams[am].max_fuel * ams[am].request_threshold, 2)})/{ams[am].max_fuel}")
            print()
            study_region = deepcopy(initial_study_region)
    return study_region

class RT:
    def __init__(self, width, length, platform, v_in, v_out, charging_rate):
        self.width = width
        self.length = length
        self.location = list(platform).copy()
        self.v_in = v_in
        self.v_out = v_out
        self.assignment_state = 0
        self.destination = None
        self.charging_rate = charging_rate
        self.refueling = False

        self.total_fuel_supply = 0
        self.moving_cost = 0

    def crd_move(self, am, study_region):
        self.assignment_state = 1
        self.destination = [int(loc) for loc in am.location()]

        if self.location == self.destination:
            self.refueling = True
            am.refueling = True
            am.request = -1
            return True

        prior_location = deepcopy(self.location)
        side_direction = self.destination[0] - self.location[0]
        side_direction = min(side_direction, self.v_in if study_region[self.location[0]][self.location[1]] == 0 else self.v_out) if side_direction != 0 else 0
        front_back_direction = self.destination[1] - self.location[1]
        front_back_direction = min(front_back_direction, self.v_in if study_region[self.location[0]][self.location[1]] == 0 else self.v_out) if front_back_direction != 0 else 0
        candidate_list, priority_list = [], []
        if side_direction:
            candidate_list.append([self.location[0] + side_direction, self.location[1]])
        if front_back_direction:
            candidate_list.append([self.location[0], self.location[1] + front_back_direction])

        for x, y in candidate_list:
            if study_region[x][y] != 1:
                priority_list.append((x, y))

        if len(priority_list):
            self.location = list(random.sample(priority_list, 1)[0])
        else:
            if len(candidate_list):
                if study_region[self.location[0]][self.location[1]] != 1:
                    self.location = list(random.sample(candidate_list, 1)[0])
        self.moving_cost += 0.5 * (abs(self.location[0] - prior_location[0]) + abs(self.location[1] - prior_location[1]))
        return False

    def stop_assign(self, contact=False):
        self.assignment_state = 0
        self.destination = None
        if contact: self.refueling = False

    def tks_move(self, action, study_region, remain=0):
        if action == 0 and self.location[0] != 1:
            self.location[0] -= 1
        elif action == 1 and self.location[1] != self.length:
            self.location[1] += 1
        elif action == 2 and self.location[0] != self.width:
            self.location[0] += 1
        elif action == 3 and self.location[1] != 1:
            self.location[1] -= 1
        else: pass

class AM:
    def __init__(self, records, request_mean, request_std, fuel_mean, fuel_std):
        self.records = [tuple(record.split(";")) for record in records]

        self.fuel = random.normalvariate(fuel_mean, fuel_std)
        self.max_fuel = self.fuel
        self.request_threshold = random.normalvariate(request_mean, request_std)

        self.loc_time = 0
        self.request = -1
        self.w_waiting_st = 0
        self.accumulated_working_time = 0
        self.last_refueling_time = 0
        self.refueling_amount = 0
        self.refueling = False

    def location(self): return self.records[self.loc_time]

    def move(self, study_region_idx):
        if self.location() == ('0', '0') or self.refueling:
            return

        if self.fuel > 0:
            if study_region_idx[int(self.location()[0])][int(self.location()[1])] == 1:
                study_region_idx[int(self.location()[0])][int(self.location()[1])] = 0
            self.loc_time += 1
            self.fuel = max(0, self.fuel - 2)
            if study_region_idx:
                self.accumulated_working_time += 1

        if self.max_fuel * self.request_threshold >= self.fuel:
            self.request += 1

    def refuel(self, rt, t):
        prior_fuel = self.fuel
        self.fuel = min(self.max_fuel, self.fuel + rt.charging_rate)
        self.refueling_amount += (self.fuel - prior_fuel)
        rt.total_fuel_supply += (self.fuel - prior_fuel)
        if self.fuel == self.max_fuel:
            self.last_refueling_time = t
            w_waiting = self.last_refueling_time - self.w_waiting_st
            self.w_waiting_st = 0
            return w_waiting
        else: return False


def start(refueling_tankers, study_region, platform, params1, params2, csv_path):

    width = max(study_region.keys())
    length = max(study_region[width].keys())
    rts, ams, max_day= {}, {}, 0

    for rt in refueling_tankers:
        v_in, v_out, charging_rate = refueling_tankers[rt]
        rts[rt] = RT(width=width, length=length, platform=platform, v_in=v_in, v_out=v_out, charging_rate=charging_rate)

    import csv
    with open(csv_path, "r", encoding="utf-8") as f:
        for machine_id, day, records in csv.reader(f):
            if machine_id == "machine_id": continue
            day = int(day)
            if day not in ams: ams[day] = {}
            ams[day][machine_id] = AM(records.split("|"), params1["request_mean"], params1["request_std"], params1["fuel_mean"], params1["fuel_std"])
            if max_day < day: max_day = day
    return predictive_mobile_refuel(rts, ams, study_region, params2, max_day)

def main():

    dispatch_training = True
    reposition_training = False

    data_dir = "C:\\Users\\USER\\Documents\\MobRef_GitHub\\data"
    output_dir = ".\\data"
    row_nums = 450
    col_nums = 550
    choose_machines = [0]  # 0-5: corn, 6: paddy, 7-11: wheat1
    num_am_day = 4

    saved_path, range_info = find_dataset(data_dir, output_dir, row_nums, col_nums, choose_machines, num_am_day)

    platform_x = 176
    platform_y = 310
    platform = (max(1, min(platform_x, row_nums)), max(1, min(platform_y, col_nums)))

    min_rt, max_rt = 2, 4
    request_mean = 0.5
    request_std = 0.1
    fuel_mean = 40
    fuel_std = 5

    working_areas = [  # MIN_LAT, MAX_LAT, MIN_LNG, MAX_LNG
        (36.04635058, 36.06342458, 116.14499324, 116.17069701),
        (36.03839537, 36.14855579, 116.57486009, 116.62898196),
        (35.89408831, 35.98541373, 116.74336870, 116.80484081),
        (35.94852120, 36.04374426, 117.09726074, 117.20133489),
        (35.96993748, 35.99374381, 117.02397783, 117.04133797),
        (35.80146604, 35.81994942, 117.13927499, 117.17214827),
        (35.83013730, 35.91009813, 116.43981722, 116.56369568),
        (35.84135307, 35.90211380, 116.23802495, 116.34077893),
        (35.46585266, 35.49610145, 116.91805657, 116.94853584)]

    params1 = {"request_mean": request_mean, "request_std": request_std, "fuel_mean": fuel_mean, "fuel_std": fuel_std}
    params2 = {"epoch": 5, "w_s": 0.8, "w_c": 0.6, "w_waiting": 0.3, "w_d": 0.4, "w_r": 0.6, "time_period": 200,
              "in_dim_crd": 16, "hidden1_dim_crd": 64, "hidden2_dim_crd": 32, "hidden3_dim_crd": 16, "hidden4_dim_crd": 8, "out_dim_crd": 1,
              "in_dim_trs": 11, "embed_dim_trs": 16, "num_heads_dim_trs": 16, "hidden1_dim_trs": 2, "hidden2_dim_trs": 4, "out_dim_trs": 5,
              "max_len_crd": 100, "batch_size_crd": 50, "mini_batch_crd": 30, "crd_lr": 0.05, "gamma_crd": 0.05,
              "max_len_trs": 100, "batch_size_trs": 50, "mini_batch_trs": 30, "trs_lr": 0.05, "gamma_trs": 0.05}

    refueling_tankers = {f"rt{i+1}": [random.randint(1, 3), random.randint(3, 5), random.randint(2, 4)] for i in range(random.randint(min_rt, max_rt))}
    study_region = {x: {y: 0 for y in range(1, col_nums + 1)} for x in range(1, row_nums + 1)}

    for min_lat, max_lat, min_lng, max_lng in ((min_lat, max_lat, min_lng, max_lng) for min_lat, max_lat, min_lng, max_lng in working_areas if range_info["lat_min"] <= min_lat and max_lat <= range_info["lat_max"] and range_info["lng_min"] <= min_lng and max_lng <= range_info["lng_max"]):
        lat_scale = max(range_info["lat_max"] - range_info["lat_min"], 1e-9) / row_nums
        lng_scale = max(range_info["lng_max"] - range_info["lng_min"], 1e-9) / col_nums
        min_row = (min_lat - range_info["lat_min"]) // lat_scale + 1
        min_col = (min_lng - range_info["lng_min"]) // lng_scale + 1
        max_row = (max_lat - range_info["lat_min"]) // lat_scale + 1
        max_col = (max_lng - range_info["lng_min"]) // lng_scale + 1
        for row in range(int(min_row), int(max_row) + 1):
            for col in range(int(min_col), int(max_col) + 1):
                study_region[col][row] = 1

    region = InitialStudyRegion(row_nums, col_nums)

    using_csv = "train" if dispatch_training or reposition_training else "test"
    start(refueling_tankers, study_region, platform, params1, params2, saved_path / f"{using_csv}.csv")

if __name__ == '__main__':
    main()