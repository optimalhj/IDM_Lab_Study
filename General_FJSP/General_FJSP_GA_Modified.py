from numpy import random as rd
import matplotlib.pyplot as plt

def printing(built):
    for job in built:
        print(job)
        for op in built[job]:
            print("\t", op, end="")
            print("\t", built[job][op])
        print()

def calculate(origin, operations):
    jobs, machines = {}, {}
    for oper in operations:
        jobs[oper[0]], machines[oper[2]] = 0, 0
    for oper in operations:
        jobs[oper[0]], machines[oper[2]] = [max(jobs[oper[0]], machines[oper[2]]) + getattr(origin, f"{oper[0]}{oper[1]}{oper[2]}") for _ in range(2)]
    return max(machines.values())

def versus(origin, candidates):
    makespans = [calculate(origin, case) for case in candidates]
    return candidates[makespans.index(min(makespans))]

def generate_offsprings(origin, mom,dad,rates,machines):
    offsprings, parents = [], (mom, dad)
    way_offspring = rd.choice([i for i in range(len(rates))], size=1, p=rates, replace=False)[0]
    for i in range(2):
        if way_offspring == 0: # POX
            jobs = []
            for oper in parents[i]:
                if oper[0] not in jobs:
                    jobs.append(oper[0])
            fixed_job = rd.choice(jobs, size=1)[0]
            fixed_oper, offspring = [oper for oper in parents[1-i] if oper[0] != fixed_job], []
            for idx in range(len(parents[i])):
                if parents[i][idx][0] == fixed_job:
                    offspring.append(parents[i][idx])
                else:
                    offspring.append(fixed_oper.pop(0))
            offsprings.append(offspring)

        elif way_offspring == 1: # Assignment_crossover
            idx1, idx2 = sorted(rd.choice([i for i in range(len(mom))], size=2, replace=False))
            offsprings.append(
                parents[i][0:idx1] + [(parents[i][idx1][0], parents[i][idx1][1], parents[1-i][idx1][2])] + parents[i][
                    idx1 + 1:idx2] + [(parents[i][idx2][0], parents[i][idx2][1], parents[1-i][idx2][2])] + parents[i][
                    idx2 + 1:])

        elif way_offspring == 2: # PPS
            idx_job = rd.randint(len(mom))
            indices = [idx for idx in range(len(parents[i])) if parents[i][idx][0] == parents[i][idx_job][0]]
            place = indices.index(idx_job)
            offspring = [oper for oper in parents[i]]
            if indices[place] != len(mom) - 1 and place != len(indices) - 1 and indices[place] + 1 != indices[place + 1]:
                offspring.insert(rd.choice(range(indices[place] + 1, indices[place + 1]), size=1)[0], offspring.pop(idx_job))
            if calculate(origin, offspring) < calculate(origin, parents[i]):
                offsprings.append(offspring)
            else:
                offsprings.append(parents[i])

        elif way_offspring == 3: # Assignment_Mutation
            idx = rd.randint(len(mom))
            offsprings.append(parents[i][0:idx] +
                              [(parents[i][idx][0], parents[i][idx][1], rd.choice([m for m in machines if m != parents[i][idx][2]]))] +
                              parents[i][idx + 1:])

        elif way_offspring == 4: # Assignment_Intelligent_Mutation
            machine_load, machine_max = {m: 0 for m in machines}, (0, 0)
            for oper in parents[i]:
                machine_load[oper[2]] += getattr(origin, f"{oper[0]}{oper[1]}{oper[2]}")
                if machine_load[oper[2]] > machine_max[1]:
                    machine_max = oper[2], machine_load[oper[2]]
            machine_min = machines[list(machine_load.values()).index(min(machine_load.values()))]
            move_candidate = sorted([oper for oper in parents[i] if oper[2] == machine_max[0]], key=lambda op:getattr(origin,f"{op[0]}{op[1]}{op[2]}"), reverse=True)[0]
            idx = parents[i].index(move_candidate)
            offsprings.append(parents[i][0:idx] + [(move_candidate[0], move_candidate[1], machine_min)] + parents[i][idx + 1:])

        else:  # Do not reach
            offsprings = 0

    return offsprings

def select_pop(origin, popped, way_select_pop):

    if way_select_pop == 0: # Binary tournament
        indices, candidates = [i for i in range(len(popped))], []

        while len(indices) > 2:
            candidates.append([indices.pop(rd.randint(len(indices))) for _ in range(2)])
        candidates.append(indices)
        new_candidates = [versus(origin, [popped[idx] for idx in candidate]) for candidate in candidates]

        if len(new_candidates) > 1:
            return select_pop(origin, new_candidates, 0)
        else:
            return new_candidates[0]

    elif way_select_pop == 1: # n-Size tournament
        indices = [i for i in range(len(popped))]
        candidates = []
        n_size = rd.randint(3, max(4, len(indices)//2))

        while len(indices) > n_size:
            candidates.append([indices.pop(rd.randint(len(indices))) for _ in range(n_size)])
        candidates.append(indices)
        new_candidates = [versus(origin, [popped[idx] for idx in candidate]) for candidate in candidates]
        
        if len(new_candidates) > 1:
            return select_pop(origin, new_candidates, 1)
        else:
            return new_candidates[0]

    elif way_select_pop == 2:  # Linear ranking
        return popped[rd.choice([i for i in range(0, len(popped))], size=1, replace=False, p=[2 * i / (len(popped) * (len(popped) + 1)) for i in range(1, len(popped) + 1)])[0]]

    else:  # Do not reach
        return 0

def initial_pop(origin, ini_set, machines, assign, seq):

    way_assign, popped = rd.choice([i for i in range(len(assign))], size = 1, p = assign)[0], []
    if way_assign == 0: # The Global Minimum

        tmp_set = {job : {op : {m : getattr(origin, f"{job}{op}{m}") for m in machines} for op in ini_set[job]} for job in ini_set}

        for _ in range(sum(len(ini_set[job]) for job in ini_set)):
            plus_time, new_job, new_op, new_m = 99999, 0, 0, 0
            for job in tmp_set:
                for op in tmp_set[job]:
                    for m in machines:
                        if tmp_set[job][op][m] < plus_time:
                            plus_time, new_job, new_op, new_m = tmp_set[job][op][m], job, op, m
            popped.append((new_job, new_op, new_m))
            tmp_set[new_job].pop(new_op)
            for job in tmp_set:
                for op in tmp_set[job]:
                    tmp_set[job][op][new_m] += plus_time

    elif way_assign == 1: # Randomly Permute Jobs and Machines

        rd_job_seq = rd.choice(list(ini_set), size=len(ini_set), replace=False)
        rd_m_seq = rd.choice(machines, size=len(machines), replace=False)

        tmp_set = {job : {op : {m : getattr(origin, f"{job}{op}{m}") for m in rd_m_seq} for op in ini_set[job]} for job in rd_job_seq}

        for job in rd_job_seq:
            for op in tmp_set[job]:
                plus_time, new_m = 999999, 0
                for m in rd_m_seq:
                    if tmp_set[job][op][m] < plus_time:
                        plus_time, new_m = tmp_set[job][op][m], m
                popped.append((job, op, new_m))
                for job_tmp in tmp_set:
                    for op_tmp in tmp_set[job_tmp]:
                        tmp_set[job_tmp][op_tmp][new_m] += plus_time

    else: # Do not reach
        popped.append(0)

    way_seq, set_tmp, length = rd.choice([i for i in range(len(seq))], size = 1, p = seq)[0], [], len(popped)
    if way_seq == 0: # Randomly select a job
        indices = list(rd.choice(range(length), size=length, replace=False))

        while len(set_tmp) < length:
            for idx in indices:
                selected = popped[idx]
                if selected[1] == ini_set[selected[0]][0] or list(ini_set[selected[0]])[list(ini_set[selected[0]]).index(selected[1]) - 1] in [op[1] for op in set_tmp if op[0] == selected[0]]:
                    set_tmp.append(selected)
                    indices.remove(idx)

    elif way_seq == 1: # Most Work Remaining(MWR)

        refer = {job: [[], 0] for job in ini_set.keys()}
        for oper in popped:
            refer[oper[0]][0].append(oper)
            refer[oper[0]][1] += getattr(origin, f"{oper[0]}{oper[1]}{oper[2]}")
        for job in refer.keys():
            refer[job][0].sort(key=lambda op:ini_set[job].index(op[1]))

        refer_job = list(ini_set)
        while len(set_tmp) < length:
            refer_job.sort(key=lambda job: refer[job][1], reverse=True)
            set_tmp.append(refer[refer_job[0]][0].pop(0))
            refer[refer_job[0]][1] -= getattr(origin, f"{set_tmp[-1][0]}{set_tmp[-1][1]}{set_tmp[-1][2]}")

    elif way_seq == 2: # Most Number of Operations Remaining(MOR)
        refer = {job: [[], 0] for job in ini_set.keys()}
        for oper in popped:
            refer[oper[0]][0].append(oper)
            refer[oper[0]][1] += 1
        for job in refer.keys():
            refer[job][0].sort(key=lambda op:ini_set[job].index(op[1]))

        refer_job = list(ini_set)
        while len(set_tmp) < length:
            refer_job.sort(key=lambda job: refer[job][1], reverse=True)
            set_tmp.append(refer[refer_job[0]][0].pop(0))
            refer[refer_job[0]][1] -= 1

    else: # Do not reach
        set_tmp = 0
    return set_tmp

def graph_gen(final):

    plt.plot(list(final), [final[g][0] for g in final])

    plt.xticks(rotation=45, fontsize=5)
    plt.title("Makespan of FJSP")

    plt.xlabel("Gen")
    plt.ylabel("Tardiness")

    plt.show()

def graph_makespan(origin, seqs, machines):
    _, ax = plt.subplots()
    start_job, start_machine = {}, {}
    for job, _, _ in seqs:
        if job not in list(start_job):
            start_job[job] = 0
    for m in machines:
        start_machine[m] = 0
        ax.barh(m, 0, left=0)
    for job,op,m in seqs:
        start_oper, operating = max(start_job[job], start_machine[m]), getattr(origin, f"{job}{op}{m}")
        ax.barh(m, operating, left=start_oper, color=plt.get_cmap('tab20', len(start_job))(list(start_job).index(job)), edgecolor='black')
        ax.text(start_oper + operating / 2, m, f"{job}\n{op}\n{m}\n({operating})", va='center', ha='center', color='black', fontsize=7)
        start_job[job], start_machine[m] = [start_oper + operating for _ in range(2)] 
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()

def ga(origin, ini_set, machines, params):

    ini_pop = sorted([initial_pop(origin, ini_set, machines, assign=params["ini_assign"], seq=params["ini_seq"])
               for _ in range(params["pop_size"])], key=lambda case: calculate(origin, case))

    generations, best_child, horizon = {}, 0, 9999999
    for Gen in range(1, params["num_of_gens"] + 1):
        offsprings = []

        for _ in range(params["pop_size"]):
            mother, father = [versus(origin, [select_pop(origin, ini_pop, rd.randint(3)) for _ in range(params["pop_size"])]) for _ in range(2)]
            offspring = generate_offsprings(origin, mother, father, params["crossover"], machines)
            offsprings.extend(offspring)
        candidate = versus(origin, offsprings)
        score_candidate = calculate(origin, candidate)

        if score_candidate < horizon:
            horizon, best_child = score_candidate, candidate

        generations[f"Gen {Gen}"] = horizon, best_child

        ini_pop = sorted(ini_pop + offsprings, key=lambda case: calculate(origin, case))[0:params["pop_size"]]
    graph_gen(generations)
    return generations[f"Gen {params["num_of_gens"]}"]

class Build:
    def __init__(self):
        pass
def start(built_parameter):
    original, ini_set, machines = Build(), {}, []

    for job in built_parameter:
        ini_set[job] = []
        for op in built_parameter[job]:
            ini_set[job].append(op)
            for m in built_parameter[job][op]:
                setattr(original, f"{job}{op}{m}", built_parameter[job][op][m])
                if m not in machines:
                    machines.append(m)

    # GA Parameter Input
    params = {"pop_size": 10, "num_of_gens": 35, "ini_assign": [0.1, 0.9], "ini_seq": [0.2, 0.4, 0.4], "crossover": [0.45, 0.45, 0.02, 0.02, 0.06]}

    result_obj, result_seq = ga(original, ini_set, machines, params)
    print("Total Makespan :", result_obj)
    print("Best Sequence :")
    print(result_seq)
    graph_makespan(original, result_seq, machines)

def main():

    # Parameter Input
    num_job = 5
    max_num_op = 8
    num_m = 5
    max_time = 9

    job_op = {}
    for i in range(num_job):
        job_op[f"Job{i+1}"] = [f"OP{j+1}" for j in range(rd.randint(1, max_num_op + 1))]
    machines = [f"M{i}" for i in range(1,num_m + 1)]

    built_parameter = {job : {op : {m : rd.randint(1,max_time+1) for m in machines} for op in job_op[job]} for job in job_op}

    printing(built_parameter)

    start(built_parameter)

if __name__ == "__main__":
    main()