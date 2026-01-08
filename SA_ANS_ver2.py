# For Random Processing_Time/Due_Date and Destruction
import numpy as np
import math
import itertools
import gurobipy as gp
from gurobipy import GRB

# Jobs to Class process / Randomly Building "Processing Time" and "Due Date"
class Jobs:
    def __init__(self):
        self.PB = np.random.randint(1,10)
        self.aD = round(np.random.random(),3)
        self.aU = round(np.random.random(),3)
        self.D = np.random.randint(1, high = 4 * Number_of_Jobs)
        print("Processing Time :",self.PB, "/ Due Date :",self.D,"/ devastate :",self.aD,"/ replace :",self.aU)

def build():
    jobs = ["j%s" % (i + 1) for i in range(Number_of_Jobs)]
    job_at = {name : Jobs() for name in jobs}
    reps = ["r%s" % (i + 1) for i in range(Number_of_Replaces)]
    return jobs,job_at,reps

# Calculating each job's tardiness and total tardiness
def tardiness(seqs):
    now,each_td = 0,{}
    for job in seqs:
        now += globals()[job].processing_time
        each_td[job] = max(now - globals()[job].due, 0)
    return each_td, sum(each_td.values())

# Calculating TC / Use every variable from TC_Initializing()
# Result is a just objective

def TC(case):
    TASKS = case + REPS
    tc = gp.Model("TC")

    x_r = {rep : tc.addVar(vtype = GRB.BINARY, name = "x_%s" % rep) for rep in REPS}
    y_kk = {(ini, fin): tc.addVar(vtype = GRB.BINARY, name = "y_%s%s" % (ini, fin)) for ini, fin in itertools.permutations(TASKS, 2)}

    a_j = {job: tc.addVar(vtype = GRB.CONTINUOUS, name =  'a_%s' % (job)) for job in case}
    l_j = {job: tc.addVar(vtype = GRB.CONTINUOUS, name =  'l_%s' % (job)) for job in case}
    p_j = {job: tc.addVar(vtype = GRB.CONTINUOUS, name =  'p_%s' % (job)) for job in case}
    t_j = {job: tc.addVar(vtype = GRB.CONTINUOUS, name =  't_%s' % (job)) for job in case}

    for a in a_j:
        tc.addConstr(a_j[a]>=0)
    for l in l_j:
        tc.addConstr(l_j[l]>=0)
    for p in p_j:
        tc.addConstr(p_j[p]>=0)
    for t in t_j:
        tc.addConstr(t_j[t]>=0)

    s_k = {task: tc.addVar(vtype = GRB.CONTINUOUS, name = 's_%s' % task) for task in TASKS}
    c_k = {task: tc.addVar(vtype = GRB.CONTINUOUS, name = 'c_%s' % task) for task in TASKS}

    for s in s_k:
        tc.addConstr(s_k[s]>=0)
    for c in c_k:
        tc.addConstr(c_k[c]>=0)

    tc.addConstr(x_r[REPS[Number_of_Replaces-1]] == 1)

    for job in case:
        tc.addConstr(y_kk[job, REPS[Number_of_Replaces-1]] == 1)

    for job in case:
        for rep in REPS:
            tc.addConstr(s_k[rep] >= c_k[job] - M * x_r[rep])

    for job in case:
        tc.addConstr(t_j[job] >= c_k[job] - JOB_AT[job].D)
        tc.addConstr(l_j[job] <= L)

    for job in case:
        for rep in REPS[0:Number_of_Replaces-1]:
            tc.addConstr(l_j[job] >= s_k[REPS[REPS.index(rep)+1]] - c_k[rep]
                         - M * (1 - y_kk[rep, job] + y_kk[REPS[REPS.index(rep)+1], job]))

    for job in case:
        tc.addConstr(l_j[job] >= s_k[REPS[0]] - M * (1 - y_kk[job, REPS[0]]))

    for job in case:
        for rep in REPS[0:Number_of_Replaces-1]:
            tc.addConstr(a_j[job] >= s_k[job] - c_k[rep]
                         - M * (1 - y_kk[rep, job] + y_kk[REPS[REPS.index(rep)+1], job]))

    for job in case:
        tc.addConstr(a_j[job] >= s_k[job] - M * (1 - y_kk[job, REPS[0]]))

    for ini, fin in itertools.combinations(REPS, 2):
        tc.addConstr(y_kk[ini, fin] == 1)

    for ini, fin in itertools.permutations(TASKS, 2):
        tc.addConstr(c_k[fin] <= s_k[ini] + M * y_kk[ini, fin])
        tc.addConstr(c_k[ini] <= s_k[fin] + M * (1 - y_kk[ini, fin]))

    for rep in REPS:
        tc.addConstr(c_k[rep] == s_k[rep] + R * x_r[rep])

    for job in case:
        tc.addConstr(c_k[job] == s_k[job] + p_j[job])

    for job in case:
        tc.addConstr(p_j[job] >= JOB_AT[job].PB + JOB_AT[job].aD * a_j[job] - JOB_AT[job].aU * (L - l_j[job]))

    for job in case:
        tc.addConstr(p_j[job] >= JOB_AT[job].PB)

    tc.setObjective(muE * sum(p_j[job] for job in case)
                  + muR * sum(x_r[rep] for rep in REPS)
                  + muT * sum(t_j[job] for job in case)
                    ,GRB.MINIMIZE)
    tc.optimize()

    obj_val = tc.getAttr("ObjVal")
    print(obj_val)
    return round(obj_val)

# Comparing each case with same jobs by comparing TC.
def best(cases):
    all_TC = []
    for case in range(len(cases)):
        all_TC.append(TC(cases[case]))
        print("Candidate %3s :" % (case+1), cases[case], "-->", all_TC[-1])
    min_TC = min(all_TC)

    # Choosing one case with the lowest Total Cost
    best_candidate = cases[all_TC.index(min_TC)]
    print("\n< Best case > : Candidate %d / %d\n"%(cases.index(best_candidate)+1, len(cases)), list(best_candidate),
          "\n<   TCost   > :", min_TC)
    return best_candidate,min_TC

# Local Search / If Nei ==1, Swap search    or    Nei == 2, Insert search
def localsearch(ini_seq,search):
    candidates = []
    for _ in range(search):
        ini_seq_tmp = ini_seq.copy()
        if Nei == 1:
            cvt = np.random.randint(len(ini_seq_tmp)-1)     # convert_index
            job = ini_seq_tmp.pop(cvt)
            ini_seq_tmp.insert(cvt+1,job)
        if Nei == 2 :
            dtt_job = ini_seq_tmp.pop(np.random.randint(len(ini_seq_tmp)))
            ini_seq_tmp.insert(np.random.randint(len(ini_seq_tmp)) + 1, dtt_job)
        candidates.append(ini_seq_tmp)
    return best(candidates)

# Iteration
# Comparing existing best sequence's Cost vs new candidate sequence's Cost. Lower one will survive.
def iteration(spt,spt_cost):
    each_sequence, total_cost = spt, spt_cost
    temperature = Temperature_Initial
    same_count = 0
    search = 1
    while temperature >= Temperature_Min and same_count <= SameCount_Max:
        iteration_compare = 0
        for Iteration in range(Iteration_Max):

            final_cost = localsearch(list(each_sequence),search)

            if final_cost[1] < total_cost:
                each_sequence, total_cost = final_cost
            else:
                if np.random.random() < math.e ** ((total_cost - final_cost[1]) / temperature):
                    each_sequence, total_cost = final_cost
                else:
                    iteration_compare += 1
                same_count += 1

            print("\n\n<<Iteration Result>>\n  Iteration  :  %s" % (Iteration + 1))
            print("New Sequence =", each_sequence)
            print("  New  Cost  = %s\n\n%s" % (total_cost, '-' * 100))

        temperature *= Temperature_K
        if iteration_compare >= Iteration_Max/2 and same_count < SameCount_Max:
            search += 1
        print("Temperature :", temperature, Temperature_Min)
        print(" Same Count :", same_count, SameCount_Max)
        print("   Search   :", search, "\n << New Period >>\n\n")
    return each_sequence, total_cost


# Initial Sequence : SPT
# Every Job Sequence is saved in List
# Jobs' attributes are saved as feature of the variable
def start():
    spt = sorted(JOBS, key = lambda job : JOB_AT[job].PB)
    spt_cost = TC(spt)
    print("\nInitial  Sequence =", spt)
    print("   Initial Cost   =", spt_cost, "\n\n%s" % ("-" * 100))
    return iteration(spt,spt_cost)

if __name__ == "__main__":

    # Number of Jobs, Replaces / Tasks = Jobs + Replaces
    Number_of_Jobs =
    Number_of_Replaces =

    # SA Parameters / Able to modify values
    Temperature_Initial =
    Temperature_Min =
    Temperature_K =
    Iteration_Max =
    SameCount_Max =
    Search_Max =

    # SOSP Parameters / Able to modify values
    muE =
    muR =
    muT =
    L =
    R =
    M = 999999

    # Neighborhood Type / (1) : Swap operator  (2) : Insert operator
    Nei =

    # SA_ANS
    JOBS,JOB_AT,REPS = build()
    result = start()
    print("<<<Final Result>>>")
    print("Final  Each  Tardiness =", result[0])
    print("Final Totals Tardiness =", result[1])