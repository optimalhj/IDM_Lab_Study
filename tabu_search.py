from numpy import random as rd

def tardiness(case):
    now = 0
    total_tardiness = 0
    for op in case:
        now += op[1]
        op_td = max(0, now - op[2])
        total_tardiness += op_td
    return total_tardiness

def neighborhood(case):
    case = list(case)
    idx1, idx2 = rd.choice([i for i in range(len(case))], size=2, replace=False)
    case[idx1], case[idx2] = case[idx2], case[idx1]
    return tuple(case)

def main():
    num_iteration = 10
    num_trial = 6
    tabu_space = []
    data_set = {f"OP{i+1}" : (rd.randint(1,10), rd.randint(1,10)) for i in range(10)}
    tmp = list(data_set)
    using_set = []
    for _ in range(len(data_set)):
        op_name = tmp.pop(rd.randint(len(tmp)))
        using_set.append((op_name, data_set[op_name][0], data_set[op_name][1]))
    using_set = tuple(using_set)
    best_set = using_set

    for i in range(num_iteration):
        candidates = [neighborhood(using_set) for _ in range(num_trial)]
        for candidate in candidates:
            candidates[candidates.index(candidate)] = (candidate, tardiness(candidate))
        best_cand = min(candidates, key=lambda case:case[1])

        if best_cand in tabu_space:
            if best_cand[1] < tardiness(best_set):
                tabu_space.append(best_cand)
                using_set = best_cand[0]
        else:
            tabu_space.append(best_cand)
            using_set = best_cand[0]

        if tardiness() < tardiness(using_set)
    return 0


if __name__ == '__main__':
    main()