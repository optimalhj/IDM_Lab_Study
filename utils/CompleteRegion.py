import sys
# sys.path.append('./')
# sys.path.append('../')
# sys.path.append('../../')
from regions import *
# from utils.Grid import Grid
from utils.Grid import Grid
import numpy as np


class WorkingRegion:
    def __init__(self, id, min_idx, max_idx, min_r, min_c, max_r, max_c):
        self.id = id

        self.min_idx = min_idx
        self.max_idx = max_idx

        self.min_r = min_r
        self.min_c = min_c
        self.max_r = max_r
        self.max_c = max_c

        '''
            Grid
            ----------
            |     max|
            |min     |
            ----------
        '''


class CompleteRegion(Grid):
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
        super().__init__(min_lat, min_lng, n_rows, n_cols, km_per_cell_lat, km_per_cell_lng, save_path, load_path, use_real_roadnetwork, use_general_distance)

        self.n_working_regions = 0
        self.working_regions = []

    def make_working_regions(self, regions: list):
        """

        @param regions: [
            (min_lat, min_lng, max_lat, max_lng),
            (min_lat, min_lng, max_lat, max_lng),
            ...,
        ]
        @return:
        """
        self.working_regions = []
        self.working_regions.append(WorkingRegion(0, self.__getitem__((50, 50)), self.__getitem__((50, 50)), 50, 50, 50, 50))

        for i, tp in enumerate(regions):
            # print('--- --- ---')
            # print('working region ', i)

            min_lat, min_lng, max_lat, max_lng = tp[0], tp[1], tp[2], tp[3]
            # print(min_lat, min_lng, max_lat, max_lng)
            _idx_min = self.index(min_lat, min_lng)
            _idx_max = self.index(max_lat, max_lng)
            _min_r, _min_c = self.row_index(_idx_min), self.col_index(_idx_min)
            _max_r, _max_c = self.row_index(_idx_max), self.col_index(_idx_max)
            # print('origin r c: ', _min_r, _min_c, _max_r, _max_c)
            min_center_lat, min_center_lng = self.geographical_coordinate(_idx_min)
            max_center_lat, max_center_lng = self.geographical_coordinate(_idx_max)
            # check if the working region is too small
            if min_lat > min_center_lat:
                _min_r -= 1
            if min_lng > min_center_lng:
                _min_c -= 1
            if max_lat > max_center_lat:
                _max_r += 1
            if max_lng > max_center_lng:
                _max_c += 1
            #
            min_r = max(_min_r, 0)
            min_c = max(_min_c, 0)
            max_r = min(_max_r, self.n_rows)
            max_c = min(_max_c, self.n_cols)
            # print('after refine, r c: ', min_r, min_c, max_r, max_c)
            idx_min = self.__getitem__((min_r, min_c))
            idx_max = self.__getitem__((max_r, max_c))
            working_region = WorkingRegion(i+1, idx_min, idx_max, min_r, min_c, max_r, max_c)  # id start from 1
            self.working_regions.append(working_region)
            self.n_working_regions += 1

    def get_region_in_by_rc(self, r, c) -> int:
        for region in self.working_regions:
            if region.min_r <= r <= region.max_r and region.min_c <= c <= region.max_c:
                return region.id
        return 0

    def get_region_in_by_idx(self, idx) -> int:
        return self.get_region_in_by_rc(self.row_index(idx), self.col_index(idx))

    def get_relative_rc(self, working_region_id, r, c):
        wr = self.working_regions[working_region_id]
        assert isinstance(wr, WorkingRegion)
        re_r = r - wr.min_r + 1
        re_c = c - wr.min_c + 1
        return int(re_r), int(re_c)

    @staticmethod
    def get_travel_plan(tanker_r, tanker_c, wr: WorkingRegion):
        # mid_r1, mid_c1 = (wr1.min_r + wr1.max_r) // 2, (wr1.min_c + wr1.max_c) // 2
        # mid_r2, mid_c2 = (wr2.min_r + wr2.max_r) // 2, (wr2.min_c + wr2.max_c) // 2
        tar_r, tar_c = tanker_r, tanker_c
        n = 0
        # row
        if tanker_r < wr.min_r:
            n += np.abs(tanker_r - wr.min_r)
            tar_r = wr.min_r
        elif tanker_r > wr.max_r:
            n += np.abs(tanker_r - wr.max_r)
            tar_r = wr.max_r
        else:
            pass
        # col
        if tanker_c < wr.min_c:
            n += np.abs(tanker_c - wr.min_c)
            tar_c = wr.min_c
        elif tanker_c > wr.max_c:
            n += np.abs(tanker_c - wr.max_c)
            tar_c = wr.max_c
        else:
            pass
        # assert n > 0
        return n, tar_r, tar_c

    @staticmethod
    def get_travel_target(tanker_r, tanker_c, wr: WorkingRegion):
        tar_r, tar_c = 0, 0

        if wr.min_r <= tanker_r <= wr.max_r:
            tar_r = tanker_r
        elif tanker_r > wr.max_r:
            tar_r = wr.max_r
        elif tanker_r < wr.min_r:
            tar_r = wr.min_r
        else:
            raise ValueError

        if wr.min_c <= tanker_c <= wr.max_c:
            tar_c = tanker_c
        elif tanker_c > wr.max_c:
            tar_c = wr.max_c
        elif tanker_c < wr.min_c:
            tar_c = wr.min_c
        else:
            raise ValueError

        return tar_r, tar_c

    @staticmethod
    def get_travel_plan_v2(tanker_r, tanker_c, wr_f: WorkingRegion, wr: WorkingRegion):
        # mid_r1, mid_c1 = (wr1.min_r + wr1.max_r) // 2, (wr1.min_c + wr1.max_c) // 2
        # mid_r2, mid_c2 = (wr2.min_r + wr2.max_r) // 2, (wr2.min_c + wr2.max_c) // 2
        tar_r, tar_c = tanker_r, tanker_c
        n = 0
        n1, n2 = 0, 0
        # row
        out = False
        if tar_r < wr.min_r:
            n1 += np.abs(tar_r - np.min([wr_f.min_r, wr.min_r]))
            n2 += np.abs(tar_r - wr.min_r) - np.abs(tar_r - np.min([wr_f.min_r, wr.min_r]))
            n += np.abs(tar_r - wr.min_r)
            tar_r = wr.min_r
        elif tar_r > wr.max_r:
            n1 += np.abs(tar_r - np.max([wr_f.max_r, wr.max_r]))
            n2 += np.abs(tar_r - wr.max_r) - np.abs(tar_r - np.max([wr_f.max_r, wr.max_r]))
            n += np.abs(tar_r - wr.max_r)
            tar_r = wr.max_r
        else:
            pass
        # col
        if tar_c < wr.min_c:
            n2 += np.abs(tar_c - wr.min_c)
            tar_c = wr.min_c
        elif tar_c > wr.max_c:
            n2 += np.abs(tar_c - wr.max_c)
            tar_c = wr.max_c
        else:
            pass
        # assert n > 0
        return n1, n2, tar_r, tar_c






if __name__ == '__main__':
    region = CompleteRegion(COMPLETE_MIN_LAT, COMPLETE_MIN_LNG, 155, 185, 0.5, 0.5, load_path='./regions/complete_region.npy', use_general_distance=True)
    region.make_working_regions(WORKING_AREAS)
