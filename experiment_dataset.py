# comparison.py 의 start(boms, factories, holding_cost, deliveries, trucks, params) 입력용 실험 조합 30 가지 (데이터 전용, 뒤로 갈수록 복잡 : Factory 3 → 7, JT 3 → 10)
# params["weights"] 는 모든 조합에서 동일, deliveries 는 comparison.py 처럼 별도로 생성

repetition = 5

datasets = [
    # ---------------- case 1 : Factory 3, JT 3, Truck 3 ----------------
    {
        "params": {"final_product": ["JT10"], "amount": [1], "float_unit": ["JT4"],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT10": {"JT4": 2, "JT8": 1}},
        "factories": {
            "Fc1": {
                "JT10": {"lots": [1], "time": 2}},
            "Fc2": {
                "JT8": {"lots": [1], "time": 2}},
            "Fc3": {
                "JT4": {"lots": [1], "time": 2}}},
        "holding_cost": {"JT4": 2, "JT8": 2, "JT10": 7},
        "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 5}, "tr3": {"cap": 5}}},
    # ---------------- case 2 : Factory 3, JT 3, Truck 3 ----------------
    {
        "params": {"final_product": ["JT14"], "amount": [1], "float_unit": [],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT14": {"JT3": 1, "JT12": 2}},
        "factories": {
            "Fc1": {
                "JT12": {"lots": [1], "time": 1}},
            "Fc2": {
                "JT3": {"lots": [1], "time": 2}},
            "Fc3": {
                "JT3": {"lots": [1], "time": 2},
                "JT14": {"lots": [1], "time": 2}}},
        "holding_cost": {"JT3": 1, "JT12": 2, "JT14": 4},
        "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 5}}},
    # ---------------- case 3 : Factory 3, JT 3, Truck 2 ----------------
    {
        "params": {"final_product": ["JT15"], "amount": [1], "float_unit": [],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT15": {"JT8": 2, "JT11": 2}},
        "factories": {
            "Fc1": {
                "JT8": {"lots": [1], "time": 2}},
            "Fc2": {
                "JT15": {"lots": [1], "time": 3}},
            "Fc3": {
                "JT11": {"lots": [1], "time": 1}}},
        "holding_cost": {"JT8": 2, "JT11": 1, "JT15": 4},
        "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 10}}},
    # ---------------- case 4 : Factory 3, JT 4, Truck 2 ----------------
    {
        "params": {"final_product": ["JT14"], "amount": [1], "float_unit": ["JT14"],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT11": {"JT9": 1},
            "JT14": {"JT3": 2, "JT11": 1}},
        "factories": {
            "Fc1": {
                "JT3": {"lots": [1], "time": 2}},
            "Fc2": {
                "JT11": {"lots": [1, 3], "time": 3}},
            "Fc3": {
                "JT9": {"lots": [1], "time": 2},
                "JT14": {"lots": [1], "time": 3}}},
        "holding_cost": {"JT3": 2, "JT9": 2, "JT11": 2, "JT14": 5},
        "trucks": {"tr1": {"cap": 8}, "tr2": {"cap": 5}}},
    # ---------------- case 5 : Factory 4, JT 4, Truck 3 ----------------
    {
        "params": {"final_product": ["JT12"], "amount": [1], "float_unit": ["JT12"],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT10": {"JT2": 1, "JT8": 1},
            "JT12": {"JT8": 2, "JT10": 1}},
        "factories": {
            "Fc1": {
                "JT2": {"lots": [1], "time": 2}},
            "Fc2": {
                "JT8": {"lots": [1], "time": 2}},
            "Fc3": {
                "JT10": {"lots": [1], "time": 2}},
            "Fc4": {
                "JT12": {"lots": [1], "time": 4}}},
        "holding_cost": {"JT2": 1, "JT8": 2, "JT10": 6, "JT12": 11},
        "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 10}, "tr3": {"cap": 8}}},
    # ---------------- case 6 : Factory 4, JT 4, Truck 4 ----------------
    {
        "params": {"final_product": ["JT10"], "amount": [1], "float_unit": ["JT5"],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT6": {"JT4": 1},
            "JT10": {"JT5": 1, "JT6": 2}},
        "factories": {
            "Fc1": {
                "JT4": {"lots": [1], "time": 1}},
            "Fc2": {
                "JT10": {"lots": [1], "time": 3}},
            "Fc3": {
                "JT5": {"lots": [1], "time": 2}},
            "Fc4": {
                "JT6": {"lots": [1, 2], "time": 2}}},
        "holding_cost": {"JT4": 2, "JT5": 1, "JT6": 3, "JT10": 4},
        "trucks": {"tr1": {"cap": 8}, "tr2": {"cap": 8}, "tr3": {"cap": 8}, "tr4": {"cap": 3}}},
    # ---------------- case 7 : Factory 4, JT 4, Truck 4 ----------------
    {
        "params": {"final_product": ["JT15"], "amount": [1], "float_unit": ["JT3"],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT8": {"JT2": 2, "JT3": 2},
            "JT15": {"JT3": 1, "JT8": 1}},
        "factories": {
            "Fc1": {
                "JT3": {"lots": [1], "time": 2}},
            "Fc2": {
                "JT8": {"lots": [1], "time": 2}},
            "Fc3": {
                "JT15": {"lots": [1], "time": 4}},
            "Fc4": {
                "JT2": {"lots": [1, 3], "time": 2}}},
        "holding_cost": {"JT2": 1, "JT3": 1, "JT8": 3, "JT15": 4},
        "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 5}, "tr4": {"cap": 3}}},
    # ---------------- case 8 : Factory 4, JT 5, Truck 4 ----------------
    {
        "params": {"final_product": ["JT7", "JT10"], "amount": [1, 1], "float_unit": [],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT5": {"JT3": 1},
            "JT7": {"JT2": 1},
            "JT10": {"JT3": 2, "JT5": 1}},
        "factories": {
            "Fc1": {
                "JT10": {"lots": [1], "time": 4}},
            "Fc2": {
                "JT5": {"lots": [1], "time": 2}},
            "Fc3": {
                "JT3": {"lots": [1], "time": 1}},
            "Fc4": {
                "JT2": {"lots": [1], "time": 2},
                "JT7": {"lots": [1], "time": 3}}},
        "holding_cost": {"JT2": 1, "JT3": 1, "JT5": 2, "JT7": 2, "JT10": 5},
        "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 5}, "tr4": {"cap": 3}}},
    # ---------------- case 9 : Factory 4, JT 5, Truck 4 ----------------
    {
        "params": {"final_product": ["JT14", "JT15"], "amount": [1, 1], "float_unit": [],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT8": {"JT2": 1, "JT3": 1},
            "JT14": {"JT2": 2, "JT3": 2, "JT8": 1},
            "JT15": {"JT8": 1}},
        "factories": {
            "Fc1": {
                "JT2": {"lots": [1, 2], "time": 2},
                "JT14": {"lots": [1], "time": 4},
                "JT15": {"lots": [1], "time": 4}},
            "Fc2": {
                "JT8": {"lots": [1], "time": 3},
                "JT15": {"lots": [1], "time": 3}},
            "Fc3": {
                "JT2": {"lots": [1], "time": 1}},
            "Fc4": {
                "JT3": {"lots": [1], "time": 1},
                "JT15": {"lots": [1], "time": 4}}},
        "holding_cost": {"JT2": 2, "JT3": 1, "JT8": 6, "JT14": 11, "JT15": 9},
        "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 5}, "tr4": {"cap": 5}}},
    # ---------------- case 10 : Factory 4, JT 5, Truck 4 ----------------
    {
        "params": {"final_product": ["JT8", "JT13"], "amount": [2, 2], "float_unit": [],
                   "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
        "boms": {
            "JT7": {"JT5": 1},
            "JT8": {"JT3": 1, "JT7": 1},
            "JT13": {"JT5": 2, "JT7": 1}},
        "factories": {
            "Fc1": {
                "JT5": {"lots": [1], "time": 1},
                "JT8": {"lots": [1], "time": 3}},
            "Fc2": {
                "JT3": {"lots": [1], "time": 2}},
            "Fc3": {
                "JT13": {"lots": [1], "time": 4}},
            "Fc4": {
                "JT5": {"lots": [1, 2], "time": 1},
                "JT7": {"lots": [1], "time": 3}}},
        "holding_cost": {"JT3": 2, "JT5": 2, "JT7": 3, "JT8": 7, "JT13": 5},
        "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 5}, "tr3": {"cap": 5}, "tr4": {"cap": 3}}},
    # ---------------- case 11 : Factory 4, JT 5, Truck 4 ----------------
    # {
    #     "params": {"final_product": ["JT10", "JT13"], "amount": [2, 1], "float_unit": ["JT2"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT9": {"JT2": 1, "JT7": 1},
    #         "JT10": {"JT2": 1, "JT9": 1},
    #         "JT13": {"JT7": 1, "JT10": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT2": {"lots": [1], "time": 2},
    #             "JT10": {"lots": [1], "time": 4}},
    #         "Fc2": {
    #             "JT9": {"lots": [1], "time": 3},
    #             "JT10": {"lots": [1], "time": 3},
    #             "JT13": {"lots": [1], "time": 4}},
    #         "Fc3": {
    #             "JT10": {"lots": [1], "time": 3}},
    #         "Fc4": {
    #             "JT7": {"lots": [1], "time": 1},
    #             "JT13": {"lots": [1], "time": 5}}},
    #     "holding_cost": {"JT2": 1, "JT7": 2, "JT9": 5, "JT10": 8, "JT13": 10},
    #     "trucks": {"tr1": {"cap": 5}, "tr2": {"cap": 3}, "tr3": {"cap": 3}, "tr4": {"cap": 3}}},
    # # ---------------- case 12 : Factory 5, JT 6, Truck 5 ----------------
    # {
    #     "params": {"final_product": ["JT14", "JT15"], "amount": [2, 1], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT10": {"JT9": 1},
    #         "JT13": {"JT4": 2, "JT9": 1, "JT10": 1},
    #         "JT14": {"JT4": 1, "JT13": 1},
    #         "JT15": {"JT4": 1, "JT13": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT4": {"lots": [1], "time": 1},
    #             "JT15": {"lots": [1], "time": 4}},
    #         "Fc2": {
    #             "JT14": {"lots": [1], "time": 5},
    #             "JT15": {"lots": [1], "time": 5}},
    #         "Fc3": {
    #             "JT4": {"lots": [1], "time": 2},
    #             "JT9": {"lots": [1, 2], "time": 2},
    #             "JT10": {"lots": [1], "time": 3}},
    #         "Fc4": {
    #             "JT13": {"lots": [1, 3], "time": 4},
    #             "JT15": {"lots": [1], "time": 5}},
    #         "Fc5": {
    #             "JT9": {"lots": [1], "time": 2},
    #             "JT13": {"lots": [1, 2], "time": 4},
    #             "JT14": {"lots": [1], "time": 4}}},
    #     "holding_cost": {"JT4": 2, "JT9": 2, "JT10": 4, "JT13": 10, "JT14": 14, "JT15": 13},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 10}, "tr3": {"cap": 8}, "tr4": {"cap": 5}, "tr5": {"cap": 3}}},
    # # ---------------- case 13 : Factory 5, JT 6, Truck 5 ----------------
    # {
    #     "params": {"final_product": ["JT10", "JT14"], "amount": [2, 1], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT8": {"JT2": 2, "JT6": 2},
    #         "JT9": {"JT2": 2},
    #         "JT10": {"JT6": 1, "JT8": 1, "JT9": 2},
    #         "JT14": {"JT2": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT2": {"lots": [1], "time": 1},
    #             "JT9": {"lots": [1], "time": 2}},
    #         "Fc2": {
    #             "JT8": {"lots": [1], "time": 2},
    #             "JT10": {"lots": [1], "time": 3}},
    #         "Fc3": {
    #             "JT6": {"lots": [1], "time": 2},
    #             "JT8": {"lots": [1], "time": 3},
    #             "JT14": {"lots": [1], "time": 2}},
    #         "Fc4": {
    #             "JT8": {"lots": [1, 3], "time": 3}},
    #         "Fc5": {
    #             "JT2": {"lots": [1, 2], "time": 2},
    #             "JT6": {"lots": [1, 2], "time": 1}}},
    #     "holding_cost": {"JT2": 1, "JT6": 1, "JT8": 4, "JT9": 3, "JT10": 9, "JT14": 4},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 10}, "tr3": {"cap": 5}, "tr4": {"cap": 5}, "tr5": {"cap": 3}}},
    # # ---------------- case 14 : Factory 5, JT 6, Truck 5 ----------------
    # {
    #     "params": {"final_product": ["JT13", "JT14"], "amount": [1, 1], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT11": {"JT3": 2},
    #         "JT12": {"JT3": 1, "JT9": 1},
    #         "JT13": {"JT9": 2, "JT11": 1, "JT12": 1},
    #         "JT14": {"JT3": 1, "JT11": 3, "JT12": 3}},
    #     "factories": {
    #         "Fc1": {
    #             "JT3": {"lots": [1, 3], "time": 2},
    #             "JT9": {"lots": [1], "time": 1}},
    #         "Fc2": {
    #             "JT3": {"lots": [1, 3], "time": 1}},
    #         "Fc3": {
    #             "JT12": {"lots": [1, 3], "time": 3}},
    #         "Fc4": {
    #             "JT13": {"lots": [1], "time": 3}},
    #         "Fc5": {
    #             "JT11": {"lots": [1], "time": 2},
    #             "JT13": {"lots": [1], "time": 4},
    #             "JT14": {"lots": [1], "time": 4}}},
    #     "holding_cost": {"JT3": 1, "JT9": 2, "JT11": 1, "JT12": 6, "JT13": 11, "JT14": 9},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 10}, "tr3": {"cap": 10}, "tr4": {"cap": 5}, "tr5": {"cap": 3}}},
    # # ---------------- case 15 : Factory 5, JT 6, Truck 5 ----------------
    # {
    #     "params": {"final_product": ["JT9", "JT10"], "amount": [1, 2], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT5": {"JT4": 1},
    #         "JT8": {"JT4": 3, "JT5": 3},
    #         "JT9": {"JT1": 1, "JT4": 2, "JT8": 1},
    #         "JT10": {"JT1": 2, "JT5": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT4": {"lots": [1], "time": 2}},
    #         "Fc2": {
    #             "JT9": {"lots": [1], "time": 5}},
    #         "Fc3": {
    #             "JT1": {"lots": [1, 2], "time": 2},
    #             "JT4": {"lots": [1, 3], "time": 2},
    #             "JT5": {"lots": [1], "time": 3},
    #             "JT10": {"lots": [1], "time": 4}},
    #         "Fc4": {
    #             "JT8": {"lots": [1, 3], "time": 3},
    #             "JT9": {"lots": [1], "time": 4}},
    #         "Fc5": {
    #             "JT1": {"lots": [1], "time": 1},
    #             "JT8": {"lots": [1], "time": 3}}},
    #     "holding_cost": {"JT1": 2, "JT4": 2, "JT5": 4, "JT8": 6, "JT9": 11, "JT10": 8},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 10}, "tr3": {"cap": 8}, "tr4": {"cap": 8}, "tr5": {"cap": 5}}},
    # # ---------------- case 16 : Factory 5, JT 7, Truck 4 ----------------
    # {
    #     "params": {"final_product": ["JT13", "JT15"], "amount": [1, 1], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT4": {"JT2": 2},
    #         "JT5": {"JT4": 1},
    #         "JT10": {"JT3": 1, "JT5": 2},
    #         "JT13": {"JT2": 1},
    #         "JT15": {"JT10": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT2": {"lots": [1], "time": 2},
    #             "JT5": {"lots": [1], "time": 3}},
    #         "Fc2": {
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT10": {"lots": [1], "time": 5}},
    #         "Fc3": {
    #             "JT3": {"lots": [1], "time": 2},
    #             "JT4": {"lots": [1], "time": 3},
    #             "JT10": {"lots": [1, 3], "time": 4}},
    #         "Fc4": {
    #             "JT5": {"lots": [1, 3], "time": 4},
    #             "JT13": {"lots": [1], "time": 2}},
    #         "Fc5": {
    #             "JT13": {"lots": [1], "time": 3},
    #             "JT15": {"lots": [1], "time": 6}}},
    #     "holding_cost": {"JT2": 2, "JT3": 2, "JT4": 3, "JT5": 6, "JT10": 11, "JT13": 4, "JT15": 13},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 10}, "tr3": {"cap": 8}, "tr4": {"cap": 5}}},
    # # ---------------- case 17 : Factory 5, JT 7, Truck 5 ----------------
    # {
    #     "params": {"final_product": ["JT8", "JT9"], "amount": [1, 1], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT3": {"JT1": 2, "JT2": 2},
    #         "JT5": {"JT3": 2},
    #         "JT6": {"JT2": 2},
    #         "JT8": {"JT5": 1, "JT6": 3},
    #         "JT9": {"JT3": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT1": {"lots": [1, 2], "time": 2},
    #             "JT2": {"lots": [1, 2], "time": 2}},
    #         "Fc2": {
    #             "JT2": {"lots": [1], "time": 1},
    #             "JT5": {"lots": [1], "time": 3}},
    #         "Fc3": {
    #             "JT2": {"lots": [1, 3], "time": 2},
    #             "JT6": {"lots": [1], "time": 3},
    #             "JT9": {"lots": [1], "time": 3}},
    #         "Fc4": {
    #             "JT8": {"lots": [1], "time": 4}},
    #         "Fc5": {
    #             "JT3": {"lots": [1], "time": 2}}},
    #     "holding_cost": {"JT1": 2, "JT2": 2, "JT3": 7, "JT5": 9, "JT6": 4, "JT8": 15, "JT9": 9},
    #     "trucks": {"tr1": {"cap": 8}, "tr2": {"cap": 8}, "tr3": {"cap": 5}, "tr4": {"cap": 5}, "tr5": {"cap": 3}}},
    # # ---------------- case 18 : Factory 5, JT 7, Truck 5 ----------------
    # {
    #     "params": {"final_product": ["JT13", "JT15"], "amount": [1, 1], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT6": {"JT1": 2, "JT5": 2},
    #         "JT11": {"JT1": 2},
    #         "JT12": {"JT5": 1, "JT6": 1, "JT11": 3},
    #         "JT13": {"JT1": 1},
    #         "JT15": {"JT1": 2, "JT12": 1, "JT13": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT1": {"lots": [1], "time": 2},
    #             "JT15": {"lots": [1], "time": 5}},
    #         "Fc2": {
    #             "JT5": {"lots": [1], "time": 2},
    #             "JT6": {"lots": [1], "time": 2}},
    #         "Fc3": {
    #             "JT13": {"lots": [1], "time": 2}},
    #         "Fc4": {
    #             "JT1": {"lots": [1, 2], "time": 1},
    #             "JT5": {"lots": [1], "time": 1},
    #             "JT6": {"lots": [1, 3], "time": 3},
    #             "JT12": {"lots": [1, 2], "time": 3}},
    #         "Fc5": {
    #             "JT11": {"lots": [1, 3], "time": 3},
    #             "JT12": {"lots": [1], "time": 4},
    #             "JT13": {"lots": [1], "time": 2}}},
    #     "holding_cost": {"JT1": 2, "JT5": 2, "JT6": 5, "JT11": 2, "JT12": 11, "JT13": 2, "JT15": 16},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 8}, "tr4": {"cap": 8}, "tr5": {"cap": 5}}},
    # # ---------------- case 19 : Factory 5, JT 7, Truck 4 ----------------
    # {
    #     "params": {"final_product": ["JT14", "JT15"], "amount": [2, 2], "float_unit": ["JT2", "JT15"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT3": {"JT2": 1},
    #         "JT4": {"JT1": 2, "JT2": 1},
    #         "JT13": {"JT2": 2},
    #         "JT14": {"JT2": 2, "JT13": 2},
    #         "JT15": {"JT3": 2, "JT4": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT4": {"lots": [1], "time": 2},
    #             "JT14": {"lots": [1], "time": 4}},
    #         "Fc2": {
    #             "JT2": {"lots": [1], "time": 1},
    #             "JT4": {"lots": [1, 2], "time": 3},
    #             "JT13": {"lots": [1], "time": 2}},
    #         "Fc3": {
    #             "JT2": {"lots": [1, 2], "time": 2},
    #             "JT3": {"lots": [1], "time": 3},
    #             "JT14": {"lots": [1], "time": 3}},
    #         "Fc4": {
    #             "JT13": {"lots": [1], "time": 3},
    #             "JT15": {"lots": [1], "time": 3}},
    #         "Fc5": {
    #             "JT1": {"lots": [1], "time": 2},
    #             "JT3": {"lots": [1, 2], "time": 2},
    #             "JT4": {"lots": [1, 2], "time": 3},
    #             "JT14": {"lots": [1], "time": 4}}},
    #     "holding_cost": {"JT1": 1, "JT2": 1, "JT3": 1, "JT4": 5, "JT13": 1, "JT14": 4, "JT15": 6},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 5}, "tr4": {"cap": 5}}},
    # # ---------------- case 20 : Factory 6, JT 8, Truck 5 ----------------
    # {
    #     "params": {"final_product": ["JT10", "JT13"], "amount": [1, 1], "float_unit": ["JT8"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT7": {"JT2": 2, "JT4": 2, "JT5": 1},
    #         "JT8": {"JT4": 1, "JT5": 1},
    #         "JT9": {"JT4": 2},
    #         "JT10": {"JT4": 2, "JT7": 1, "JT8": 2},
    #         "JT13": {"JT9": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT4": {"lots": [1, 2], "time": 1},
    #             "JT8": {"lots": [1, 3], "time": 2},
    #             "JT10": {"lots": [1], "time": 3}},
    #         "Fc2": {
    #             "JT2": {"lots": [1], "time": 2},
    #             "JT4": {"lots": [1], "time": 1},
    #             "JT13": {"lots": [1], "time": 3}},
    #         "Fc3": {
    #             "JT7": {"lots": [1], "time": 3},
    #             "JT9": {"lots": [1], "time": 3},
    #             "JT10": {"lots": [1], "time": 3}},
    #         "Fc4": {
    #             "JT4": {"lots": [1, 3], "time": 1},
    #             "JT8": {"lots": [1], "time": 2},
    #             "JT10": {"lots": [1], "time": 4},
    #             "JT13": {"lots": [1], "time": 3}},
    #         "Fc5": {
    #             "JT4": {"lots": [1], "time": 1},
    #             "JT7": {"lots": [1], "time": 3},
    #             "JT8": {"lots": [1], "time": 2}},
    #         "Fc6": {
    #             "JT5": {"lots": [1], "time": 2},
    #             "JT10": {"lots": [1], "time": 4}}},
    #     "holding_cost": {"JT2": 1, "JT4": 1, "JT5": 1, "JT7": 4, "JT8": 4, "JT9": 1, "JT10": 12, "JT13": 1},
    #     "trucks": {"tr1": {"cap": 8}, "tr2": {"cap": 5}, "tr3": {"cap": 5}, "tr4": {"cap": 5}, "tr5": {"cap": 3}}},
    # # ---------------- case 21 : Factory 6, JT 8, Truck 6 ----------------
    # {
    #     "params": {"final_product": ["JT12", "JT15"], "amount": [1, 1], "float_unit": ["JT3", "JT10"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT7": {"JT2": 1, "JT3": 2, "JT4": 1},
    #         "JT9": {"JT2": 3, "JT3": 2},
    #         "JT10": {"JT2": 2, "JT3": 1, "JT9": 1},
    #         "JT12": {"JT4": 2, "JT10": 1},
    #         "JT15": {"JT4": 1, "JT7": 1, "JT10": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT9": {"lots": [1], "time": 3},
    #             "JT10": {"lots": [1], "time": 4},
    #             "JT15": {"lots": [1], "time": 4}},
    #         "Fc2": {
    #             "JT2": {"lots": [1], "time": 2},
    #             "JT10": {"lots": [1, 2], "time": 3},
    #             "JT12": {"lots": [1], "time": 4}},
    #         "Fc3": {
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT9": {"lots": [1], "time": 3}},
    #         "Fc4": {
    #             "JT4": {"lots": [1], "time": 2},
    #             "JT7": {"lots": [1], "time": 2}},
    #         "Fc5": {
    #             "JT3": {"lots": [1, 3], "time": 2},
    #             "JT4": {"lots": [1, 3], "time": 1}},
    #         "Fc6": {
    #             "JT3": {"lots": [1, 2], "time": 2},
    #             "JT7": {"lots": [1, 2], "time": 3},
    #             "JT9": {"lots": [1], "time": 3},
    #             "JT10": {"lots": [1], "time": 4},
    #             "JT15": {"lots": [1], "time": 4}}},
    #     "holding_cost": {"JT2": 1, "JT3": 1, "JT4": 1, "JT7": 3, "JT9": 3, "JT10": 6, "JT12": 9, "JT15": 13},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 5}, "tr4": {"cap": 5}, "tr5": {"cap": 5}, "tr6": {"cap": 3}}},
    # # ---------------- case 22 : Factory 6, JT 8, Truck 6 ----------------
    # {
    #     "params": {"final_product": ["JT11", "JT14"], "amount": [1, 1], "float_unit": ["JT7", "JT11"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT5": {"JT3": 1, "JT4": 1},
    #         "JT7": {"JT1": 1},
    #         "JT9": {"JT1": 1, "JT7": 1},
    #         "JT11": {"JT4": 1, "JT5": 1, "JT9": 3},
    #         "JT14": {"JT3": 1, "JT4": 1, "JT7": 2}},
    #     "factories": {
    #         "Fc1": {
    #             "JT3": {"lots": [1, 3], "time": 1},
    #             "JT4": {"lots": [1], "time": 1},
    #             "JT7": {"lots": [1], "time": 3},
    #             "JT11": {"lots": [1], "time": 5},
    #             "JT14": {"lots": [1], "time": 3}},
    #         "Fc2": {
    #             "JT4": {"lots": [1, 3], "time": 2}},
    #         "Fc3": {
    #             "JT9": {"lots": [1, 3], "time": 4}},
    #         "Fc4": {
    #             "JT1": {"lots": [1], "time": 2},
    #             "JT7": {"lots": [1], "time": 2},
    #             "JT9": {"lots": [1], "time": 3},
    #             "JT11": {"lots": [1], "time": 5}},
    #         "Fc5": {
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT11": {"lots": [1], "time": 4},
    #             "JT14": {"lots": [1], "time": 3}},
    #         "Fc6": {
    #             "JT5": {"lots": [1], "time": 3},
    #             "JT11": {"lots": [1], "time": 5}}},
    #     "holding_cost": {"JT1": 1, "JT3": 1, "JT4": 2, "JT5": 3, "JT7": 1, "JT9": 4, "JT11": 10, "JT14": 4},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 8}, "tr4": {"cap": 5}, "tr5": {"cap": 5}, "tr6": {"cap": 3}}},
    # # ---------------- case 23 : Factory 6, JT 8, Truck 5 ----------------
    # {
    #     "params": {"final_product": ["JT14", "JT15"], "amount": [2, 1], "float_unit": ["JT4"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT4": {"JT1": 1, "JT2": 2, "JT3": 1},
    #         "JT5": {"JT1": 1},
    #         "JT13": {"JT2": 1, "JT4": 1, "JT5": 2},
    #         "JT14": {"JT1": 2, "JT5": 1},
    #         "JT15": {"JT1": 2, "JT2": 2, "JT3": 1, "JT13": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT3": {"lots": [1, 2], "time": 2},
    #             "JT4": {"lots": [1], "time": 2},
    #             "JT13": {"lots": [1, 2], "time": 3},
    #             "JT15": {"lots": [1], "time": 4}},
    #         "Fc2": {
    #             "JT14": {"lots": [1], "time": 3}},
    #         "Fc3": {
    #             "JT4": {"lots": [1], "time": 2},
    #             "JT5": {"lots": [1, 2], "time": 2},
    #             "JT15": {"lots": [1], "time": 4}},
    #         "Fc4": {
    #             "JT1": {"lots": [1], "time": 1},
    #             "JT5": {"lots": [1], "time": 3}},
    #         "Fc5": {
    #             "JT2": {"lots": [1], "time": 2},
    #             "JT13": {"lots": [1], "time": 3}},
    #         "Fc6": {
    #             "JT1": {"lots": [1, 3], "time": 2},
    #             "JT13": {"lots": [1], "time": 3},
    #             "JT14": {"lots": [1], "time": 3},
    #             "JT15": {"lots": [1], "time": 4}}},
    #     "holding_cost": {"JT1": 1, "JT2": 1, "JT3": 1, "JT4": 3, "JT5": 2, "JT13": 7, "JT14": 6, "JT15": 10},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 10}, "tr3": {"cap": 5}, "tr4": {"cap": 3}, "tr5": {"cap": 3}}},
    # # ---------------- case 24 : Factory 6, JT 9, Truck 6 ----------------
    # {
    #     "params": {"final_product": ["JT14", "JT15"], "amount": [1, 1], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT9": {"JT7": 2, "JT8": 1},
    #         "JT10": {"JT9": 2},
    #         "JT12": {"JT6": 2, "JT9": 1},
    #         "JT13": {"JT6": 1},
    #         "JT14": {"JT6": 3, "JT7": 1, "JT10": 1, "JT12": 2},
    #         "JT15": {"JT13": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT12": {"lots": [1], "time": 3}},
    #         "Fc2": {
    #             "JT14": {"lots": [1], "time": 4},
    #             "JT15": {"lots": [1], "time": 3}},
    #         "Fc3": {
    #             "JT7": {"lots": [1], "time": 1},
    #             "JT8": {"lots": [1, 2], "time": 1},
    #             "JT10": {"lots": [1], "time": 4}},
    #         "Fc4": {
    #             "JT6": {"lots": [1], "time": 1},
    #             "JT7": {"lots": [1], "time": 2},
    #             "JT8": {"lots": [1], "time": 1},
    #             "JT13": {"lots": [1], "time": 2},
    #             "JT14": {"lots": [1], "time": 4}},
    #         "Fc5": {
    #             "JT6": {"lots": [1], "time": 2},
    #             "JT8": {"lots": [1, 2], "time": 2},
    #             "JT13": {"lots": [1, 3], "time": 2}},
    #         "Fc6": {
    #             "JT7": {"lots": [1, 2], "time": 1},
    #             "JT9": {"lots": [1], "time": 3},
    #             "JT12": {"lots": [1], "time": 3}}},
    #     "holding_cost": {"JT6": 2, "JT7": 1, "JT8": 2, "JT9": 6, "JT10": 6, "JT12": 10, "JT13": 3, "JT14": 20, "JT15": 5},
    #     "trucks": {"tr1": {"cap": 8}, "tr2": {"cap": 5}, "tr3": {"cap": 5}, "tr4": {"cap": 5}, "tr5": {"cap": 3}, "tr6": {"cap": 3}}},
    # # ---------------- case 25 : Factory 6, JT 9, Truck 6 ----------------
    # {
    #     "params": {"final_product": ["JT13", "JT14"], "amount": [1, 2], "float_unit": ["JT6"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT6": {"JT3": 1},
    #         "JT7": {"JT1": 1, "JT3": 1, "JT4": 2},
    #         "JT11": {"JT1": 3, "JT3": 1, "JT4": 1, "JT6": 2},
    #         "JT12": {"JT7": 1},
    #         "JT13": {"JT11": 1, "JT12": 1},
    #         "JT14": {"JT7": 2}},
    #     "factories": {
    #         "Fc1": {
    #             "JT1": {"lots": [1], "time": 1},
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT11": {"lots": [1, 2], "time": 3},
    #             "JT14": {"lots": [1], "time": 4}},
    #         "Fc2": {
    #             "JT12": {"lots": [1], "time": 4},
    #             "JT13": {"lots": [1], "time": 4}},
    #         "Fc3": {
    #             "JT3": {"lots": [1], "time": 2},
    #             "JT6": {"lots": [1], "time": 2},
    #             "JT11": {"lots": [1], "time": 4}},
    #         "Fc4": {
    #             "JT3": {"lots": [1], "time": 2},
    #             "JT14": {"lots": [1], "time": 4}},
    #         "Fc5": {
    #             "JT4": {"lots": [1], "time": 2}},
    #         "Fc6": {
    #             "JT1": {"lots": [1], "time": 1},
    #             "JT6": {"lots": [1], "time": 2},
    #             "JT7": {"lots": [1], "time": 3}}},
    #     "holding_cost": {"JT1": 1, "JT3": 2, "JT4": 1, "JT6": 4, "JT7": 5, "JT11": 11, "JT12": 7, "JT13": 19, "JT14": 6},
    #     "trucks": {"tr1": {"cap": 8}, "tr2": {"cap": 5}, "tr3": {"cap": 5}, "tr4": {"cap": 3}, "tr5": {"cap": 3}, "tr6": {"cap": 3}}},
    # # ---------------- case 26 : Factory 6, JT 9, Truck 5 ----------------
    # {
    #     "params": {"final_product": ["JT14", "JT15"], "amount": [2, 1], "float_unit": ["JT1", "JT14"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT4": {"JT2": 1},
    #         "JT5": {"JT2": 2, "JT3": 1, "JT4": 1},
    #         "JT8": {"JT1": 1, "JT2": 2, "JT3": 1, "JT4": 1},
    #         "JT10": {"JT3": 1},
    #         "JT14": {"JT8": 2},
    #         "JT15": {"JT1": 3, "JT5": 1, "JT10": 3}},
    #     "factories": {
    #         "Fc1": {
    #             "JT1": {"lots": [1], "time": 1},
    #             "JT3": {"lots": [1], "time": 2},
    #             "JT4": {"lots": [1], "time": 3},
    #             "JT8": {"lots": [1], "time": 3},
    #             "JT14": {"lots": [1], "time": 4},
    #             "JT15": {"lots": [1], "time": 5}},
    #         "Fc2": {
    #             "JT1": {"lots": [1], "time": 2},
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT10": {"lots": [1], "time": 3}},
    #         "Fc3": {
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT5": {"lots": [1], "time": 4},
    #             "JT10": {"lots": [1, 3], "time": 2},
    #             "JT15": {"lots": [1], "time": 4}},
    #         "Fc4": {
    #             "JT4": {"lots": [1], "time": 2},
    #             "JT8": {"lots": [1], "time": 3}},
    #         "Fc5": {
    #             "JT2": {"lots": [1, 2], "time": 2},
    #             "JT3": {"lots": [1, 2], "time": 2}},
    #         "Fc6": {
    #             "JT5": {"lots": [1], "time": 3},
    #             "JT14": {"lots": [1], "time": 5}}},
    #     "holding_cost": {"JT1": 2, "JT2": 2, "JT3": 2, "JT4": 5, "JT5": 11, "JT8": 14, "JT10": 2, "JT14": 14, "JT15": 18},
    #     "trucks": {"tr1": {"cap": 5}, "tr2": {"cap": 5}, "tr3": {"cap": 5}, "tr4": {"cap": 3}, "tr5": {"cap": 3}}},
    # # ---------------- case 27 : Factory 7, JT 9, Truck 6 ----------------
    # {
    #     "params": {"final_product": ["JT14", "JT15"], "amount": [1, 1], "float_unit": ["JT10", "JT14"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT5": {"JT2": 1, "JT4": 3},
    #         "JT9": {"JT2": 2, "JT5": 1},
    #         "JT10": {"JT4": 2},
    #         "JT11": {"JT2": 3, "JT9": 1, "JT10": 2},
    #         "JT14": {"JT3": 2, "JT10": 1},
    #         "JT15": {"JT3": 1, "JT4": 3, "JT11": 1, "JT14": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT10": {"lots": [1, 2], "time": 3},
    #             "JT11": {"lots": [1], "time": 5},
    #             "JT14": {"lots": [1], "time": 3}},
    #         "Fc2": {
    #             "JT2": {"lots": [1], "time": 1},
    #             "JT15": {"lots": [1], "time": 5}},
    #         "Fc3": {
    #             "JT11": {"lots": [1, 2], "time": 4},
    #             "JT14": {"lots": [1], "time": 3}},
    #         "Fc4": {
    #             "JT3": {"lots": [1], "time": 2},
    #             "JT4": {"lots": [1, 2], "time": 1},
    #             "JT9": {"lots": [1], "time": 3},
    #             "JT10": {"lots": [1, 3], "time": 2},
    #             "JT15": {"lots": [1], "time": 5}},
    #         "Fc5": {
    #             "JT3": {"lots": [1, 3], "time": 2},
    #             "JT5": {"lots": [1], "time": 2},
    #             "JT9": {"lots": [1, 2], "time": 4},
    #             "JT14": {"lots": [1], "time": 3}},
    #         "Fc6": {
    #             "JT3": {"lots": [1, 3], "time": 2},
    #             "JT10": {"lots": [1], "time": 2}},
    #         "Fc7": {
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT9": {"lots": [1], "time": 4},
    #             "JT15": {"lots": [1], "time": 5}}},
    #     "holding_cost": {"JT2": 1, "JT3": 1, "JT4": 2, "JT5": 3, "JT9": 7, "JT10": 4, "JT11": 14, "JT14": 5, "JT15": 23},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 5}, "tr3": {"cap": 5}, "tr4": {"cap": 3}, "tr5": {"cap": 3}, "tr6": {"cap": 3}}},
    # # ---------------- case 28 : Factory 7, JT 10, Truck 6 ----------------
    # {
    #     "params": {"final_product": ["JT14", "JT15"], "amount": [2, 1], "float_unit": ["JT2", "JT5"],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT10": {"JT1": 2, "JT5": 1},
    #         "JT11": {"JT1": 1, "JT10": 2},
    #         "JT12": {"JT2": 1},
    #         "JT13": {"JT10": 2, "JT11": 2, "JT12": 2},
    #         "JT14": {"JT3": 1, "JT12": 1},
    #         "JT15": {"JT2": 2, "JT13": 1, "JT14": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT5": {"lots": [1], "time": 1},
    #             "JT10": {"lots": [1], "time": 3},
    #             "JT11": {"lots": [1, 2], "time": 3},
    #             "JT12": {"lots": [1, 2], "time": 2},
    #             "JT13": {"lots": [1], "time": 5},
    #             "JT15": {"lots": [1], "time": 6}},
    #         "Fc2": {
    #             "JT1": {"lots": [1, 2], "time": 1},
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT5": {"lots": [1], "time": 1},
    #             "JT10": {"lots": [1], "time": 3},
    #             "JT13": {"lots": [1], "time": 4},
    #             "JT15": {"lots": [1], "time": 6}},
    #         "Fc3": {
    #             "JT1": {"lots": [1, 2], "time": 2},
    #             "JT2": {"lots": [1, 3], "time": 1},
    #             "JT11": {"lots": [1], "time": 3}},
    #         "Fc4": {
    #             "JT3": {"lots": [1, 3], "time": 1},
    #             "JT15": {"lots": [1], "time": 5}},
    #         "Fc5": {
    #             "JT2": {"lots": [1, 3], "time": 1},
    #             "JT11": {"lots": [1], "time": 3},
    #             "JT13": {"lots": [1, 3], "time": 4}},
    #         "Fc6": {
    #             "JT5": {"lots": [1, 2], "time": 1},
    #             "JT10": {"lots": [1, 2], "time": 2},
    #             "JT12": {"lots": [1], "time": 3},
    #             "JT13": {"lots": [1], "time": 4}},
    #         "Fc7": {
    #             "JT1": {"lots": [1, 2], "time": 1},
    #             "JT2": {"lots": [1], "time": 2},
    #             "JT13": {"lots": [1, 3], "time": 4},
    #             "JT14": {"lots": [1], "time": 4}}},
    #     "holding_cost": {"JT1": 2, "JT2": 1, "JT3": 2, "JT5": 2, "JT10": 7, "JT11": 11, "JT12": 3, "JT13": 21, "JT14": 7, "JT15": 30},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 8}, "tr4": {"cap": 5}, "tr5": {"cap": 5}, "tr6": {"cap": 3}}},
    # # ---------------- case 29 : Factory 7, JT 10, Truck 6 ----------------
    # {
    #     "params": {"final_product": ["JT13", "JT15"], "amount": [1, 1], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT8": {"JT1": 3, "JT2": 1, "JT5": 1, "JT6": 1},
    #         "JT9": {"JT1": 2, "JT5": 1, "JT8": 2},
    #         "JT11": {"JT1": 1, "JT2": 2},
    #         "JT12": {"JT5": 1, "JT8": 1, "JT11": 1},
    #         "JT13": {"JT2": 2, "JT6": 1, "JT12": 2},
    #         "JT15": {"JT5": 2, "JT9": 1}},
    #     "factories": {
    #         "Fc1": {
    #             "JT1": {"lots": [1], "time": 1},
    #             "JT2": {"lots": [1], "time": 2},
    #             "JT6": {"lots": [1], "time": 2},
    #             "JT15": {"lots": [1], "time": 4}},
    #         "Fc2": {
    #             "JT1": {"lots": [1, 3], "time": 2},
    #             "JT9": {"lots": [1, 3], "time": 3},
    #             "JT13": {"lots": [1], "time": 5}},
    #         "Fc3": {
    #             "JT2": {"lots": [1, 3], "time": 2},
    #             "JT12": {"lots": [1, 2], "time": 4},
    #             "JT13": {"lots": [1], "time": 5},
    #             "JT15": {"lots": [1], "time": 5}},
    #         "Fc4": {
    #             "JT5": {"lots": [1], "time": 2},
    #             "JT11": {"lots": [1, 3], "time": 3},
    #             "JT13": {"lots": [1], "time": 5}},
    #         "Fc5": {
    #             "JT5": {"lots": [1], "time": 2},
    #             "JT8": {"lots": [1], "time": 3},
    #             "JT13": {"lots": [1], "time": 4}},
    #         "Fc6": {
    #             "JT12": {"lots": [1], "time": 3},
    #             "JT13": {"lots": [1], "time": 5},
    #             "JT15": {"lots": [1], "time": 5}},
    #         "Fc7": {
    #             "JT2": {"lots": [1, 3], "time": 1},
    #             "JT5": {"lots": [1], "time": 2},
    #             "JT6": {"lots": [1], "time": 1},
    #             "JT9": {"lots": [1], "time": 4},
    #             "JT12": {"lots": [1, 2], "time": 4}}},
    #     "holding_cost": {"JT1": 1, "JT2": 1, "JT5": 2, "JT6": 1, "JT8": 8, "JT9": 14, "JT11": 5, "JT12": 15, "JT13": 18, "JT15": 16},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 10}, "tr3": {"cap": 10}, "tr4": {"cap": 8}, "tr5": {"cap": 5}, "tr6": {"cap": 5}}},
    # # ---------------- case 30 : Factory 7, JT 10, Truck 7 ----------------
    # {
    #     "params": {"final_product": ["JT14", "JT15"], "amount": [1, 2], "float_unit": [],
    #                "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}},
    #     "boms": {
    #         "JT10": {"JT2": 1, "JT4": 2},
    #         "JT11": {"JT2": 2, "JT4": 1, "JT9": 2, "JT10": 2},
    #         "JT12": {"JT3": 1},
    #         "JT13": {"JT11": 1},
    #         "JT14": {"JT3": 1, "JT9": 2, "JT10": 1, "JT13": 2},
    #         "JT15": {"JT9": 2, "JT12": 2}},
    #     "factories": {
    #         "Fc1": {
    #             "JT2": {"lots": [1, 2], "time": 1},
    #             "JT9": {"lots": [1], "time": 1},
    #             "JT10": {"lots": [1, 3], "time": 2},
    #             "JT11": {"lots": [1], "time": 3},
    #             "JT12": {"lots": [1], "time": 3},
    #             "JT14": {"lots": [1], "time": 5}},
    #         "Fc2": {
    #             "JT2": {"lots": [1], "time": 1},
    #             "JT9": {"lots": [1], "time": 1},
    #             "JT12": {"lots": [1], "time": 3},
    #             "JT13": {"lots": [1], "time": 5}},
    #         "Fc3": {
    #             "JT2": {"lots": [1, 3], "time": 1},
    #             "JT3": {"lots": [1, 3], "time": 2},
    #             "JT4": {"lots": [1, 3], "time": 1},
    #             "JT9": {"lots": [1], "time": 1},
    #             "JT14": {"lots": [1], "time": 5},
    #             "JT15": {"lots": [1], "time": 3}},
    #         "Fc4": {
    #             "JT9": {"lots": [1], "time": 1},
    #             "JT10": {"lots": [1, 3], "time": 2},
    #             "JT12": {"lots": [1], "time": 2},
    #             "JT14": {"lots": [1], "time": 5}},
    #         "Fc5": {
    #             "JT2": {"lots": [1], "time": 1},
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT14": {"lots": [1], "time": 6},
    #             "JT15": {"lots": [1], "time": 3}},
    #         "Fc6": {
    #             "JT10": {"lots": [1], "time": 2},
    #             "JT14": {"lots": [1], "time": 6}},
    #         "Fc7": {
    #             "JT3": {"lots": [1], "time": 1},
    #             "JT4": {"lots": [1, 3], "time": 2}}},
    #     "holding_cost": {"JT2": 2, "JT3": 2, "JT4": 1, "JT9": 2, "JT10": 4, "JT11": 10, "JT12": 5, "JT13": 12, "JT14": 22, "JT15": 9},
    #     "trucks": {"tr1": {"cap": 10}, "tr2": {"cap": 8}, "tr3": {"cap": 5}, "tr4": {"cap": 5}, "tr5": {"cap": 3}, "tr6": {"cap": 3}, "tr7": {"cap": 3}}},
    ]
