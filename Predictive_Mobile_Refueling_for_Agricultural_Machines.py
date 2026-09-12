import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.rnn import pad_sequence
import torch.optim as optim

import numpy as np
from collections import deque
import random
import math
from copy import deepcopy

from dataset import find_dataset
rt_additional = "RT"
am_additional = "AM"

class CentralRequestDispatcher(nn.Module):
    def __init__(self, in_dim_crd, hidden1_dim_crd, hidden2_dim_crd, hidden3_dim_crd, hidden4_dim_crd, out_dim_crd):
        super(CentralRequestDispatcher, self).__init__()

        self.layer1 = nn.TransformerEncoder(nn.TransformerEncoderLayer(d_model=in_dim_crd, nhead=4, dim_feedforward=64, batch_first=True), 4)
        self.layer2 = nn.Linear(in_dim_crd, out_dim_crd)

    def forward(self, x, padding_mask=None):
        x = self.layer1(x, src_key_padding_mask=padding_mask)
        x = F.relu(x)

        x = self.layer2(x)
        x = F.relu(x)
        return x

class TankerRepositionScheduler(nn.Module):
    def __init__(self, in_dim_trs, embed_dim_trs, num_heads_dim_trs, hidden1_dim_trs, hidden2_dim_trs, out_dim_trs):
        super(TankerRepositionScheduler, self).__init__()
        self.layer0 = nn.TransformerEncoder(nn.TransformerEncoderLayer(d_model=in_dim_trs, nhead=1, dim_feedforward=64, batch_first=True), 4)
        self.layer1 = nn.Linear(in_dim_trs, embed_dim_trs)
        self.layer2 = nn.MultiheadAttention(embed_dim_trs, num_heads_dim_trs, batch_first=True)
        self.layer3 = nn.Linear(embed_dim_trs, hidden1_dim_trs)

        self.layer4 = nn.Linear(hidden1_dim_trs, 1 + out_dim_trs)

    def forward(self, x, padding_mask=None):
        x = self.layer0(x, src_key_padding_mask=padding_mask)
        x = F.relu(x)
        x = self.layer1(x)
        x = F.relu(x)
        x, _ = self.layer2(x, x, x)

        x = torch.mean(x, dim=1, keepdim=True)

        x = self.layer3(x)
        x = F.relu(x)

        x = self.layer4(x)
        x = F.relu(x)
        x = x.squeeze(0)
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
        return s_lst, a_lst, r_lst, s_prime_lst
class InitialStudyRegion:
    def __init__(self, width, length):
        self.width = width
        self.length = length
        self.width_format, self.length_format, decent1, decent2 = 2, 1, 10, 10
        while 1:
            if self.width / decent1 >= 1:
                self.width_format += 1
                decent1 *= 10
            else: break
        while 1:
            if self.length / decent2 >= 1:
                self.length_format += 1
                decent2 *= 10
            else: break
    def show(self, study_region):
        for y in range(self.length, 0, -1):
            print(f"{y :>{self.length_format}} : ", end="")
            for x in range(1, self.width + 1):
                print(f"{study_region[x][y] : >{self.width_format}}", end=" ")
            print()
        print(" " * (self.length_format + 3) + "".join([f"{j:>{self.width_format}} " for j in range(1, self.width + 1)]))

def calculate_distance(location1, location2):
    (x1, y1), (x2, y2) = location1, location2
    return (abs(x1 - x2) ** 2 + abs(y1 - y2) ** 2) ** 0.5

def build_crd_state(rts, ams, t, max_time):
    t += 1

    entire_state = []
    for rt in rts:
        space = (rts[rt].width, rts[rt].length)
        rt_id = [int(rt.replace(rt_additional, ""))]
        current_location = [(loc - 1) / (max_space - 1) for loc, max_space in zip(rts[rt].location, space)]
        assignment_state = [rts[rt].assignment_state]
        if assignment_state[0]: intended_destination = [(loc - 1) / (max_space - 1) for loc, max_space in zip(rts[rt].destination, space)]
        else: intended_destination = current_location
        rt_t = rt_id + current_location + assignment_state + intended_destination

        for am in ams:
            am_id = [int(am.replace(am_additional, ""))]
            current_location = [(loc - 1) / (max_space - 1) for loc, max_space in zip(ams[am].location(t-1), space)]
            historical_record = [ams[am].accumulated_working_time / t, ams[am].last_refueling_time / t, ams[am].refueling_amount / ams[am].max_fuel]
            request_state = [ams[am].request]
            am_t = am_id + current_location + historical_record + request_state

            total_path = (abs(rts[rt].location[0] - ams[am].location(t-1)[0]) + abs(rts[rt].location[1] - ams[am].location(t-1)[1])) / (sum(space) - 2)
            extra_path = 0
            mi_t = [total_path, extra_path]
            batch = rt_t + am_t + mi_t + [t / max_time]
            entire_state.append(batch)
    return entire_state

def build_trs_state(rts, ams, t, max_time):
    space, t = (rts.width, rts.length), t + 1
    entire_state = []

    assignment_state = [rts.assignment_state]
    if assignment_state[0]: intended_destination = rts.destination
    else: intended_destination = rts.location
    ot_t = assignment_state + [float((loc - 1) / (max_space - 1)) for loc, max_space in zip(intended_destination, space)]
    for am in ams.keys():
        am_id = [int(am.replace(am_additional, ""))]
        relative_location = [float((am_loc - rt_loc) / (max_space - 1)) for am_loc, rt_loc, max_space in zip(ams[am].location(t-1), rts.location, space)]
        historical_record = [ams[am].accumulated_working_time / t, ams[am].last_refueling_time / t, ams[am].refueling_amount / ams[am].max_fuel]
        request_state = [ams[am].request]
        am_t_prime = am_id + relative_location + historical_record + request_state

        batch = ot_t + am_t_prime + [t / max_time]
        entire_state.append(batch)
    return entire_state

def build_tensor_state(crd_state):
    return torch.Tensor(crd_state).unsqueeze(0)

def build_tensor_state_batch(state_list):
    tensors = [torch.as_tensor(state, dtype=torch.float32) for state in state_list]
    lengths = torch.tensor([state.shape[0] for state in tensors], dtype=torch.long)
    states = pad_sequence(tensors, batch_first=True, padding_value=0.0)

    max_len = states.size(1)
    padding_mask = (torch.arange(max_len).unsqueeze(0) >= lengths.unsqueeze(1))
    return states, padding_mask

def regulated_profit(w_s, w_c, rts, w_waiting, online_ams):
    return w_s * sum(rts[rt].total_fuel_supply for rt in rts.keys()) - w_c * sum(rts[rt].moving_cost for rt in rts.keys()) - w_waiting * sum(online_ams[am].w_waiting for am in online_ams)

def trs_energy_calculator(w_d, rts_location, ams_locations):
    potential_energy = 0
    for ams_x, ams_y in ams_locations:
        potential_energy += math.exp(-w_d * abs(ams_x + ams_y - rts_location[0] - rts_location[1]))
    return potential_energy

def predictive_mobile_refuel(rts, ams_total, study_region, set_region, params, max_group_id):
    crd = CentralRequestDispatcher(params["in_dim_crd"], params["hidden1_dim_crd"], params["hidden2_dim_crd"], params["hidden3_dim_crd"], params["hidden4_dim_crd"], params["out_dim_crd"])
    crd_target = deepcopy(crd)
    trs = {rt: TankerRepositionScheduler(params["in_dim_trs"], params["embed_dim_trs"], params["num_heads_dim_trs"], params["hidden1_dim_trs"], params["hidden2_dim_trs"], params["out_dim_trs"]) for rt in rts.keys()}
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

    for crd_epoch in range(params["crd_epoch"]):
        print(f"--------- EPISODE {crd_epoch + 1} ---------")
        i = 1
        for group_id in range(1, max_group_id + 1):
            ams = ams_total[group_id]

            system_refueling = []
            for t in range(params["time_step"]):
                print(f"Time : {t + 1}")

                online_ams = {am: ams[am] for am in ams.keys() if ams[am].location(t) != (0, 0)}
                if not len(online_ams): continue

                print("Online AMS")
                for am in online_ams.keys():
                    print(f"\t{am} : {online_ams[am].location(t)}  /  Fuel: {online_ams[am].fuel}/{online_ams[am].max_fuel}")
                print()

                able_rts = []
                for rt in rts:
                    if not rts[rt].refueling:
                        able_rts.append(rt)
                print(f"AbleRTs : {able_rts}")

                request_ams = []
                for am in online_ams.keys():
                    online_ams[am].step()
                    if online_ams[am].request >= 0:
                        request_ams.append(am)
                print(f"Request : {request_ams}")


                if len(system_refueling):
                    print("Refueling")
                    for pair in system_refueling:
                        print(pair, f"charging : {online_ams[pair[1]].fuel}/{online_ams[pair[1]].max_fuel}")
                    print()

                if len(request_ams) and len(able_rts): print("Assignment")
                while len(request_ams) and len(able_rts):
                    crd_state = build_crd_state({rt: rts[rt] for rt in able_rts}, {am: online_ams[am] for am in request_ams}, t, params["time_step"])
                    for state in crd_state:
                        print("\t", state)

                    if i < 0.88:
                        crd_action = random.randint(0, len(crd_state) - 1)
                    else:
                        crd_state_tensor = build_tensor_state(crd_state)
                        with torch.no_grad():
                            crd_action = crd(crd_state_tensor).argmax().item()
                    i *= 0.99
                    crd_best_action = crd_state[crd_action]
                    assigned_rt, assigned_am = f"{rt_additional}{crd_best_action[0]}", f"{am_additional}{crd_best_action[6]}"

                    print(f"{assigned_rt}{tuple(rts[assigned_rt].location)} <-> {assigned_am}({online_ams[assigned_am].location(t)})")

                    assign_rt, assign_am = rts[f"{rt_additional}{crd_best_action[0]}"], online_ams[f"{am_additional}{crd_best_action[6]}"]
                    assign_rt.assignment_state = 1
                    assign_rt.destination = list(assign_am.location(t))
                    assign_rt.moving_cost += 0.05

                    if assign_rt.crd_move(study_region=study_region):
                        pair = (assigned_rt, assigned_am)
                        if pair not in system_refueling:
                            system_refueling.append(pair)
                        assign_rt.refueling = True
                        assign_am.refueling = True
                        assign_am.request = -1
                        online_ams[assigned_am].w_waiting = 0

                    crd_prime_state = build_crd_state({rt: rts[rt] for rt in able_rts}, {am: online_ams[am] for am in request_ams}, t, params["time_step"])

                    crd_reward = regulated_profit(params["w_s"], params["w_c"], rts, params["w_waiting"], online_ams)
                    buffer = crd_state, crd_action, crd_reward, crd_prime_state
                    crd_memory.add_buffer(buffer)

                    request_ams.remove(assigned_am)
                    able_rts.remove(assigned_rt)

                if len(crd_memory.memory) >= params["batch_size_crd"]:
                    s_list, a_list, r_list, s_prime_list = crd_memory.sample()

                    (s_batch, s_padding_mask), (s_prime_batch, s_prime_padding_mask) = [build_tensor_state_batch(state_list) for state_list in (s_list, s_prime_list)]
                    a_batch, r_batch = torch.tensor(a_list, dtype=torch.int32), torch.tensor(r_list, dtype=torch.int32)

                    with torch.no_grad():
                        q_primes = crd_target(s_prime_batch, padding_mask=s_prime_padding_mask).squeeze(-1)
                        q_primes = q_primes.masked_fill(s_prime_padding_mask, -torch.inf)
                        max_q_prime = q_primes.max(dim=-1).values

                        target = r_batch + params["gamma_crd"] * max_q_prime
                    q_values = crd(s_batch, padding_mask=s_padding_mask)
                    q_values = q_values.squeeze(-1)

                    q_a = q_values.gather(dim=1, index=a_batch.unsqueeze(1)).squeeze(1)
                    # q_a = crd(s_batch)[0, a_batch]
                    loss = F.smooth_l1_loss(q_a, target)
                    crd_optimizer.zero_grad()
                    loss.backward()
                    crd_optimizer.step()


                deleting_pairs = []
                for assigned_rt, assigned_am in system_refueling:
                    rts[assigned_rt].total_fuel_supply += rts[assigned_rt].charging_rate
                    online_ams[assigned_am].refueling_amount += rts[assigned_rt].charging_rate
                    online_ams[assigned_am].fuel = min(online_ams[assigned_am].fuel + rts[assigned_rt].charging_rate, online_ams[assigned_am].max_fuel)

                    if online_ams[assigned_am].fuel == online_ams[assigned_am].max_fuel:

                        rts[assigned_rt].assignment_state = 0
                        rts[assigned_rt].destination = None
                        rts[assigned_rt].refueling = False
                        online_ams[assigned_am].refueling = False
                        online_ams[assigned_am].last_refueling_time = t
                        deleting_pairs.append((assigned_rt, assigned_am))

                for pair in reversed(deleting_pairs):
                    system_refueling.remove(pair)
                print()

                if len(able_rts):
                    print("Reposition")
                    for trd_epoch in range(params["trs_epoch"]):

                        for rt in able_rts:
                            rts[rt].assignment_state,rts[rt].destination = 0, None
                            trs_state = build_trs_state(rts[rt], online_ams, t, params["time_step"] + 1)
                            trs_tensor_state = build_tensor_state(trs_state)
                            print()
                            for state in trs_state:
                                print(rt, state, end="  ->  ")
                            with torch.no_grad():
                                trs_action = trs[rt](trs_tensor_state)
                            print(trs_action)
                            print(f"->  {trs_action.argmax().item()}", end="   /   ")
                            print(f"{tuple(rts[rt].location)}", end=" -> ")
                            energy_before = trs_energy_calculator(params["w_d"], rts[rt].location, [online_ams[am].location(t) for am in online_ams if online_ams[am].request == -1])
                            rts[rt].trs_move(action=trs_action.argmax().item(), study_region=study_region)
                            energy_after = trs_energy_calculator(params["w_d"], rts[rt].location, [online_ams[am].location(t) for am in online_ams if online_ams[am].request == -1])
                            r_pei = -(energy_after - energy_before)
                            p_envi = regulated_profit(params["w_s"], params["w_c"], {rt: rts[rt]}, params["w_waiting"], online_ams)
                            reward = p_envi + params["w_r"] * r_pei
                            buffer = trs_state, trs_action.argmax().item(), reward, build_trs_state(rts[rt], online_ams, t, params["time_step"] + 1)
                            trs_memory[rt].add_buffer(buffer)
                            print(tuple(rts[rt].location))

                            if len(trs_memory[rt].memory) >= params["batch_size_trs"]:
                                s_list, a_list, r_list, s_prime_list = trs_memory[rt].sample()

                                (s_batch, s_padding_mask), (s_prime_batch, s_prime_padding_mask) = [build_tensor_state_batch(state_list) for state_list in (s_list, s_prime_list)]
                                a_batch, r_batch = torch.tensor(a_list, dtype=torch.int32), torch.tensor(r_list, dtype=torch.int32)

                                with torch.no_grad():
                                    q_primes = trs_target[rt](s_prime_batch, padding_mask=s_prime_padding_mask).squeeze(1)
                                    max_q_prime = q_primes.max(dim=-1).values
                                    target = r_batch + params["gamma_trs"] * max_q_prime
                                q_values = trs[rt](s_batch, padding_mask=s_padding_mask)
                                q_values = q_values.squeeze(1)

                                q_a = q_values.gather(dim=1, index=a_batch.unsqueeze(1)).squeeze(1)

                                loss = F.smooth_l1_loss(q_a, target)
                                crd_optimizer.zero_grad()
                                loss.backward()
                                crd_optimizer.step()

                            if trd_epoch % 3 == 0:
                                trs_target[rt].load_state_dict(trs[rt].state_dict())

                print()
                print("-" * 50)
            for rt in rts.keys(): rts[rt].initialize()
            for am in ams.keys(): ams[am].initialize()
            if crd_epoch % 4 == 0:
                crd_target.load_state_dict(crd.state_dict())
    return

class RT:
    def __init__(self, width, length, platform, v_in, v_out, charging_rate,base_directions,scaling_point):

        self.width = width
        self.length = length
        self.location = list(platform).copy()
        self.v_in = v_in
        self.v_out = v_out
        self.charging_rate = charging_rate
        self.base_directions = base_directions
        self.scaling_point = scaling_point

        self.platform = list(platform).copy()
        self.total_fuel_supply = 0
        self.moving_cost = 0

        self.assignment_state = 0
        self.destination = None
        self.refueling = False

    def initialize(self):
        self.location =self.platform.copy()
        self.total_fuel_supply = 0
        self.moving_cost = 0

        self.assignment_state = 0
        self.destination = None
        self.refueling = False

    def crd_move(self, study_region):
        first_location = self.location.copy()
        angle = math.atan2(self.destination[1] - self.location[1], self.destination[0] - self.location[0])
        vec_x, vec_y = np.array([func(angle) for func in (math.cos, math.sin)]) * self.v_out

        for _ in range(10 ** self.scaling_point):
            if [round(loc) for loc in self.location] == self.destination: return True
            x, y = self.location
            velocity_ratio = 1 if study_region[round(x)][round(y)] == 0 else self.v_in / self.v_out
            new_x, new_y = [loc + velocity_ratio * vec_loc / 10 ** self.scaling_point for loc, vec_loc in zip((x, y), (vec_x, vec_y))]

            if new_x < 1:
                new_x = 1
            elif new_x > self.width:
                new_x = self.width
            else: pass

            if new_y < 1:
                new_y = 1
            elif new_y > self.length:
                new_y = self.length
            else: pass

            self.location = [new_x, new_y]

        self.moving_cost += (abs(first_location[0] - self.location[0]) + abs(first_location[1] - self.location[1])) / (self.width + self.length)
        return False

    def trs_move(self, action, study_region):
        first_location = self.location.copy()
        if action == self.base_directions: pass
        else:
            vec_x, vec_y = np.array([func(2 * action / self.base_directions * math.pi) for func in (math.cos, math.sin)]) * self.v_out
            for _ in range(10 ** self.scaling_point):
                x, y = self.location

                if study_region[round(x)][round(y)] == 0:
                    velocity_ratio = 1
                else:
                    velocity_ratio = self.v_in / self.v_out

                new_x, new_y = [loc + velocity_ratio * vec_loc / 10 ** self.scaling_point for loc, vec_loc in zip((x,y), (vec_x, vec_y))]
                if new_x < 1:
                    new_x = 1
                elif new_x > self.width:
                    new_x = self.width
                else: pass

                if new_y < 1:
                    new_y = 1
                elif new_y > self.length:
                    new_y = self.length
                else: pass

                self.location = [new_x, new_y]
        self.location = [round(loc, self.scaling_point) for loc in self.location]
        self.moving_cost += (abs(first_location[0] - self.location[0]) + abs(first_location[1] - self.location[1])) / (self.width + self.length)

class AM:
    def __init__(self, records, request_mean, request_std, consuming, fuel_mean, fuel_std):

        self.records = [tuple(int(loc) for loc in record.split(";")) for record in records]
        self.consuming = consuming
        self.fuel = random.normalvariate(fuel_mean, fuel_std)
        self.max_fuel = self.fuel
        self.request_threshold = random.normalvariate(request_mean, request_std) * self.max_fuel

        self.request = -1
        self.w_waiting = 0
        self.accumulated_working_time = 0
        self.last_refueling_time = 0
        self.refueling_amount = 0
        self.refueling = False
        self.stopped = 0

    def location(self, t):
        return self.records[t - self.stopped]

    def initialize(self):
        self.request = -1
        self.w_waiting = 0
        self.accumulated_working_time = 0
        self.last_refueling_time = 0
        self.refueling_amount = 0
        self.refueling = False

        self.stopped = 0

    def step(self):
        if not self.refueling:
            if self.fuel > 0:
                self.accumulated_working_time += 1
                self.fuel = max(0, self.fuel - self.consuming)
            else:
                self.w_waiting += 1

            if self.fuel <= self.request_threshold:
                self.request += 1
        if self.refueling or self.fuel == 0:
            self.stopped += 1

def start(refueling_tankers, study_region, set_region, platform, params1, params2, csv_path):

    width = max(study_region.keys())
    length = max(study_region[width].keys())
    rts, ams, max_group_id = {}, {}, -1

    for rt in refueling_tankers:
        v_in, v_out, charging_rate = refueling_tankers[rt]
        rts[rt] = RT(width=width, length=length, platform=platform, v_in=v_in, v_out=v_out, charging_rate=charging_rate, base_directions=params2["out_dim_trs"], scaling_point=params2["scaling_point"])

    import csv
    with open(csv_path, "r", encoding="utf-8") as f:
        for machine_id, group_id, records in csv.reader(f):
            if machine_id == "machine_id": continue
            group_id = int(group_id)
            if group_id not in ams: ams[group_id] = {}
            ams[group_id][machine_id] = AM(records.split("|"), params1["request_mean"], params1["request_std"], params1["consuming"], params1["fuel_mean"], params1["fuel_std"])
            if max_group_id < group_id: max_group_id = group_id
    return predictive_mobile_refuel(rts, ams, study_region, set_region, params2, max_group_id)

def main():

    dispatch_training = True
    reposition_training = False

    data_dir = ""
    output_dir = ".\\data"
    row_nums = 15
    col_nums = 20
    choose_machines = [0]  # 0-5: corn, 6: paddy, 7-11: wheat1
    num_am_day = 4

    saved_path, range_info = find_dataset(data_dir, output_dir, row_nums, col_nums, choose_machines, num_am_day)

    platform_x = 7
    platform_y = 4
    platform = (max(1, min(platform_x, col_nums)), max(1, min(platform_y, row_nums)))

    min_rt, max_rt = 3, 4
    request_mean = 0.5
    request_std = 0.1
    consuming = 3
    fuel_mean = 40
    fuel_std = 5
    time_step = 140

    num_base_directions = 12
    scaling_point = 3

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

    params1 = {"request_mean": request_mean, "request_std": request_std, "consuming": consuming, "fuel_mean": fuel_mean, "fuel_std": fuel_std}
    params2 = {"crd_epoch": 3, "trs_epoch": 10, "w_s": 0.3, "w_c": 0.6, "w_waiting": 0.3, "w_d": 0.4, "w_r": 0.6, "scaling_point": scaling_point, "time_step": min(288, max(0, time_step)),
              "in_dim_crd": 16, "hidden1_dim_crd": 64, "hidden2_dim_crd": 32, "hidden3_dim_crd": 16, "hidden4_dim_crd": 8, "out_dim_crd": 1,
              "in_dim_trs": 11, "embed_dim_trs": 16, "num_heads_dim_trs": 16, "hidden1_dim_trs": 2, "hidden2_dim_trs": 4, "out_dim_trs": num_base_directions,
              "max_len_crd": 50, "batch_size_crd": 20, "mini_batch_crd": 20, "crd_lr": 0.05, "gamma_crd": 0.05,
              "max_len_trs": 100, "batch_size_trs": 50, "mini_batch_trs": 30, "trs_lr": 0.05, "gamma_trs": 0.05}

    refueling_tankers = {f"{rt_additional}{i+1}": [random.randint(8, 14), random.randint(17, 25), random.randint(2, 4)] for i in range(random.randint(min_rt, max_rt))}
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

    set_region = InitialStudyRegion(row_nums, col_nums)
    set_region.show(study_region)
    using_csv = "train" if dispatch_training or reposition_training else "test"
    start(refueling_tankers, study_region, set_region, platform, params1, params2, saved_path / f"{using_csv}.csv")

if __name__ == '__main__':
    main()