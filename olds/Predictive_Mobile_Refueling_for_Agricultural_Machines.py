import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from collections import deque
import numpy as np
import random
import math
from copy import deepcopy

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
            am_id = [int(am.replace("am", ""))]
            current_location = ams[am].location
            historical_record = [ams[am].accumulated_working_time, ams[am].last_refueling_time, ams[am].refueling_amount]
            request_state = [ams[am].request]
            am_t = am_id + current_location + historical_record + request_state

            total_path = abs(rts[rt].location[0] - ams[am].location[0]) + abs(rts[rt].location[1] - ams[am].location[1])
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
        am_id = [int(am.replace("am", ""))]
        relative_location = [ams[am].location[0] - x, ams[am].location[1] - y]
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

def reward_calculator(rt, ams, w_d, geographical_distance):
    potential = 0
    # for am in ams:
    #     geographical_distance =

    return potential

def predictive_mobile_refuel(rts, ams, study_region, show_study_region, params):
    (crd, crd_target) = [CentralRequestDispatcher(params["in_dim_crd"], params["hidden1_dim_crd"], params["hidden2_dim_crd"], params["hidden3_dim_crd"], params["hidden4_dim_crd"], params["out_dim_crd"]) for _ in range(2)]
    (trs, trs_target) = [TankerRepositionScheduler(params["in_dim_trs"], params["embed_dim_trs"], params["num_heads_dim_trs"], params["hidden1_dim_trs"], params["hidden2_dim_trs"], params["out_dim_trs"], params["w_d"]) for _ in range(2)]
    crd_target.load_state_dict(crd.state_dict())
    crd_target.eval()
    trs_target.load_state_dict(trs.state_dict())
    trs_target.eval()
    crd_optimizer, crd_memory, trs_optimizer, trs_memory= optim.Adam(crd.parameters(), lr=params["crd_lr"]), ReplayMemory(max_len=params["max_len_crd"], sample_size=params["mini_batch_crd"]), optim.Adam(trs.parameters(), lr=params["trs_lr"]), ReplayMemory(max_len=params["max_len_trs"], sample_size=params["mini_batch_trs"])

    initial_study_region = deepcopy(study_region)
    print("\n----------Start----------")
    show_study_region.show(study_region)
    print()
    for rt in rts.keys():
        print(f"{rt} : {rts[rt].location}")
    print()
    for am in ams.keys():
        print(f"{am} : {ams[am].location}")

    time_period = params["time_period"]

    for i in range(1, params["epoch"] + 1):
        print()
        show_study_region.show(study_region)
        refueling_list = []
        for t in range(1, time_period + 1):
            print(f"\n---------- Time : {t:2} ----------")
            # print("Now Refueling :", refueling_list)
            requests = []
            for am in [am for am in ams if not ams[am].refueling]:
                print(f"AM : {am}({ams[am].speed})")
                ams[am].move(study_region=study_region, t=t)
                if ams[am].request >= 0:
                    requests.append(am)
                print()
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
                chosen_am = f"am{entire_state_assign[action][6]}"
                print(f"{chosen_rt}{tuple(rts[chosen_rt].location)} -- {chosen_am}{tuple(ams[chosen_am].location)}", end="  :  ")
                able_rts.remove(chosen_rt)
                requests.remove(chosen_am)
                assign_rt_am(chosen_rt, chosen_am, rts[chosen_rt], ams[chosen_am], study_region, t, refueling_list)
                print()
                # crd_memory.add_buffer([entire_state_assign, action, ])
            print("\nCharging State :")
            refuel_process(rts, ams, t, refueling_list)
            print()

            for rt in able_rts:
                entire_state_unassign = tks_transformer_encoder(rts[rt], ams, t)
                state_tensor = torch.tensor(entire_state_unassign, dtype=torch.float)
                with torch.no_grad():
                    q_result = trs(state_tensor)
                    action = q_result.argmax().item()
                rts[rt].tks_move(action=action, study_region=study_region)

            print("\nMoved to :")
            for rt in rts.keys():
                print(f"{rt} : {rts[rt].location}")
            print()
            for am in ams.keys():
                print(f"{am} : {ams[am].location} to {ams[am].destination}, {ams[am].fuel}({round(ams[am].max_fuel * ams[am].request_fuel_rate, 2)})/{ams[am].max_fuel}")
        print()
        show_study_region.show(study_region)
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
    def crd_move(self, am, study_region):
        self.assignment_state = 1
        self.destination = am.location

        left_move, waiting_count = max(self.v_in, self.v_out), 0
        while left_move:
            if self.location == self.destination:
                self.refueling = True
                am.refueling = True
                am.request = -1
                return True
            side_direction = self.destination[0] - self.location[0]
            side_direction = round(math.copysign(1, side_direction)) if side_direction != 0 else 0
            front_back_direction = self.destination[1] - self.location[1]
            front_back_direction = round(math.copysign(1, front_back_direction)) if front_back_direction != 0 else 0
            candidate_list, priority_list = [], []
            if side_direction:
                candidate_list.append([self.location[0] + side_direction, self.location[1]])
            if front_back_direction:
                candidate_list.append([self.location[0], self.location[1] + front_back_direction])

            for x, y in candidate_list:
                if study_region[x][y] not in ("F", "D"):
                    priority_list.append((x, y))

            left_move -= 1
            if len(priority_list):
                self.location = list(random.sample(priority_list, 1)[0])
            else:
                if len(candidate_list):
                    if study_region[self.location[0]][self.location[1]] not in ("F", "D"):
                        self.location = list(random.sample(candidate_list, 1)[0])
                    else:
                        decision_distance = 1 / 2 * (1 / self.v_in + 1 / self.v_out)
                        decision_bool = random.random() > decision_distance
                        if decision_bool:
                            self.location = list(random.sample(candidate_list, 1)[0])
                        else:
                            if waiting_count > decision_distance:
                                self.location = list(random.sample(candidate_list, 1)[0])
                                waiting_count = 0
                            waiting_count += 1
        return False

    def stop_assign(self, contact=False):
        self.assignment_state = 0
        self.destination = None
        if contact:
            self.refueling = False

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
    def __init__(self, width, length, platform, speed, fuel, consuming_rate, request_fuel_rate):
        self.width = width
        self.length = length
        self.platform = platform
        self.location = list(platform).copy()
        self.speed = speed
        self.fuel = fuel
        self.max_fuel = fuel
        self.consuming_rate = consuming_rate

        self.request = -1
        self.w_waiting_st = 0
        self.accumulated_working_time = 0
        self.last_refueling_time = 0
        self.refueling_amount = 0
        self.refueling = False
        self.request_fuel_rate = request_fuel_rate
        self.destination = None
    def move(self, study_region, t):

        dont_move_bool = self.location == list(self.platform).copy() and self.destination is None and "F" not in (study_region[x][y] for x in range(1, self.width + 1) for y in range(1, self.length + 1))
        if self.fuel > 0 and not dont_move_bool:
            waiting_count = 0
            for i in range(1 if study_region[self.location[0]][self.location[1]] in ("F", "D") else self.speed):
                print(f"{i + 1} th move Now Location :", self.location, f"and wanna go to {self.destination}")
                if self.destination is None:
                    candidate_destination, break1 = [], False
                    for search in range(1, self.length + self.width):
                        for delta_x in range(0, search + 1):
                            for side_direction in (-1, 1):
                                for fron_back_direction in (-1, 1):
                                    x, y = int(self.location[0] + side_direction * delta_x), int(self.location[1] + fron_back_direction * (search - delta_x))
                                    if 1 <= x <= self.width and 1 <= y <= self.length and study_region[x][y] == "F" and (x, y) not in candidate_destination:
                                        print(f"({search})  Delta x :", side_direction * delta_x, "  /  Delta_y :", fron_back_direction * (search - delta_x), "    ---->>>>    ", x, y)
                                        candidate_destination.append((x, y))
                                        break1 = True
                        if break1:
                            break
                    if not break1:
                        self.destination = list(self.platform).copy()
                    else:
                        self.destination = list(random.sample(candidate_destination, 1)[0])

                candidate_direction, priority_direction = [], []
                delta_x, delta_y = self.destination[0] - self.location[0], self.destination[1] - self.location[1]
                if delta_x != 0:
                    new_x = int(self.location[0] + np.copysign(1, delta_x))
                    candidate_direction.append([new_x, self.location[1]].copy())
                    if study_region[new_x][self.location[1]] not in ("F", "D"):
                        priority_direction.append([new_x, self.location[1]].copy())
                if delta_y != 0:
                    new_y = int(self.location[1] + np.copysign(1, delta_y))
                    candidate_direction.append([self.location[0], new_y])
                    if study_region[self.location[0]][new_y] not in ("F", "D"):
                        priority_direction.append([self.location[0], new_y])
                print("Candidates :", candidate_direction, end="  -->>  ")
                if len(priority_direction):
                    assigned = random.randint(0, len(priority_direction)-1)
                    print("Priority Assigned :", assigned, end=f"  -->>  {priority_direction[assigned]}  -->>  ")
                    assigned = priority_direction[assigned]
                    self.location = assigned
                else:
                    if len(candidate_direction):
                        if study_region[self.location[0]][self.location[1]] not in ("F", "D"):
                            assigned = random.randint(0, len(candidate_direction) - 1)
                            print("Candidate Assigned :", assigned, end=f"  -->>  {candidate_direction[assigned]}  -->>  ")
                            assigned = candidate_direction[assigned]
                            self.location = assigned
                        else:
                            decision_distance = 1 / 2 * (1 + 1 / self.speed)
                            decision_bool = random.random() > decision_distance
                            if decision_bool:
                                assigned = random.randint(0, len(candidate_direction) - 1)
                                print("Candidate Assigned :", assigned, end=f"  -->>  {candidate_direction[assigned]}  -->>  ")
                                assigned = candidate_direction[assigned]
                                self.location = assigned
                            else:
                                if waiting_count > decision_distance:
                                    assigned = random.randint(0, len(candidate_direction) - 1)
                                    print("Candidate Assigned :", assigned, end=f"  -->>  {candidate_direction[assigned].copy()}  -->>  ")
                                    assigned = candidate_direction[assigned].copy()
                                    self.location = assigned
                                    waiting_count = 0
                                else: print("But because of Boundary issue, It can't move", end="  -->>  ")
                                waiting_count += 1
                print("Moved to  :", self.location)
                if self.location == self.destination: self.destination = None
                if study_region[self.location[0]][self.location[1]] == "F":
                    study_region[self.location[0]][self.location[1]] = "D"
                    self.accumulated_working_time += 1
                print()
            self.fuel = max(0, self.fuel - self.consuming_rate)
            if self.fuel < self.max_fuel * self.request_fuel_rate: self.request += 1
        if dont_move_bool: self.request = -1
        if self.fuel == 0 and self.w_waiting_st == 0: self.w_waiting_st = t

    def refuel(self, rt, t):
        prior_fuel = self.fuel
        self.fuel = min(self.max_fuel, self.fuel + rt.charging_rate)
        self.refueling_amount += (self.fuel - prior_fuel)
        if self.fuel == self.max_fuel:
            self.last_refueling_time = t
            w_waiting = self.last_refueling_time - self.w_waiting_st
            self.w_waiting_st = 0
            return w_waiting
        else: return False

class InitialStudyRegion:
    def __init__(self, width, length, study_region):
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

def start(refueling_tankers, agricultural_machines, study_region, platform, params):
    width = max(study_region.keys())
    length = max(study_region[width].keys())
    rts, ams = {}, {}

    for rt in refueling_tankers:
        v_in, v_out, charging_rate = refueling_tankers[rt]
        rts[rt] = RT(width=width, length=length, platform=platform, v_in=v_in, v_out=v_out, charging_rate=charging_rate)
    for am in agricultural_machines:
        speed, fuel, consuming_rate, request_fuel_rate = agricultural_machines[am]
        ams[am] = AM(width=width, length=length, platform=platform, speed=speed, fuel=fuel, consuming_rate=consuming_rate, request_fuel_rate=request_fuel_rate)
    initial_study_region = InitialStudyRegion(width=width, length=length, study_region=study_region)
    return predictive_mobile_refuel(rts, ams, study_region, initial_study_region, params)

def set_load(x, y, length, width, platform, tree_ratio, max_ratio, loads):
    point, prior_direction, continuous_exception = [x, y], 4, []
    while 1:
        point_tmp = point.copy()
        able_direction = [0, 1, 2, 3]  # LEFT, UP, RIGHT, DOWN
        for exception in continuous_exception:
            if exception in able_direction: able_direction.remove(exception)
        if prior_direction in able_direction:
            able_direction.remove(prior_direction)
        if point[0] == 1 and 0 in able_direction: able_direction.remove(0)
        if point[1] == length and 1 in able_direction: able_direction.remove(1)
        if point[0] == width and 2 in able_direction: able_direction.remove(2)
        if point[1] == 1 and 3 in able_direction: able_direction.remove(3)
        if len(able_direction):
            chosen_direction = random.choice(able_direction)
            if chosen_direction == 0: point[0] -= 1
            elif chosen_direction == 1: point[1] += 1
            elif chosen_direction == 2: point[0] += 1
            else: point[1] -= 1
            new_point = tuple(point)
            if new_point in loads or new_point == platform:
                continuous_exception.append(chosen_direction)
                if len(continuous_exception) == 2: break
                point = point_tmp.copy()
                continue
            loads.append(new_point)
            if len(loads) >= max_ratio * length * width: break
            if random.random() < tree_ratio:
                loads.extend(set_load(new_point[0], new_point[1], length, width, platform, tree_ratio, max_ratio, loads))
            prior_direction, continuous_exception = (chosen_direction + 2) % 4, []
        else: break
    return loads

def main():
    min_rt, max_rt = 2, 4
    min_am, max_am = 3, 6
    width, length, tree_ratio, max_ratio = 10, 15, 0.15, 0.35
    min_request_fuel_rate, max_request_fuel_rate = 0.6, 0.8

    params = {"epoch": 5, "w_d": 0.4, "w_r": 0.6, "time_period": 300,
              "in_dim_crd": 16, "hidden1_dim_crd": 64, "hidden2_dim_crd": 32, "hidden3_dim_crd": 16, "hidden4_dim_crd": 8, "out_dim_crd": 1,
              "in_dim_trs": 11, "embed_dim_trs": 16, "num_heads_dim_trs": 16, "hidden1_dim_trs": 2, "hidden2_dim_trs": 4, "out_dim_trs": 5,
              "max_len_crd": 100, "batch_size_crd": 50, "mini_batch_crd": 30, "crd_lr": 0.05, "gamma_crd": 0.05,
              "max_len_trs": 100, "batch_size_trs": 50, "mini_batch_trs": 30, "trs_lr": 0.05, "gamma_trs": 0.05}

    refueling_tankers = {f"rt{i}": [random.randint(2, 3), random.randint(3, 5), random.randint(5, 8)] for i in range(random.randint(min_rt, max_rt))}
    agricultural_machines = {f"am{i}": [random.randint(2, 4), random.randint(120, 150), random.randint(3, 5), random.uniform(min_request_fuel_rate, max_request_fuel_rate)] for i in range(random.randint(min_am, max_am))}
    study_region = {x: {y: "F" for y in range(1, length + 1)} for x in range(1, width + 1)}

    platform = (random.randint(1, width), random.randint(1, length))
    study_region[platform[0]][platform[1]] = "P"

    loads = set_load(platform[0], platform[1], length, width, platform, tree_ratio, max_ratio, [])

    for x, y in loads:
        study_region[x][y] = "L"

    study_region = start(refueling_tankers, agricultural_machines, study_region, platform, params)

if __name__ == '__main__':
    main()