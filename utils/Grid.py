import torch
import numpy as np
import requests
import json
import time
import traceback
import math
import os
import sys

from utils.SpatialCompute import Point, haversine_distance
from parameter import *


class Grid:
    """
    index order
    30 31 32 33 34...
    20 21 22 23 24...
    10 11 12 13 14...
    01 02 03 04...
    """

    def __init__(self,
                 min_lat: float,
                 min_lng: float,
                 n_rows: int,
                 n_cols: int,
                 km_per_cell_lat: float,
                 km_per_cell_lng: float,
                 save_path: str = None,
                 load_path: str = None,
                 use_real_roadnetwork: bool = False,
                 use_general_distance: bool = False,
                 ):

        km_lat = n_rows * km_per_cell_lat
        km_lng = n_cols * km_per_cell_lng

        self.max_lat = min_lat + LAT_PER_METER * km_lat * 1000.0
        self.max_lng = min_lng + LNG_PER_METER * km_lng * 1000.0

        self.min_lat = min_lat
        self.min_lng = min_lng

        self.n_rows = n_rows
        self.n_cols = n_cols

        self.km_per_cell_lat = km_per_cell_lat
        self.km_per_cell_lng = km_per_cell_lng

        self.m_per_cell_lat = km_per_cell_lat * 1000.
        self.m_per_cell_lng = km_per_cell_lng * 1000.

        # use to pre-calculate the distance matrix
        n_rc = n_rows * n_cols
        # self.dis_mat = np.zeros((n_rc + 1, n_rc + 1))

        # print(sys.path)

        def pre_cal_mat():
            for i in range(n_rc):
                print(i, n_rc)
                for j in range(i, n_rc):
                    idx1 = i + 1
                    idx2 = j + 1
                    self.dis_mat[idx1][idx2] = self.dis_mat[idx2][idx1] = self.get_distance(idx1, idx2)
            print('pre calculate grid distances finished.')
            self.dis_mat_t = torch.from_numpy(self.dis_mat)
            self.dis_mat_t = self.dis_mat_t.to(DEVICE)
            # np.save(save_path, self.dis_mat)

        #
        self.use_general_distance = use_general_distance
        if use_general_distance:
            pass
        else:
            self.dis_mat = np.zeros((n_rc + 1, n_rc + 1))
            if load_path is not None:
                if os.path.exists(load_path):
                    print("load from npy file")
                    self.dis_mat = np.load(load_path)
                else:
                    print("load path is None, pre-calculate grid first ...")
                    if save_path is not None:
                        pre_cal_mat()
                        self.save_grid_file(save_path)
                    else:
                        raise Exception("PARAM_ERROR: save_path is None")
            else:
                if not use_real_roadnetwork:
                    pre_cal_mat()
                    # self.save_grid_file(save_path)
                else:
                    # TODO: get relative road network
                    self.read_real_roadnetwork_distance('./real_dis_mat_bicycling.pt')
        #
        # print('Grid: ')
        # print(self.min_lat, self.min_lng)
        # print(self.max_lat, self.max_lng)

    def __getitem__(self, item: tuple):
        """
        Transpose (row idx, col idx) to grid idx.
        :param item: 2d tuple (row index, col index)
        :return: index in grid (return type same as those in item)
        """
        ri, ci = item

        _ri = ri - 1
        _ci = ci - 1

        return _ri * self.n_cols + _ci + 1

    def __setitem__(self, key, value):
        pass

    def __delitem__(self, key):
        pass

    @staticmethod
    def get_grid_by_points(min_lat, min_lng, max_lat, max_lng, km_per_cell_lat, km_per_cell_lng):
        n_rows = (max_lat - min_lat) / (LAT_PER_METER * km_per_cell_lat * 1000.0)
        n_rows = math.ceil(n_rows)
        n_cols = (max_lng - min_lng) / (LNG_PER_METER * km_per_cell_lng * 1000.0)
        n_cols = math.ceil(n_cols)

        return Grid(min_lat, min_lng, n_rows, n_cols, km_per_cell_lat, km_per_cell_lng, use_general_distance=True)


    def save_grid_file(self, save_path: str):
        assert save_path is not None
        print('save Grid in path: ', save_path)
        np.save(save_path, self.dis_mat)


    def reshape(self, km_per_cell_lat, km_per_cell_lng, num_rows=None, num_cols=None):

        if num_rows is None:
            num_rows = math.ceil((self.km_per_cell_lat / km_per_cell_lat) * self.n_rows)
        if num_cols is None:
            num_cols = math.ceil((self.km_per_cell_lng / km_per_cell_lng) * self.n_cols)
        km_lat = num_rows * km_per_cell_lat
        km_lng = num_cols * km_per_cell_lng

        self.max_lat = self.min_lat + LAT_PER_METER * km_lat * 1000.0
        self.max_lng = self.min_lng + LNG_PER_METER * km_lng * 1000.0

        # print(self.max_lat)
        # print(self.max_lng)

        self.n_rows = num_rows
        self.n_cols = num_cols

        self.km_per_cell_lat = km_per_cell_lat
        self.km_per_cell_lng = km_per_cell_lng

        self.m_per_cell_lat = km_per_cell_lat * 1000.
        self.m_per_cell_lng = km_per_cell_lng * 1000.

    def center(self, idx):
        lat = (self.min_lat + LAT_PER_METER * self.m_per_cell_lat / 2) + LAT_PER_METER * (self.row_index(
            idx) - 1) * self.m_per_cell_lat
        lng = (self.min_lng + LNG_PER_METER * self.m_per_cell_lng / 2) + LNG_PER_METER * (self.col_index(
            idx) - 1) * self.m_per_cell_lng
        return lat, lng

    def row_index(self, idx):
        if idx == 0:
            return 0.
        return (idx - 1.) // self.n_cols + 1

    def col_index(self, idx):
        if idx == 0:
            return 0.
        return (idx - 1.) % self.n_cols + 1

    def mid(self, idx1, idx2):
        row_st = min(self.row_index(idx1), self.row_index(idx2))
        col_st = min(self.col_index(idx1), self.col_index(idx2))

        row_add = abs(self.row_index(idx1) - self.row_index(idx2)) // 2
        col_add = abs(self.col_index(idx1) - self.col_index(idx2)) // 2

        mid_idx = 1 + (row_st + row_add) * self.n_cols + (col_st + col_add)
        return mid_idx

    def get_distance(self, idx1, idx2):
        lat1, lng1 = self.center(idx1)
        lat2, lng2 = self.center(idx2)

        return haversine_distance(Point(lat1, lng1), Point(lat2, lng2))

    def distance(self, idx1, idx2):
        if self.use_general_distance:
            r1, c1 = self.row_index(idx1), self.col_index(idx1)
            r2, c2 = self.row_index(idx2), self.col_index(idx2)
            return math.sqrt((r1 - r2) ** 2 + (c1 - c2) ** 2) * self.km_per_cell_lat * 1000.
        return self.dis_mat[int(idx1), int(idx2)]

    def index(self, lat, lng, preprocess=False):
        """

        :param lat: lat
        :param lng: lng
        :param preprocess: If preprocess, return -1 when ValueError instead of exit(1).
        :return:
        """

        try:
            if lat < self.min_lat or lat >= self.max_lat:
                raise ValueError('[Grid.index()] Location(' + str(lat) + ', ' + str(
                    lng) + ') not in the current grid. Check the lat.')
            if lng < self.min_lng or lng >= self.max_lng:
                raise ValueError('[Grid.index()] Location(' + str(lat) + ', ' + str(
                    lng) + ') not in the current grid. Check the lng.')

            delta_lat = lat - self.min_lat
            delta_lng = lng - self.min_lng

            m_lat = delta_lat / LAT_PER_METER
            m_lng = delta_lng / LNG_PER_METER
            row_idx = m_lat // self.m_per_cell_lat + 1
            col_idx = m_lng // self.m_per_cell_lng + 1
            return self.__getitem__((row_idx, col_idx))

        except ValueError:
            if not preprocess:
                traceback.print_exc()
                exit(1)
            else:
                return -1

    def geographical_coordinate(self, idx):
        """
        Transpose idx to lat and lng.
        :param idx:
        :return:
        """
        ri = self.row_index(idx)
        ci = self.col_index(idx)

        m_lat = (ri - 1) * self.m_per_cell_lat + self.m_per_cell_lat / 2
        m_lng = (ci - 1) * self.m_per_cell_lng + self.m_per_cell_lng / 2

        lat = self.min_lat + LAT_PER_METER * m_lat
        lng = self.min_lng + LNG_PER_METER * m_lng

        return lat, lng

    def up(self, idx):
        if self.row_index(idx) < self.n_rows:
            return idx + self.n_cols
        return idx

    def down(self, idx):
        if self.row_index(idx) > 1:
            return idx - self.n_cols
        return idx

    def left(self, idx):
        if self.col_index(idx) > 1:
            return idx - 1
        return idx

    def right(self, idx):
        if self.col_index(idx) < self.n_cols:
            return idx + 1
        return idx

    def lu(self, idx):
        if self.col_index(idx) > 1 and self.row_index(idx) < self.n_rows:
            return self.up(self.left(idx))
        return idx

    def ld(self, idx):
        if self.col_index(idx) > 1 and self.row_index(idx) > 1:
            return self.down(self.left(idx))
        return idx

    def ru(self, idx):
        if self.col_index(idx) < self.n_cols and self.row_index(idx) < self.n_rows:
            return self.up(self.right(idx))
        return idx

    def rd(self, idx):
        if self.col_index(idx) < self.n_cols and self.row_index(idx) > 1:
            return self.down(self.right(idx))
        return idx

    def stay(self, idx):
        return idx

    def up1(self, r, c):
        if r < self.n_rows:
            return r+1, c
        return r, c

    def down1(self, r, c):
        if r > 1:
            return r-1, c
        return r, c

    def left1(self, r, c):
        if c > 1:
            return r, c-1
        return r, c

    def right1(self, r, c):
        if c < self.n_cols:
            return r, c+1
        return r, c

    def lu1(self, r, c):
        if c > 1 and r < self.n_rows:
            r1, c1 = self.left1(r, c)
            return self.up1(r1, c1)
        return r, c

    def ld1(self, r, c):
        if c > 1 and r > 1:
            r1, c1 = self.left1(r, c)
            return self.down1(r1, c1)
        return r, c

    def ru1(self, r, c):
        if c < self.n_cols and r < self.n_rows:
            r1, c1 = self.right1(r, c)
            return self.up1(r1, c1)
        return r, c

    def rd1(self, r, c):
        if c < self.n_cols and r > 1:
            r1, c1 = self.right1(r, c)
            return self.down1(r1, c1)
        return r, c

    def stay1(self, r, c):
        return r, c

    def get_real_roadnetwork_distance(self, save_path=r'./real_dis_mat.pt'):
        real_dis_mat = torch.clone(self.dis_mat_t)  # [1+n_s, 1+n_s]
        n_grids, _ = real_dis_mat.size()

        key = 'YOUR-API-KEY'
        mode = 'bicycling'  # walking driving(default)

        for i in range(1, n_grids):
            for j in range(1, n_grids):
                request_params = {'key': key, 'mode': mode}
                lat_from, lng_from = self.center(i)
                request_params['from'] = str(lat_from) + ',' + str(lng_from)

                lat_to, lng_to = self.center(j)
                request_params['to'] = str(lat_to) + ',' + str(lng_to)

                # print(request_params)

                request = requests.get(url='https://apis.map.qq.com/ws/distance/v1/matrix', params=request_params)
                # tencent max requests: 5 times per sec
                time.sleep(0.2)
                # status = json.loads(request.text).get('status')
                # message = json.loads(request.text).get('message')
                rows = json.loads(request.text).get('result').get('rows')  # list which element is dict
                row = rows[0]
                elements = row['elements']  # list

                real_dis_mat[i][j] = elements[0]['distance']
                print('from {} to {}: {}'.format(i, j, elements[0]['distance']))
            print('{} / {}'.format(i, n_grids))
            torch.save(real_dis_mat, save_path)

    def read_real_roadnetwork_distance(self, load_path='./real_dis_mat_bicycling.pt'):
        self.dis_mat_t = torch.load(load_path).clone()
        print(self.dis_mat_t)

    def get_move_dir(self, grid_idx_1: int, grid_idx_2: int):
        """

        @param grid_idx_1:
        @param grid_idx_2:
        @return:
        """
        '''
        0 1 2
        3 4 5
        6 7 8
        
        '''
        str2int = {
            # 'lu': 0,
            'u': 0,
            # 'ru': 2,
            'l': 1,
            's': 2,
            'r': 3,
            # 'ld': 6,
            'd': 4,
            # 'rd': 8
        }
        if grid_idx_1 == grid_idx_2:
            return str2int['s']
        r1, c1 = self.row_index(grid_idx_1), self.col_index(grid_idx_1)
        r2, c2 = self.row_index(grid_idx_2), self.col_index(grid_idx_2)

        delta_r = r2 - r1
        delta_c = c2 - c1

        if delta_c > 0:
            return str2int['r']
            # x = 'r'
        elif delta_c < 0:
            # x = 'l'
            return str2int['l']
        elif delta_r > 0:
            return str2int['u']
        elif delta_r < 0:
            return str2int['d']
        return None
        # return str2int[dir]


if __name__ == '__main__':
    grid = Grid(MIN_LAT, MIN_LNG, 160, 198, 0.5, 0.5, use_real_roadnetwork=False)
    print(grid.distance(1, 2))
    # grid.read_real_roadnetwork_distance('./real_dis_mat_bicycling.pt')
