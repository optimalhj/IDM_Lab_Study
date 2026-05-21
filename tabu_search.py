from numpy import random as rd

class ATTR:
    def __init__(self):
        pass

def tardiness(case, attr):
    now = 0
    total_tardiness = 0
    for op in case:
        now += getattr(attr, f"{op}0")
        op_td = max(0, now - getattr(attr, f"{op}1"))
        total_tardiness += op_td
    return total_tardiness

def neighborhood(case,tabu_space):
    case = list(case)
    idx1, idx2 = sorted(rd.choice([i for i in range(len(case))], size=2, replace=False))
    for _ in range(10):
        if (idx1, idx2) in [(tabu[0], tabu[1]) for tabu in tabu_space]: idx1, idx2 = sorted(rd.choice([i for i in range(len(case))], size=2, replace=False))
        else: break

    case[idx1], case[idx2] = case[idx2], case[idx1]
    return tuple(case),idx1, idx2

def main():
    num_ops = 15
    num_iteration = 100
    num_trial = 10
    tabu_window = 8

    tabu_space = []
    attr = ATTR()
    tmp = []
    for i in range(num_ops):
        for j in range(2):
            setattr(attr, f"OP{i+1}{j}", rd.randint(1,10))
        tmp.append(f"OP{i+1}")

    using_set = [tmp.pop(rd.randint(len(tmp))) for _ in range(len(tmp))]
    using_set = tuple(using_set), tardiness(using_set, attr)
    best_set = using_set

    for i in range(num_iteration):
        candidates = [neighborhood(using_set[0], tabu_space) for _ in range(num_trial)]
        for candidate in candidates:
            candidate_set, idx1, idx2 = candidate
            candidates[candidates.index(candidate)] = candidate_set, tardiness(candidate_set, attr), int(idx1), int(idx2)
        best_cand = min(candidates, key=lambda case:case[1])
        print("Current :", using_set)
        print("Bestset :", best_set)
        print("BestCand:", best_cand,"\n")
        if best_cand[1] < best_set[1]:
            tabu_space.append([best_cand[2], best_cand[3], tabu_window])
            best_set, using_set = [(best_cand[0], best_cand[1]) for _ in range(2)]
            print("Improved and New Tabu", tabu_space)
        else:
            if (best_cand[2], best_cand[3]) not in tabu_space:
                tabu_space.append([best_cand[2], best_cand[3], tabu_window])
                using_set = best_cand[0], best_cand[1]
                print("Not improved, new current", tabu_space)

        delete_tabu_tmp = []
        for tabu in tabu_space:
            tabu[2] -= 1
            if tabu[2] == 0: delete_tabu_tmp.append(tabu)
        for tabu in delete_tabu_tmp: tabu_space.remove(tabu)
        print("Best :", best_set,"\n\n-------------\n")

    print(best_set)

if __name__ == '__main__':
    main()