from numpy import random as rd
import mysql.connector

# Parameter Input
num_jts ,max_num_job, max_num_op, num_machines, max_time = 6, 10, 15, 10, 9
params = {"pop_size": 50, "num_of_gens": 200, "mating_pool": 100, "num_offs": 45, "s_max": 5, "T": 60, "w": 0.4, "K": 0.25}
database_input, user, password, db_name, case_database = 20, 'root', 'gh314wns!', 'cbr', 'case_database'

def select_mp(populations):
    index = list(range(params["pop_size"]))
    way_pop = rd.randint(3)

    if way_pop == 0:  # Binary tournament
        return populations[min(rd.choice(index, size=2, replace=False), key=lambda idx: populations[idx][1][0])]
    elif way_pop == 1:  # n-Size tournament
        return populations[min(rd.choice(index, size=rd.randint(3, max(4, int(params["pop_size"] / 2.5))), replace=False), key=lambda idx: populations[idx][1][0])]
    elif way_pop == 2:  # Linear ranking
        return populations[rd.choice(index, size=1, p=[2 * i / (params["pop_size"] * (params["pop_size"] + 1)) for i in range(params["pop_size"], 0, -1)])[0]]
    else: return [] # Do not reach

def correct_procedure(ini_set, seq):
    info_op = {jt : {job : {op : 0 for op in ini_set[jt]["ops"]} for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    info_job = {jt: {op: {job: 0 for job in ini_set[jt]["jobs"]} for op in ini_set[jt]["ops"]} for jt in ini_set.keys()}
    for i in range(len(seq)):
        jt, job, _ = seq[i]
        using_op = min(ini_set[jt]["ops"], key=lambda op: info_op[jt][job][op])
        info_op[jt][job][using_op] += 1
        seq[i] = (jt, using_op)
    for i in range(len(seq)):
        jt, op = seq[i]
        using_job = min(ini_set[jt]["jobs"], key=lambda job: info_job[jt][op][job])
        info_job[jt][op][using_job] += 1
        seq[i] = (jt, using_job, op)
    return seq

def objective(process, setup, ini_set, seq):
    se_process = {jt: {job: {op: [] for op in ini_set[jt]["ops"]} for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    st_job = {jt: {job: 0 for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    se_setup, ops_machine, st_machine, t_setup, p_tot, s_tot = {}, {}, {}, {}, 0, 0
    for _, _, _, m in seq:
        if m not in se_setup:
            se_setup[m] = {}
            ops_machine[m] = []
            st_machine[m] = 0
    for l in range(len(seq)):
        jt, job, op, m = seq[l]
        if len(ops_machine[m]) == 0: now = max(st_machine[m], st_job[jt][job])
        else:
            setup_time = getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}")
            now = max(st_machine[m] + setup_time, st_job[jt][job])
            while True:
                pass_count = 0
                for t in range(now - setup_time, now):
                    if t in t_setup and t_setup[t] == params["s_max"]:
                        now += 1
                        break
                    else: pass_count += 1
                if pass_count == setup_time: break

            if setup_time != 0:
                se_setup[m][l] = [now - setup_time, now]
                for t in range(se_setup[m][l][0], se_setup[m][l][1]):
                    if t not in t_setup: t_setup[t] = 1
                    else: t_setup[t] += 1
            s_tot += setup_time
        se_process[jt][job][op].append(now)
        ops_machine[m] = (jt, op)
        st_machine[m], st_job[jt][job] = [now + getattr(process, f"{jt}{op}") for _ in range(2)]
        p_tot += getattr(process, f"{jt}{op}")
        se_process[jt][job][op].append(st_machine[m])

    f_u = 0
    for jt in ini_set.keys():
        for job in ini_set[jt]["jobs"]:
            for op in ini_set[jt]["ops"]:
                if params["T"] >= se_process[jt][job][op][1]:
                    f_u += se_process[jt][job][op][1] - se_process[jt][job][op][0]
                elif se_process[jt][job][op][0] <= params["T"] < se_process[jt][job][op][1]:
                    f_u += params["T"] - se_process[jt][job][op][0]
                else: break
    f_u /= (len(ops_machine) * params["T"])
    f_s = 0
    f_c = {}
    for m in se_setup:
        f_c[m] = 0
        for l in se_setup[m]:
            if params["T"] >= se_setup[m][l][1]:
                f_s += se_setup[m][l][1] - se_setup[m][l][0]
                f_c[m] += 1
            elif se_setup[m][l][0] <= params["T"] < se_setup[m][l][1]:
                f_s += params["T"] - se_setup[m][l][0]
                f_c[m] += 1
            else: break
    f_s /= (len(ops_machine) * params["T"])
    f_i = 1 - f_u - f_s
    f_b = max(st_machine.values()) / min(st_machine.values()) - 1

    alt = (sum(st_machine[m] for m in st_machine) - p_tot) / len(st_machine)
    awt = (sum(st_job[jt][job] for jt in ini_set.keys() for job in ini_set[jt]["jobs"]) - p_tot - s_tot) / sum(len(ini_set[jt]["jobs"]) for jt in ini_set.keys())
    return seq, ((alt, awt), f_u, f_s, f_c, f_i, f_b), se_process, se_setup

def crossing(points, pr1, pr2, apx=True):
    for idx in points:
        jt1, job1, op1, _ = pr1[idx]
        for jt2, job2, op2, m in pr2:
            if jt1 == jt2 and job1 == job2 and op1 == op2:
                if apx: pr1[idx] = (jt1, job1, op1, m)
                pr2.remove((jt2, job2, op2, m))
                break
    return [pr1[i] if i in points else pr2.pop(0) for i in range(len(pr1))]

def crossover(mating_pool, cr):

    index = list(range(params["mating_pool"]))

    if cr == 1: # Based on Job Type
        pr1, pr2 = [mating_pool[pr][0].copy() for pr in rd.choice(index, size=2, replace=False)]
        chosen_jt = pr1[rd.randint(len(pr1))][0]
        points = [idx for idx in range(len(pr1)) if pr1[idx][0] == chosen_jt]
        child = crossing(points, pr1, pr2, apx=False)
    else:
        if cr == 2: # Based on F_c(# of Setup Change)
            index.sort(key=lambda idx:sum(mating_pool[idx][1][3].values()))
        elif cr == 3: # Based on F_b(Degree of Machine Load)
            index.sort(key=lambda idx:-mating_pool[idx][1][5])
        elif cr == 4: # Based on F_i(Degree of Idle Time)
            index.sort(key=lambda idx:mating_pool[idx][1][4])
        else: pass # Do not reach

        pr1, pr2 = [mating_pool[pr][0].copy() for pr in (rd.choice(index[:max(1, int(params["mating_pool"] * params["K"]))]), rd.choice(index[-max(1, int(params["mating_pool"] * params["K"])):]))]
        child = crossing(list(range(len(pr1))), pr1, pr2)
    return child

def mutation(process, setup, ini_set, machines, seq, cr):
    seq, (obj, f_u, f_s, f_c, f_i, f_b), se_process, se_setup = seq
    seq = seq.copy()
    if cr == 1:
        random_idx = rd.randint(len(seq))
        jt, job, op, m = seq.pop(random_idx)
        place_in_job = list(ini_set[jt]["ops"]).index(op)
        if place_in_job == 0:
            if len(list(ini_set[jt]["ops"])) > 1:
                for l in range(random_idx, len(seq)):
                    if seq[l][0] == jt and seq[l][1] == job and seq[l][2] == list(ini_set[jt]["ops"])[place_in_job + 1]:
                        next_idx = l
                        break
            else: next_idx = len(seq) + 1
            if next_idx == 0:
                seq.insert(0, (jt, job, op, m))
            else: seq.insert(rd.choice([i for i in range(next_idx + 1) if i != random_idx]), (jt, job, op, m))

        elif place_in_job == len(ini_set[jt]["ops"]) - 1:
            for l in range(random_idx - 1, -1, -1):
                if seq[l][0] == jt and seq[l][1] == job and seq[l][2] == list(ini_set[jt]["ops"])[place_in_job - 1]:
                    prior_idx = l
                    break
            if prior_idx == len(seq) - 1: seq.append((jt, job, op, m))
            else: seq.insert(rd.choice([i for i in range(prior_idx + 1, len(seq) + 1) if i != random_idx]), (jt, job, op, m))

        else:
            for l in range(random_idx - 1, -1, -1):
                if seq[l][0] == jt and seq[l][1] == job and seq[l][2] == list(ini_set[jt]["ops"])[place_in_job - 1]:
                    prior_idx = l
                    break
            for l in range(random_idx, len(seq)):
                if seq[l][0] == jt and seq[l][1] == job and seq[l][2] == list(ini_set[jt]["ops"])[place_in_job + 1]:
                    next_idx = l
                    break
            seq.insert(rd.choice(list(range(prior_idx + 1, next_idx + 1))), (jt, job, op, m))
    elif cr == 2:
        chosen_m = max(f_c, key=lambda m : f_c[m])
        if len(se_setup[chosen_m]) != 0:
            chosen_idx = rd.choice(list(se_setup[chosen_m]))
            chosen_jt, chosen_job, chosen_op, _ = seq[chosen_idx]
            alternative_m = rd.permutation([m for m in ini_set[chosen_jt]["ops"][chosen_op] if m != chosen_m]).tolist()
            if len(alternative_m) != 0:
                for m in alternative_m:
                    go_break = False
                    seq_tmp = seq.copy()
                    seq_tmp[chosen_idx] = (chosen_jt, chosen_job, chosen_op, m)

                    prior_op_found = False

                    for prior_idx in range(chosen_idx - 1, -1, -1):
                        if seq_tmp[prior_idx][3] == m:
                            prior_op_found = True
                            if getattr(setup, f"{seq_tmp[prior_idx][0]}{seq_tmp[prior_idx][2]}{seq_tmp[chosen_idx][0]}{seq_tmp[chosen_idx][2]}") == 0:
                                seq = seq_tmp.copy()
                                go_break = True
                            break
                    if not prior_op_found:
                        seq = seq_tmp.copy()
                        go_break = True
                    if go_break: break
    elif cr == 3:
        using_machine = []
        for _, _, _, m in seq:
            if m not in using_machine:
                using_machine.append(m)
        using_machine.sort(key=lambda using_m:-sum(getattr(process, f"{jt}{op}") for jt, _, op, m in seq if m == using_m))
        from_m = rd.choice(using_machine[:max(1, int(len(using_machine) * params["K"]))])
        to_m = min(machines, key=lambda m:sum(1 for sche in seq if m==sche[3]))

        for idx in rd.permutation(list(range(len(seq)))):
            jt, job, op, m = seq[idx]
            if m == from_m and to_m in ini_set[jt]["ops"][op]:
                seq[idx] = (jt, job, op, to_m)
                break

    elif cr == 4:
        using_machine = []
        for sche in seq:
            if sche[3] not in using_machine:
                using_machine.append(sche[3])
        t_p, t_s = {}, {}
        for tmp_m in using_machine:
            t_p[tmp_m], t_s[tmp_m] = 0, 0
            for jt, job, op, m in seq:
                if m == tmp_m:
                    if params["T"] >= se_process[jt][job][op][1]:
                        t_p[tmp_m] += se_process[jt][job][op][1] - se_process[jt][job][op][0]
                    elif se_process[jt][job][op][0] <= params["T"] < se_process[jt][job][op][1]:
                        t_p[tmp_m] += params["T"] - se_process[jt][job][op][0]
                    else: pass # Do not reach
            for l in se_setup[tmp_m]:
                if params["T"] >= se_setup[tmp_m][l][1]:
                    t_s[tmp_m] += se_setup[tmp_m][l][1] - se_setup[tmp_m][l][0]
                elif se_setup[tmp_m][l][0] <= params["T"] < se_setup[tmp_m][l][1]:
                    t_s[tmp_m] += params["T"] - se_setup[tmp_m][l][0]
                else: break
        using_machine.sort(key=lambda m:t_p[m] + t_s[m])
        from_m = rd.choice(using_machine[:max(1, int(len(using_machine) * params["K"]))])

        for idx in rd.permutation(list(range(len(seq)))):
            jt, job, op, m = seq[idx]
            if seq[idx][3] == from_m and list(ini_set[jt]["ops"]).index(op) != 0:
                for first_idx in range(len(seq)):
                    first_jt, first_job, first_op, first_m = seq[first_idx]
                    if first_jt == jt and first_job == job and list(ini_set[jt]["ops"]).index(first_op) == 0:
                        seq.insert(0, seq.pop(first_idx))
                        break
                break
    else: pass # Do not reach
    return seq

def first_stage(process, setup, ini_set, machines, seq):
    ops_machine, st_machine = {}, {}
    for m in machines:
        ops_machine[m], st_machine[m] = [], 0
    st_job = {jt : {job : 0 for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    for l in range(len(seq)):
        jt, job, op = seq[l]
        eligible_m, now = ini_set[jt]["ops"][op], []
        for m in eligible_m:
            if len(ops_machine[m]) == 0:
                now.append(max(st_machine[m], st_job[jt][job]))
            else:
                now.append(max(st_machine[m] + getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}"), st_job[jt][job]))
        select_m = eligible_m[now.index(min(now))]
        ops_machine[select_m] = (jt, op)
        st_machine[select_m], st_job[jt][job] = [now[eligible_m.index(select_m)] + getattr(process, f"{jt}{op}") for _ in range(2)]
        seq[l] = (jt, job, op, select_m)
    return objective(process, setup, ini_set, seq)

def second_stage(process, setup, ini_set, machines, mating_pool, cr):
    return crossover(mating_pool.copy(), cr) if rd.random() < 0.5 else mutation(process, setup, ini_set, machines, mating_pool[rd.choice(list(range(params["mating_pool"])))], cr)

def generate_case(process, setup, ini_set, machines):
    ini_pop = [(jt, job, op) for jt in ini_set.keys() for job in ini_set[jt]["jobs"] for op in ini_set[jt]["ops"]]
    pops = sorted([first_stage(process, setup, ini_set, machines, correct_procedure(ini_set, rd.permutation(ini_pop).tolist())) for _ in range(params["pop_size"])], key=lambda case: (params["w"] * case[1][0][0] + (1-params["w"]) * case[1][0][1], case[1][1]))
    database, cr = [pops[0]], 1

    for gen in range(1, params["num_of_gens"] + 1):
        mating_pool = [select_mp(pops) for _ in range(params["mating_pool"])]
        offsprings = []
        for _ in range(params["num_offs"]):
            offspring = second_stage(process, setup, ini_set, machines, mating_pool, cr)
            offsprings.append(objective(process, setup, ini_set, offspring))
        offsprings.sort(key=lambda offs: (params["w"] * offs[1][0][0] + (1-params["w"]) * offs[1][0][1], offs[1][1]))

        if params["w"] * offsprings[0][1][0][0] + (1-params["w"]) * offsprings[0][1][0][1] < params["w"] * pops[0][1][0][0] + (1-params["w"]) * pops[0][1][0][1]:
            cr = 1
            pops = sorted(pops + offsprings, key=lambda case: (params["w"] * case[1][0][0] + (1-params["w"]) * case[1][0][1], case[1][1]))[:params["pop_size"]]
            database.append(pops[0])
        elif sum(offsprings[0][1][3].values()) > sum(pops[0][1][3].values()): cr = 2
        elif offsprings[0][1][5] > pops[0][1][5]: cr = 3
        elif offsprings[0][1][4] > pops[0][1][4]: cr = 4
        else: cr = 1
    return database

def save(ini_set, data):
    conn = mysql.connector.connect(user=user, password=password, database=db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {case_database};")
    add = [i[0] for i in cursor][0]
    for h, data in enumerate(data):
        h += add
        alt = data[1][0][0]
        awt = data[1][0][1]
        cursor.execute(f"INSERT INTO {case_database} VALUES ({h + 1}, \"{[len(ini_set[jt]["jobs"]) for jt in ini_set.keys()]}\", {alt}, {awt});")

        cursor.execute(f"""
        CREATE TABLE S_O_{h + 1} (
        info smallint PRIMARY KEY NOT NULL,
        job_type varchar(20) NOT NULL,
        job varchar(10) NOT NULL);""")

        for i in range(len(data[0])):
            jt, job, _, _ = data[0][i]
            cursor.execute(f"INSERT INTO S_O_{h + 1} VALUES ({i + 1}, \"{jt}\", \"{job}\");")
    conn.commit()
    conn.close()

class Duration:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
def start(processes, setups, machines_tmp):
    process, setup, ini_set, machines = Duration(), SetUp(), {}, []

    conn = mysql.connector.connect(user=user, password=password, database=db_name)
    cursor = conn.cursor()
    for jt in processes.keys():
        ini_set[jt] = {"ops": {}}
        for op in processes[jt]["ops"]:
            ms,processing_time = processes[jt]["ops"][op]
            ini_set[jt]["ops"][op] = ms
            for m in ms:
                if m not in machines:
                    machines.append(m)
            setattr(process, f"{jt}{op}", processing_time)
            cursor.execute(f"INSERT INTO PROCESSES VALUES (\"{jt}\",\"{op}\",{processing_time});")
    machines.sort(key=lambda machine: machines_tmp.index(machine))

    for op_type1 in setups:
        for op_type2 in setups:
            (jt1, op1), (jt2, op2) = op_type1, op_type2
            setattr(setup, f"{jt1}{op1}{jt2}{op2}", setups[(jt1, op1)][(jt2, op2)])
            cursor.execute(f"INSERT INTO SETUPS VALUES (\"{jt1}\",\"{op1}\",\"{jt2}\",\"{op2}\", {getattr(setup, f"{jt1}{op1}{jt2}{op2}")});")
    conn.commit()
    cursor.close()

    for i in range(database_input):
        print(i+1)
        for jt in processes.keys():
            ini_set[jt]["jobs"] = [f"Job{j+1}" for j in range(rd.randint(5,max_num_job+1))]
        save(ini_set, generate_case(process, setup, ini_set, machines))
    return process, setup, ini_set, machines

def main():

    jts = [f"Job_Type{i}" for i in range(1, num_jts + 1)]
    machines = [f"M{i}" for i in range(1, num_machines + 1)]

    processes = {jt : {"ops":{f"Op{o+1}" : [sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False),key=lambda machine: machines.index(machine)),rd.randint(2, max_num_op + 1)] for o in range(rd.randint(1, max_num_op + 1))}} for jt in jts}

    op_types = [(jt, op) for jt in jts for op in processes[jt]["ops"]]
    setups = {op1:{op2:0 if op1[0] == op2[0] else rd.randint(1, max(max_time//2, 1) + 1) for op2 in op_types} for op1 in op_types}

    for jt in processes.keys():
        print(jt)
        for job in processes[jt]:
            print(f"\t{job}")
            print(f"\t{processes[jt][job]}")
        print()

    for op1 in setups.keys():
        print(op1," -> ", end="")
        for op2 in setups[op1]:
            if setups[op1][op2] != 0:
                print(f"{op2}({setups[op1][op2]})", end=" / ")
        print()

    print("\n-----------------------------------------------------------------------------------------------------")

    start(processes, setups, machines)

if __name__ == '__main__':
    main()