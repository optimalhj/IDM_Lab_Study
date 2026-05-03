from numpy import random as rd
import matplotlib.pyplot as plt

def printing(built):
    for job in built:
        print(job)
        for op in built[job]:
            print("\t", op, end="")
            print("\t", built[job][op])
        print()

def calculate(og, ops):
    jobs, ms = {}, {}
    for oper in ops: jobs[oper[0]], ms[oper[2]] = 0, 0
    for oper in ops: jobs[oper[0]], ms[oper[2]] = [max(jobs[oper[0]], ms[oper[2]]) + getattr(og, f"{oper[0]}{oper[1]}{oper[2]}") for _ in range(2)]
    return max(ms.values())

def generate_offs(og, pr1, pr2, rates, ms):
    way_off = rd.choice([i for i in range(len(rates))], size=1, p=rates, replace=False)[0]
    if way_off == 0: # POX
        jobs = []
        for oper in pr1:
            if oper[0] not in jobs: jobs.append(oper[0])
        fixed_job = jobs[rd.randint(len(jobs))]
        fixed_oper, off = [oper for oper in pr2 if oper[0] != fixed_job], []
        for idx in range(len(pr1)):
            if pr1[idx][0] == fixed_job: off.append(pr1[idx])
            else: off.append(fixed_oper.pop(0))
    elif way_off == 1: # Assignment_crossover
        idx1, idx2 = sorted(rd.choice([i for i in range(len(pr1))], size=2, replace=False))
        off = pr1[0:idx1] + [(pr1[idx1][0], pr1[idx1][1], pr2[idx1][2])] + pr1[
                idx1 + 1:idx2] + [(pr1[idx2][0], pr1[idx2][1], pr2[idx2][2])] + pr1[
                idx2 + 1:]
    elif way_off == 2: # PPS
        idx_job = rd.randint(len(pr1))
        idxs = [idx for idx in range(len(pr1)) if pr1[idx][0] == pr1[idx_job][0]]
        place = idxs.index(idx_job)
        off = [oper for oper in pr1]
        if idxs[place] != len(pr1) - 1 and place != len(idxs) - 1 and idxs[place] + 1 != idxs[place + 1]: off.insert(rd.choice(range(idxs[place] + 1, idxs[place + 1]), size=1)[0], off.pop(idx_job))
    elif way_off == 3: # Assignment_Mutation
        idx = rd.randint(len(pr1))
        off = pr1[0:idx] + [(pr1[idx][0], pr1[idx][1], rd.choice([m for m in ms if m != pr1[idx][2]]))] + pr1[idx + 1:]
    elif way_off == 4: # Assignment_Intelligent_Mutation
        m_load, m_max = {m: 0 for m in ms}, (0, 0)
        for oper in pr1:
            m_load[oper[2]] += getattr(og, f"{oper[0]}{oper[1]}{oper[2]}")
            if m_load[oper[2]] > m_max[1]: m_max = oper[2], m_load[oper[2]]
        m_min = ms[list(m_load.values()).index(min(m_load.values()))]
        moving = sorted([oper for oper in pr1 if oper[2] == m_max[0]], key=lambda op:getattr(og,f"{op[0]}{op[1]}{op[2]}"), reverse=True)[0]
        idx = pr1.index(moving)
        off = pr1[0:idx] + [(moving[0], moving[1], m_min)] + pr1[idx + 1:]
    else: off = 0 # Do not reach
    return off

def select_pop(pops):
    idxs = [i for i in range(len(pops))]
    way_pop = rd.randint(3)

    if way_pop == 0: # Binary tournament
        return pops[min(rd.choice(idxs, size=2, replace=False),key=lambda idx: pops[idx][1])]
    elif way_pop == 1:  # n-Size tournament
        return pops[min(rd.choice(idxs, size=rd.randint(3, max(4, int(len(idxs) / 2.5))), replace=False),key=lambda idx: pops[idx][1])]
    elif way_pop == 2:  # Linear ranking
        return pops[rd.choice(idxs, size=1, p=[2 * i / (len(idxs) * (len(idxs) + 1)) for i in range(len(idxs), 0, -1)])[0]]
    else: return 0 # Do not reach

def ini_pop(og, ini_set, ms, assign, seq):

    way_assign, popped = rd.choice([i for i in range(len(assign))], size = 1, p = assign)[0], []
    if way_assign == 0: # The Global Minimum

        tmp_set = {job : {op : {m : getattr(og, f"{job}{op}{m}") for m in ms} for op in ini_set[job]} for job in ini_set}

        for _ in range(sum(len(ini_set[job]) for job in ini_set)):
            plus_time, n_job, n_op, n_m = 99999, 0, 0, 0
            for job in tmp_set:
                for op in tmp_set[job]:
                    for m in ms:
                        if tmp_set[job][op][m] < plus_time: plus_time, n_job, n_op, n_m = tmp_set[job][op][m], job, op, m
            popped.append((n_job, n_op, n_m))
            tmp_set[n_job].pop(n_op)
            for job in tmp_set:
                for op in tmp_set[job]: tmp_set[job][op][n_m] += plus_time

    elif way_assign == 1: # Randomly Permute Jobs and Machines

        rd_job = rd.choice(list(ini_set), size=len(ini_set), replace=False)
        rd_m = rd.choice(ms, size=len(ms), replace=False)
        tmp_set = {job : {op : {m : getattr(og, f"{job}{op}{m}") for m in rd_m} for op in ini_set[job]} for job in rd_job}
        for job in rd_job:
            for op in tmp_set[job]:
                plus_time, n_m = 999999, 0
                for m in rd_m:
                    if tmp_set[job][op][m] < plus_time: plus_time, n_m = tmp_set[job][op][m], m
                popped.append((job, op, n_m))
                for job_tmp in tmp_set:
                    for op_tmp in tmp_set[job_tmp]: tmp_set[job_tmp][op_tmp][n_m] += plus_time
    else: popped.append(0)# Do not reach

    way_seq, set_tmp, length = rd.choice([i for i in range(len(seq))], size = 1, p = seq)[0], [], len(popped)
    if way_seq == 0: # Randomly select a job
        idxs = list(rd.choice(range(length), size=length, replace=False))

        while len(set_tmp) < length:
            for idx in idxs:
                selected = popped[idx]
                if selected[1] == ini_set[selected[0]][0] or list(ini_set[selected[0]])[list(ini_set[selected[0]]).index(selected[1]) - 1] in [op[1] for op in set_tmp if op[0] == selected[0]]:
                    set_tmp.append(selected)
                    idxs.remove(idx)

    elif way_seq == 1: # Most Work Remaining(MWR)
        ref = {job: [[], 0] for job in ini_set.keys()}
        for oper in popped:
            ref[oper[0]][0].append(oper)
            ref[oper[0]][1] += getattr(og, f"{oper[0]}{oper[1]}{oper[2]}")
        for job in ref.keys(): ref[job][0].sort(key=lambda op:ini_set[job].index(op[1]))

        ref_job = list(ini_set)
        while len(set_tmp) < length:
            ref_job.sort(key=lambda job: ref[job][1], reverse=True)
            set_tmp.append(ref[ref_job[0]][0].pop(0))
            ref[ref_job[0]][1] -= getattr(og, f"{set_tmp[-1][0]}{set_tmp[-1][1]}{set_tmp[-1][2]}")

    elif way_seq == 2: # Most Number of Operations Remaining(MOR)
        ref = {job: [[], 0] for job in ini_set.keys()}
        for oper in popped:
            ref[oper[0]][0].append(oper)
            ref[oper[0]][1] += 1
        for job in ref.keys(): ref[job][0].sort(key=lambda op:ini_set[job].index(op[1]))

        ref_job = list(ini_set)
        while len(set_tmp) < length:
            ref_job.sort(key=lambda job: ref[job][1], reverse=True)
            set_tmp.append(ref[ref_job[0]][0].pop(0))
            ref[ref_job[0]][1] -= 1

    else: set_tmp = 0# Do not reach
    return set_tmp

def graph_gen(og, history):
    his_gen = [f"Gen {i+1}" for i in range(len(history))]
    his_makespan = [calculate(og, his) for his in history]
    plt.plot(his_gen, his_makespan)

    plt.xticks(rotation=45, fontsize=5)
    plt.title("Makespan of FJSP")

    plt.xlabel("Gen")
    plt.ylabel("Tardiness")

    plt.show()
    return his_makespan[-1], history[-1]

def graph_makespan(og, obj, seqs, ms):
    _, ax = plt.subplots()
    s_job, s_m = {}, {}
    for job, _, _ in seqs:
        if job not in list(s_job): s_job[job] = 0
    for m in ms:
        s_m[m] = 0
        ax.barh(m, 0, left=0)
    for job,op,m in seqs:
        s_oper, dur = max(s_job[job], s_m[m]), getattr(og, f"{job}{op}{m}")
        ax.barh(m, dur, left=s_oper, color=plt.get_cmap('tab20', len(s_job))(list(s_job).index(job)), edgecolor='black')
        ax.text(s_oper + dur / 2, m, f"{job}\n{op}\n({dur})", va='center', ha='center', color='black', fontsize=7)
        s_job[job], s_m[m] = [s_oper + dur for _ in range(2)]
    ax.set_xticks([i for i in range(int(obj) + 2)])
    ax.tick_params(axis='x', labelsize=5)
    ax.set_yticks(range(len(ms)))
    ax.set_yticklabels(ms)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()

def ga(og, ini_set, ms, params):
    history = []
    pops = sorted([ini_pop(og, ini_set, ms, assign=params["assign"], seq=params["seq"]) for _ in range(params["pop_size"])], key=lambda case: calculate(og, case))

    for Gen in range(1, params["gens"] + 1):
        mating_pool = [select_pop(pops) for _ in range(params["pop_size"])]
        idxs, offs = [i for i in range(len(mating_pool))], []
        for _ in range(params["pop_size"]):
            mom, dad = rd.choice(idxs, size=2, replace=False)
            offs.append(generate_offs(og, mating_pool[mom], mating_pool[dad], params["offs"], ms))
        pops = sorted(pops + offs, key=lambda case: calculate(og, case))[0:params["pop_size"]]
        history.append(pops[0])
    return graph_gen(og, history)

class Build:
    def __init__(self): pass
def start(job_op):
    origin, ini_set, ms = Build(), {}, []

    for job in job_op:
        ini_set[job] = []
        for op in job_op[job]:
            ini_set[job].append(op)
            for m in job_op[job][op]:
                setattr(origin, f"{job}{op}{m}", job_op[job][op][m])
                if m not in ms: ms.append(m)

    # GA Parameter Input
    params = {"pop_size": 10, "gens": 35, "assign": [0.1, 0.9], "seq": [0.2, 0.4, 0.4], "offs": [0.45, 0.45, 0.02, 0.02, 0.06]}

    obj, seq = ga(origin, ini_set, ms, params)
    print("Total Makespan :", obj)
    print("Best Sequence :")
    print(seq)
    graph_makespan(origin, obj, seq, ms)

def main():

    # Parameter Input
    num_job = 5
    max_num_op = 8
    num_m = 5
    max_time = 9

    job_op = {f"Job{i+1}" : [f"OP{j+1}" for j in range(rd.randint(1, max_num_op + 1))] for i in range(num_job)}
    ms = [f"M{i}" for i in range(1,num_m + 1)]

    ini_set = {job : {op : {m : rd.randint(1,max_time+1) for m in ms} for op in job_op[job]} for job in job_op}
    printing(ini_set)
    start(ini_set)

if __name__ == "__main__":
    main()