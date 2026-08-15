"""Convert the public machinery GPS workbooks to MobRef CSV files."""

import csv
import json
import random
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from parameter import DATA_DIR

# -----------------------------------------------------------------------------
# Settings: edit these values before running this file.
# -----------------------------------------------------------------------------
# paddy has 100 recordings, enough for the default 25-machine train/test split.
CHOOSE_MACHINE = [0, 1, 2, 3, 4, 5]  # 0-5: corn, 6: paddy, 7-11: wheat1
MACHINES = {
    0: "corn_0", 1: "corn_1", 2: "corn_2", 3: "corn_3", 4: "corn_4",
    5: "corn_5", 6: "paddy", 7: "wheat1_0", 8: "wheat1_1",
    9: "wheat1_2", 10: "wheat1_3", 11: "wheat1_4"}

# To combine sources, put more ZIP paths in this list.
ARCHIVES = [Path(DATA_DIR) / f"public_trajectory_dataset"/ f"{MACHINES[machine_id]}.zip" for machine_id in CHOOSE_MACHINE]
OUTPUT_DIR = Path(DATA_DIR)
MACHINES_PER_DAY = 25
GRID_ROWS = 155
GRID_COLS = 185
TEST_RATIO = 0.25
SEED = 2333

# Unicode escapes keep the Chinese Excel headers portable on Windows.
TIME_COLUMNS = ("time", "\u65f6\u95f4")
LAT_COLUMNS = ("latitude", "\u7eac\u5ea6")
LNG_COLUMNS = ("longitude", "\u7ecf\u5ea6")


def find_column(frame, candidates):
    for name in candidates:
        if name in frame.columns:
            return name
    raise ValueError(f"Expected one of {candidates}; found {list(frame.columns)}")


def make_daily_trajectory(frame):

    day = frame["time"].iloc[0].normalize()
    frame = frame[frame["time"].dt.normalize() == day].copy()
    frame["bin"] = frame["time"].dt.floor("5min")
    sampled = frame.groupby("bin", sort=True)[["lat", "lng"]].last()
    sampled = sampled.reindex(pd.date_range(day, periods=288, freq="5min"))

    active = sampled.notna().any(axis=1)

    first, last = active[active].index[[0, -1]]
    sampled.loc[first:last] = sampled.loc[first:last].ffill().bfill()
    return sampled


def grid_indices(sampled, bounds):
    min_lat, max_lat, min_lng, max_lng = bounds
    indices = np.zeros(len(sampled), dtype=int)
    active = sampled["lat"].notna() & sampled["lng"].notna()

    lat_scale = max(max_lat - min_lat, 1e-9)
    lng_scale = max(max_lng - min_lng, 1e-9)
    row = np.floor((sampled.loc[active, "lat"] - min_lat) / lat_scale * (GRID_ROWS - 1)).astype(int) + 1
    col = np.floor((sampled.loc[active, "lng"] - min_lng) / lng_scale * (GRID_COLS - 1)).astype(int) + 1
    row = row.clip(1, GRID_ROWS)
    col = col.clip(1, GRID_COLS)
    indices[active.to_numpy()] = (row.to_numpy() - 1) * GRID_COLS + col.to_numpy()
    return indices


def write_csv(path, episodes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("did", "group_id", "records"))
        for group_id, machines in enumerate(episodes):
            for machine_id, indices in machines:
                records = "|".join(f"{int(index)};0" for index in indices)
                writer.writerow((machine_id, group_id, records))


def main():

    recordings = []
    seen = set()

    for archive in ARCHIVES:
        with ZipFile(archive) as bundle:
            for workbook in sorted(name for name in bundle.namelist() if name.lower().endswith(".xlsx")):
                machine_id = Path(workbook).stem
                if machine_id in seen:
                    machine_id = f"{archive.stem}_{machine_id}"
                seen.add(machine_id)

                raw = pd.read_excel(BytesIO(bundle.read(workbook)))
                frame = raw[[find_column(raw, TIME_COLUMNS), find_column(raw, LAT_COLUMNS), find_column(raw, LNG_COLUMNS)]].copy()
                frame.columns = ["time", "lat", "lng"]
                frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
                frame["lat"] = pd.to_numeric(frame["lat"], errors="coerce")
                frame["lng"] = pd.to_numeric(frame["lng"], errors="coerce")
                frame = frame.dropna().sort_values("time")
                
                if not frame.empty: recordings.append((machine_id, frame))

    prepared = [(machine_id, make_daily_trajectory(frame)) for machine_id, frame in recordings]
    all_lat = pd.concat([frame["lat"] for _, frame in prepared]).dropna()
    all_lng = pd.concat([frame["lng"] for _, frame in prepared]).dropna()
    bounds = (float(all_lat.min()), float(all_lat.max()), float(all_lng.min()), float(all_lng.max()))
    mapped = [(machine_id, grid_indices(frame, bounds)) for machine_id, frame in prepared]

    random.Random(SEED).shuffle(mapped)
    episodes = [mapped[index:index + MACHINES_PER_DAY] for index in range(0, len(mapped), MACHINES_PER_DAY)]
    episodes = [episode for episode in episodes if len(episode) == MACHINES_PER_DAY]
    test_count = max(1, round(len(episodes) * TEST_RATIO))
    train, test = episodes[:-test_count], episodes[-test_count:]

    write_csv(OUTPUT_DIR / "train.csv", train)
    write_csv(OUTPUT_DIR / "test.csv", test)
    metadata = {
        "archives": [str(path) for path in ARCHIVES],
        "train_days": len(train),
        "test_days": len(test),
        "machines_per_day": MACHINES_PER_DAY,
        "grid": {"rows": GRID_ROWS, "cols": GRID_COLS},
        "gps_bounds": {"min_lat": bounds[0], "max_lat": bounds[1], "min_lng": bounds[2], "max_lng": bounds[3]},
    }
    (OUTPUT_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Created {OUTPUT_DIR / 'train.csv'} ({len(train)} days) and {OUTPUT_DIR / 'test.csv'} ({len(test)} days).")


if __name__ == "__main__":
    main()
