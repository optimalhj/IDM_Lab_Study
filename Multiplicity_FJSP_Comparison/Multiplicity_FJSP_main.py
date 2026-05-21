import Multiplicity_FJSP_Comparison_modified
import Multiplicity_FJSP_Comparison_paper
import matplotlib.pyplot as plt
from numpy import random as rd

def start(durations,setups,machines):
    result_paper, result_new = Multiplicity_FJSP_Comparison_paper.start(durations, setups, machines), Multiplicity_FJSP_Comparison_modified.start(durations,setups,machines)
    if result_paper[0] == result_new[0]:
        print(f"From Paper : {result_paper[1]}s")
        print(f"From New : {result_new[1]}s\n")
    else:
        print("Something is wrong")
        print(f"Result_New : {result_new[0]} vs Result_Paper : {result_paper[0]}")
        print("From New\n" if result_new[0] > result_paper[0] else "From Paper\n")
    return result_paper, result_new

def main():

    num_comparison = 10
    # Parameter Input
    num_job_types = 2
    max_num_job = 3
    max_num_op = 3
    num_machines = 3
    max_time = 6
    max_setup_time = max(max_time // 2, 1)

    results, win_count = {"paper" : [], "new" : [], "duration_competition" : {}}, {"paper" : 0, "new" : 0}
    for i in range(num_comparison):
        machines = [f"M{i}" for i in range(1, num_machines + 1)]
        durations = {job_type: {"jobs": [f"Job{j + 1}" for j in range(rd.randint(2, max_num_job + 1))],
                                "ops": {f"Op{o + 1}":
                                            [sorted(rd.choice(machines, size=rd.randint(1, len(machines)), replace=False),
                                                    key=lambda m: machines.index(m)),
                                             rd.randint(2, max_num_op + 1)]
                                        for o in range(rd.randint(1, max_num_op + 1))}}
                     for job_type in [f"Job_Type{i + 1}" for i in range(rd.randint(2, num_job_types + 1))]}

        every_op = [(job_type, op) for job_type in durations.keys() for op in
                    durations[job_type][list(durations[job_type])[1]]]
        setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max_setup_time + 1) for op2 in every_op} for op1 in
                  every_op}

        print(f"{i+1}th Comparison\ndurations = ", durations)
        print("setups = ", setups)
        print("machines = ", machines,"\n")

        result_paper, result_new = start(durations, setups, machines)
        results["paper"].append(result_paper[1])
        results["new"].append(result_new[1])

        if result_new[1] > result_paper[1]:
            win_count["paper"] += 1
        else:
            win_count["new"] += 1

        if result_new[0] == result_paper[0]:
            pass
        elif result_new[0] > result_paper[0]:
            results["duration_competition"][f"f{i+1}"]= "Paper win"
        else:
            results["duration_competition"][f"f{i+1}"]= "New win"

    for result in ["paper", "new"]:
        plt.plot(range(1, num_comparison + 1), results[result], linestyle="--", marker="o", label=result)
    plt.xticks([i for i in range(1, num_comparison + 1)])
    plt.xlabel("Number of Comparisons")
    plt.ylabel("Operating Duration(seconds)")
    plt.title("Comparison : Paper vs New")
    plt.legend()
    plt.show()
    print(results["duration_competition"])
    print("Win Count")
    print(f"Total {num_comparison} Comparisons / {win_count}")

if __name__ == '__main__':
    main()