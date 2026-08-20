import csv
import json
import random
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# Settings: edit these values before running this file.
# -----------------------------------------------------------------------------
# paddy has 100 recordings, enough for the default 25-machine train/test split.

def make_daily_trajectory(frame):
    day = frame["time"].iloc[0].normalize()
    frame = frame[frame["time"].dt.normalize() == day].copy()
    frame["bin"] = frame["time"].dt.floor("5min")

    sampled = frame.groupby("bin", sort=True)[["lat", "lng"]].last().reindex(pd.date_range(day, periods=288, freq="5min"))

    active = sampled.notna().any(axis=1)

    first, last = active[active].index[[0, -1]]
    sampled.loc[first:last] = sampled.loc[first:last].ffill().bfill()
    return sampled

def grid_indices(frame, bounds, row_nums, col_nums):
    min_lat, max_lat, min_lng, max_lng = bounds
    indices = np.zeros((len(frame), 2), dtype=int)
    active = frame["lat"].notna() & frame["lng"].notna()

    lat_scale = max(max_lat - min_lat, 1e-9)
    lng_scale = max(max_lng - min_lng, 1e-9)
    row = np.floor((frame.loc[active, "lat"] - min_lat) / lat_scale * (row_nums - 1)).astype(int) + 1
    col = np.floor((frame.loc[active, "lng"] - min_lng) / lng_scale * (col_nums - 1)).astype(int) + 1

    indices[active.to_numpy(), 0] = row.clip(1, row_nums)
    indices[active.to_numpy(), 1] = col.clip(1, col_nums)
    return indices

def write_csv(output_dir, episodes):
    path = Path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("machine_id", "day", "records"))
        for day, machines in enumerate(episodes):

            for machine_id in machines.keys():
                records = []
                for row, col in machines[machine_id]:
                    records.append(f"{row};{col}")
                records = "|".join(records)
                writer.writerow((machine_id, day + 1, records))

def find_dataset(data_dir, output_dir, row_nums, col_nums, choose_machines, num_am_day):
    json_path = Path(output_dir) / "metadata.json"
    metadata = {"saved_dir": output_dir, "study_region_shape": [row_nums, col_nums], "Num_am_day": num_am_day, "AM_Groups": list(set(choose_machines))}

    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            prior_data = json.load(f)
            if all(prior_data[key] == metadata[key] for key in metadata.keys()):
                return Path(output_dir), prior_data["range"]

    machines = {0: "corn_0", 1: "corn_1", 2: "corn_2", 3: "corn_3", 4: "corn_4", 5: "corn_5", 6: "paddy", 7: "wheat1_0", 8: "wheat1_1", 9: "wheat1_2", 10: "wheat1_3", 11: "wheat1_4"}

    files_dir = [Path(data_dir) / f"public_trajectory_dataset_main" / f"{machines[machine_id]}.zip" for machine_id in choose_machines]

    recordings = {}

    for directory in files_dir:
        with ZipFile(directory) as bundle:
            for workbook in sorted(name for name in bundle.namelist() if name.lower().endswith(".xlsx")):
                machine_id = Path(workbook).stem
                print(machine_id)
                raw = pd.read_excel(BytesIO(bundle.read(workbook)))
                frame = raw[["time", "latitude", "longitude"]].copy()
                frame.columns = ["time", "lat", "lng"]
                frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
                frame["lat"] = pd.to_numeric(frame["lat"], errors="coerce")
                frame["lng"] = pd.to_numeric(frame["lng"], errors="coerce")
                frame = frame.dropna().sort_values("time")

                if not frame.empty: recordings[machine_id] = frame

    prepared = {machine_id: make_daily_trajectory(frame) for machine_id, frame in recordings.items()}
    all_lat = pd.concat([frame["lat"] for frame in prepared.values()]).dropna()
    all_lng = pd.concat([frame["lng"] for frame in prepared.values()]).dropna()
    bounds = (float(all_lat.min()), float(all_lat.max()), float(all_lng.min()), float(all_lng.max()))
    metadata["range"] = {"lat_min": bounds[0], "lat_max": bounds[1], "lng_min": bounds[2], "lng_max": bounds[3]}
    mapped = {machine_id: grid_indices(prepared[machine_id], bounds, row_nums, col_nums) for machine_id in prepared.keys()}
    # for machine_id in mapped.keys():
    #     print(machine_id)
    #     for row_info, col_info in mapped[machine_id]:
    #         print("\tRow :", round(row_info, 2), " Col :", round(col_info, 2))

    seed = 2399
    random.Random(seed).shuffle(list(mapped))

    episodes = [[(machine_id, mapped[machine_id]) for machine_id in list(mapped)[idx:idx+num_am_day]] for idx in range(0, len(mapped), num_am_day)]
    working_per_day = [{machine_id: frame for machine_id, frame in episodes[day]} for day in range(len(episodes)) if len(episodes[day]) == num_am_day]

    test_count = max(1, round(len(working_per_day) * 0.25))
    train, test = working_per_day[:-test_count], working_per_day[-test_count:]

    for csv_name, data in zip(("\\train.csv", "\\test.csv"), (train, test)):
        write_csv(output_dir + csv_name, data)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)

    return Path(output_dir), metadata["range"]

def main():
    data_dir = "C:\\Users\\USER\\Documents\\MobRef_GitHub\\data"
    output_dir = ".\\data"
    row_nums = 450
    col_nums = 550
    choose_machines = [0, 3]  # 0-5: corn, 6: paddy, 7-11: wheat1
    nun_am_day = 4
    find_dataset(data_dir, output_dir, row_nums, col_nums, choose_machines, nun_am_day)

if __name__ == "__main__":
    main()
