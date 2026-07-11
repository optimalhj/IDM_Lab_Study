import mysql.connector
from Case_Based_Reasoning_CaseGeneration_Initialization import user, password, db_name, case_database
from Case_Based_Reasoning_CaseGeneration_Repetition import params, max_num_job, correct_procedure, max_time
from numpy import random as rd
import matplotlib.pyplot as plt

def graph_makespan(process, setup, ini_set, seqs, machines):
    print(seqs)

def str_to_list(strings, forward_add = "", backward_add = ""):
    to_list = []
    for string in strings.split(", "):
        if "[" in string:
            new_string = string.replace("[", "")
        elif "]" in string:
            new_string = string.replace("]", "")
        else:
            new_string = string
        to_list.append(f"{forward_add}{new_string}{backward_add}")
    return to_list

def start(process, setup, p_prime, ini_set,  machines):
    conn = mysql.connector.connect(user=user, password=password, database=db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {case_database};")
    N_R = 100
    H = list(range(1, [i[0] for i in cursor][0] + 1))
    R = []
    sigma = N_R - len(H)

    cursor.execute(f"SELECT * FROM {case_database} ORDER BY {params["w"]} * alt + ({1 - params["w"]}) * awt ASC;")
    database = [row for row in cursor]
    for c in database:
        while len(R) < N_R:
            h, _, _, _= c
            if h in H:
                if c not in R: R.append(c)
                H.remove(h)
            elif sigma > 0:
                if c not in R: R.append(c)
                sigma -= 1
            else: break
    history = []
    for c in R:
        cursor.execute(f"SELECT job_type, op FROM s_o_{c[0]} ORDER BY info ASC")
        s_o, p, s_o_prime = [(jt, op) for jt, op in cursor], {jt : int(p) for jt, p in zip(list(ini_set), str_to_list(c[1]))}, []
        dij = {jt : {op : p_prime[jt] - p[jt] for op in ini_set[jt]["ops"].keys()} for jt in ini_set.keys()}
        for u in range(1, len(s_o) + 1):
            jt, op = s_o[len(s_o) - u]
            if dij[jt][op] < 0:
                dij[jt][op] += 1
            else:
                s_o_prime.insert(0, (jt, op))
                while dij[jt][op] > 0:
                    s_o_prime.insert(0, (jt, op))
                    dij[jt][op] -= 1
        delta = {jt : {job : 0 for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
        another_set = {jt : {op : [job for job in ini_set[jt]["jobs"]] for op in ini_set[jt]["ops"]} for jt in ini_set.keys()}
        f = {m : [0, ()] for m in machines}
        new_seq = []
        for u in range(1, len(s_o_prime) + 1):
            jt, op = s_o_prime[u - 1]
            job = another_set[jt][op].pop(0)
            horizon = max_time * len(s_o_prime)
            v, o_star, m_star = {}, "o", "m"
            for m in ini_set[jt]["ops"][op]:
                if len(f[m][1]) == 0:
                    v[m] = getattr(process, f"{jt}{op}")
                else:
                    prior_jt, prior_op = f[m][1]
                    v[m] = getattr(process, f"{jt}{op}") + getattr(setup, f"{prior_jt}{prior_op}{jt}{op}") + max(f[m][0], delta[jt][job])
                if horizon > v[m]:
                    o_star, m_star, horizon = (jt, job, op), m, v[m]

            f[m_star] = [horizon, (jt, op)]
            delta[jt][job] = horizon

            new_seq.append((o_star[0], o_star[1], o_star[2], m_star))
        history.append([new_seq, max(f[m][0] for m in machines)])
    conn.close()
    history.sort(key=lambda case:case[1])

    graph_makespan(process, setup, ini_set, history[0], machines)

class Duration:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass

def main():
    process, setup, ini_set = Duration(), SetUp(), {}
    conn = mysql.connector.connect(user=user, password=password, database=db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT job_type, op, process, machines FROM PROCESSES")
    for jt, op, process1, ms in cursor:
        setattr(process, f"{jt}{op}", process1)
        if jt not in ini_set: ini_set[jt] = {"ops" : {}, "jobs" : [f"Job{i}" for i in range(1, rd.randint(2, max_num_job + 1))] }
        ini_set[jt]["ops"][op] = str_to_list(ms, forward_add="M")
    cursor.execute(f"SELECT PRIOR_JT, PRIOR_OP, NOW_JT, NOW_OP, SETUP FROM SETUPS")
    for jt1, op1, jt2, op2, setup1 in [row for row in cursor]:
        setattr(setup, f"{jt1}{op1}{jt2}{op2}", setup1)
    cursor.execute(f"SELECT M FROM MACHINES")
    machines = [m[0] for m in cursor]
    conn.close()
    for jt in ini_set.keys():
        print(jt)
        for op in ini_set[jt]["ops"]:
            print("\t", op, ini_set[jt]["ops"][op])
    print("-"*50)
    p_prime = {jt:len(ini_set[jt]["jobs"]) for jt in ini_set.keys()}
    print(p_prime)
    start(process, setup, p_prime, ini_set, machines)


if __name__=="__main__":
    main()