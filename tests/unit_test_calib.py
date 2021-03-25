#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "inbox@christopherhahne.de"
__license__ = """
    Copyright (c) 2021 Christopher Hahne <inbox@christopherhahne.de>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import unittest
import numpy as np
from os.path import join, exists
import zipfile

from plenopticam.lfp_calibrator import CentroidSorter, GridFitter
from plenopticam.cfg import PlenopticamConfig, constants
from plenopticam.misc import load_img_file


class PlenoptiCamTesterCalib(unittest.TestCase):

    CEA_PATH = r'../examples/data/synth_spots'

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTesterCalib, self).__init__(*args, **kwargs)

    def setUp(self):

        # instantiate config and status objects
        self.cfg = PlenopticamConfig()
        self.cfg.default_values()

        # enable options in config to cover more algorithms in tests
        self.cfg.params[self.cfg.cal_meth] = constants.CALI_METH[3]

        # print current process message (to prevent Travis from stopping after 10 mins)
        self.cfg.params[self.cfg.opt_prnt] = True

        try:
            with zipfile.ZipFile(self.CEA_PATH+'.zip', 'r') as zip_obj:
                zip_obj.extractall(self.CEA_PATH)
        except BaseException:
            pass

    def test_mla_geometry_estimate(self):

        pat_types = ['rec', 'hex']
        max_dim = 30
        pitch = 1 / (max_dim - 1)

        for flip in [False, True]:
            for pat_type in pat_types:
                pseudo_grid = GridFitter.grid_gen(dims=[max_dim, max_dim], pat_type=pat_type, hex_odd=False)
                pseudo_grid = pseudo_grid[:, :2][:, ::-1] if flip else pseudo_grid
                sorter = CentroidSorter(centroids=pseudo_grid)
                pattern = sorter._estimate_mla_geometry(pitch)
                self.assertEqual(pat_type, pattern, 'Pattern detection failed')

        return True

    def test_grid_gen(self):

        dim = 5
        x = np.linspace(-1, 1, dim)
        i = np.linspace(0, dim-1, dim)
        coords = np.concatenate([np.meshgrid(x.T, x)[::-1], np.meshgrid(i.T, i)[::-1]], axis=0).reshape(-1, dim**2).T

        pseudo_grid = GridFitter.grid_gen(dims=[dim, dim], pat_type='rec', hex_odd=False)

        self.assertEqual(np.sum(coords-pseudo_grid), 0, 'Grid generation failed')

    def test_mla_dims_estimate(self):

        # init
        dim_y, dim_x = 9, 9
        pat_type = 'hex'
        flip = False

        # grid generation and modification
        pseudo_grid = GridFitter.grid_gen(dims=[dim_y, dim_x], pat_type=pat_type, hex_odd=False)[:, :2]
        ty, tx = np.min(pseudo_grid[:, 0]), np.min(pseudo_grid[:, 1])
        pseudo_grid -= np.array([ty, tx])
        pseudo_grid = pseudo_grid[:, ::-1] if flip else pseudo_grid

        #
        sorter = CentroidSorter(centroids=pseudo_grid)
        sorter._mla_dims()

        est_y, est_x = sorter._lens_y_max, sorter._lens_x_max

        self.assertEqual((est_y, est_x), (dim_y, dim_x), 'Centroid number estimation failed')

    def test_pitch_estimator(self):

        from plenopticam.lfp_calibrator import PitchEstimator

        fns = [join(self.CEA_PATH, fn+'.png') for fn in ['a', 'b', 'c', 'd']]
        ref_sizes = [141, 52, 18, 6]

        for fn, ref_size in zip(fns, ref_sizes):
            img = load_img_file(fn)
            obj = PitchEstimator(img=img, cfg=self.cfg)
            obj.main()

            self.assertEqual(ref_size, obj.M)

    def test_all(self):

        self.test_mla_geometry_estimate()
        self.test_grid_gen()
        self.test_mla_dims_estimate()
        self.test_pitch_estimator()


if __name__ == '__main__':
    unittest.main()
