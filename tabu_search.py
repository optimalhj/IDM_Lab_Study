from numpy import random as rd

class ATTR:
    def __init__(self):
        pass

def tardiness(case, attr):
    now = 0
    total_tardiness = 0
    for op in case:
        now += getattr(attr, f"{op}0")
        op_td = max(0, now - getattr(attr, f"{op}0"))
        total_tardiness += op_td
    return total_tardiness

def neighborhood(case):
    case = list(case)
    idx1, idx2 = sorted(rd.choice([i for i in range(len(case))], size=2, replace=False))
    case[idx1], case[idx2] = case[idx2], case[idx1]
    return tuple(case),idx1, idx2

def main():
    num_ops = 10
    num_iteration = 10
    num_trial = 6

    tabu_space = []
    attr = ATTR()
    tmp = []
    for i in range(num_ops):
        for j in range(2):
            setattr(attr, f"OP{i+1}{j}", rd.randint(1,10))
        tmp.append(f"OP{i+1}")

    using_set = []
    for _ in range(len(tmp)):
        op_name = tmp.pop(rd.randint(len(tmp)))
        using_set.append(op_name)
    using_set = tuple(using_set), tardiness(using_set, attr)
    best_set = using_set

    for i in range(num_iteration):
        candidates = [neighborhood(using_set[0]) for _ in range(num_trial)]
        for candidate in candidates:
            candidate_set, idx1, idx2 = candidate
            candidates[candidates.index(candidate)] = candidate_set, tardiness(candidate_set, attr), int(idx1), int(idx2)
        best_cand = min(candidates, key=lambda case:case[1])
        if (best_cand[2], best_cand[3]) in tabu_space:
            if best_cand[1] < best_set[1]:
                tabu_space.append((best_cand[2], best_cand[3]))
                using_set = best_cand[0], best_cand[1]
        else:
            tabu_space.append((best_cand[2], best_cand[3]))
            using_set = best_cand[0], best_cand[1]

        if using_set[1] < best_set[1]:
            best_set = using_set[0],using_set[1]
        print(tabu_space)
        print("Best :", best_set)

    print(best_set)

if __name__ == '__main__':
    main()