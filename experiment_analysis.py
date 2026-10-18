import mysql.connector
import matplotlib.pyplot as plt
from private import *
def main():

    graph = {}
    models = ("lp", "cp", "lp_various_trucks", "cp_various_trucks")
    for db_name_tmp in ("test", "test22", "test333", "test4444"):
        conn = mysql.connector.connect(user=user, password=password, database=db_name_tmp)
        cursor = conn.cursor()

        for start in models:
            cursor.execute(f"SELECT * FROM {table_time_record} WHERE DATASET LIKE \"{start}_fc%\";")
            for dataset, time in cursor:
                graph.setdefault(dataset[:-2].replace(f"{start}_", ""), {}).setdefault(start, []).append(time)
        cursor.close()

    for key in graph.keys():
        for model in models:
            graph[key][model] = sum(graph[key][model]) / len(graph[key][model])
    print(graph)

    key_sorting = sorted(graph.keys(), key=lambda key: sum(graph[key][model] for model in models))
    print(key_sorting)

    for system in models:
        plt.plot(key_sorting, [graph[key][system] for key in key_sorting], label=system, marker="o", linestyle="--")
    plt.legend()
    plt.xticks(rotation=45, fontsize=5)
    plt.xlabel("dataset")
    plt.ylabel("time")
    plt.show()
    return

if __name__ == "__main__":
    main()