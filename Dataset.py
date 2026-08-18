
import os
import pandas as pd
import numpy as np
import torch
import random

from torch.utils.data import Dataset

from utils.Grid import Grid
from regions import *




class TankerDataSetV3(Dataset):
    def __init__(self, file_path):
        super(TankerDataSetV3, self).__init__()

        self.did_data, self.records_data = [], []
        """
        self.did_data: 
        - list 每个item是一条数据
        - 每个item是一个ndarray(5-10,) 内容是农机ID

        self.records_data:
        - list 
        - ndarray(5-10, 288[时间片个数], 2[grid_idx, state]) 第1维(从0开始)是grid_idx
        """

        dt_pd = pd.read_csv(file_path, sep=',')
        dt_np = np.array(dt_pd)

        cur_group_id = 0
        l = len(dt_np)
        did_group, records_group = [], []
        for i in range(l):
            row = dt_np[i]  # did group_id records
            did, group_id, records = str(row[0]), row[1], row[2]
            records_list = records.split('|')
            records_list = [[int(float(a)) for a in e.split(';')] for e in records_list]

            if group_id == cur_group_id:
                did_group.append(did)
                records_group.append(records_list)
            else:
                # handle the pre group
                if len(did_group) > 0:
                    this_did_data = np.array(did_group)
                    this_records_data = np.array(records_group)
                    self.did_data.append(this_did_data)
                    self.records_data.append(this_records_data)
                    did_group.clear()
                    records_group.clear()
                # create this new group
                did_group.append(did)
                records_group.append(records_list)
                cur_group_id = group_id
        # last group
        if len(did_group) > 0:
            this_did_data = np.array(did_group)
            this_records_data = np.array(records_group)
            self.did_data.append(this_did_data)
            self.records_data.append(this_records_data)
            did_group.clear()
            records_group.clear()

        #
        self.n_samples = len(self.did_data)

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        
        
        # record里面，第一维代表不同的农机，第二维代表不同的时间步，第三维中的第一个变量是grid_idx，可以唯一地转换为col和row
        return self.did_data[idx], self.records_data[idx]
        # (n_h, )  (n_h, n_steps, 3)

    def sample(self):
        return random.choice(self.did_data), random.choice(self.records_data)

if __name__ == "__main__":
    from parameter import DATA_DIR
    TankerDataSetV3(os.path.join(DATA_DIR, "train.csv"))