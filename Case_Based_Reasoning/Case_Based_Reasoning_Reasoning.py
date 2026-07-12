import mysql.connector
from Case_Based_Reasoning_CaseGeneration_Initialization import user, password, db_name, case_database
from Case_Based_Reasoning_CaseGeneration_Repetition import params, max_num_job, max_time
from numpy import random as rd
import matplotlib.pyplot as plt

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

def start(process, setup, p_prime, ini_set,  machines, N_R):
    conn = mysql.connector.connect(user=user, password=password, database=db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {case_database};")
    H ,R = list(range(1, [i[0] for i in cursor][0] + 1)), []
    sigma = N_R - len(H)

    cursor.execute(f"SELECT * FROM {case_database} ORDER BY {params["w"]} * alt + ({1 - params["w"]}) * awt ASC;")
    for c in [row for row in cursor]:
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
            if dij[jt][op] < 0: dij[jt][op] += 1
            else:
                s_o_prime.insert(0, (jt, op))
                while dij[jt][op] > 0:
                    s_o_prime.insert(0, (jt, op))
                    dij[jt][op] -= 1

        _, ax = plt.subplots()
        f, delta = {}, {(jt, job) : 0 for jt in ini_set.keys() for job in ini_set[jt]["jobs"]}
        for m in machines:
            f[m] = [0, ()]
            ax.barh(m, 0, left = 0)

        another_set, new_seq = {jt : {op : ini_set[jt]["jobs"].copy() for op in ini_set[jt]["ops"]} for jt in ini_set.keys()}, []
        for u in range(1, len(s_o_prime) + 1):
            jt, op = s_o_prime[u - 1]
            job = another_set[jt][op].pop(0)
            end, v, m_star, duration = max_time * len(s_o_prime), {}, "m", getattr(process, f"{jt}{op}")
            for m in ini_set[jt]["ops"][op]:
                v[m] = duration + getattr(setup, f"{f[m][1][0]}{f[m][1][1]}{jt}{op}") + max(f[m][0], delta[(jt, job)]) if len(f[m][1]) else duration + max(f[m][0], delta[(jt, job)])
                if end > v[m]: m_star, end = m, v[m]

            ax.barh(m_star, duration, left=end - duration, color=plt.get_cmap('tab20', len(delta))(list(delta).index((jt, job))), edgecolor='black')
            ax.text(end - duration / 2, m_star, f"{jt}\n{job}\n{op}\n({duration})", va='center', ha='center', color='black', fontsize=7)

            setup_time = getattr(setup, f"{f[m_star][1][0]}{f[m_star][1][1]}{jt}{op}") if len(f[m_star][1]) else 0
            if len(f[m_star][1]) and setup_time:
                ax.barh(m_star, setup_time, left=end - duration - setup_time, color='white', edgecolor='black')
                ax.text(end - duration - setup_time/2, m_star, f"({setup_time})", va='center', ha='center', color='black', fontsize=7)

            f[m_star], delta[(jt, job)] = [end, (jt, op)], end
            new_seq.append((jt, job, op, m_star))
        history.append([new_seq, max(f[m][0] for m in machines), len(history) + 1])

        ax.set_xticks([i for i in range(int(history[-1][1]) + 2)])
        ax.tick_params(axis='x', labelsize=5)
        ax.set_yticks(range(len(machines)))
        ax.set_yticklabels(machines)
        ax.set_xlabel("Time")
        ax.set_title(f"Makespan_Result({history[-1][2]})")
        plt.show()
    conn.close()
    history.sort(key=lambda case:case[1])
    print(f"({history[0][2]}) -> Makespan : {history[0][1]} / Sequence : {history[0][0]}")

class Duration:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass

def main():

    N_R = 10

    process, setup, ini_set = Duration(), SetUp(), {}
    conn = mysql.connector.connect(user=user, password=password, database=db_name)
    cursor = conn.cursor()

    cursor.execute(f"SELECT job_type, op, process, machines FROM PROCESSES")
    for jt, op, process1, ms in cursor:
        setattr(process, f"{jt}{op}", process1)
        if jt not in ini_set: ini_set[jt] = {"ops" : {}, "jobs" : [f"Job{i}" for i in range(1, rd.randint(2, max_num_job + 1))]}
        ini_set[jt]["ops"][op] = str_to_list(ms, forward_add="M")

    cursor.execute(f"SELECT PRIOR_JT, PRIOR_OP, NOW_JT, NOW_OP, SETUP FROM SETUPS")
    for jt1, op1, jt2, op2, setup1 in [row for row in cursor]: setattr(setup, f"{jt1}{op1}{jt2}{op2}", setup1)

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
    start(process, setup, p_prime, ini_set, machines, N_R)

if __name__=="__main__":
    main()