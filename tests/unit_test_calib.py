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
from os.path import join
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

        # omit status messages
        self.cfg.params[self.cfg.opt_prnt] = False

        # enable options in config to cover more algorithms in tests
        self.cfg.params[self.cfg.cal_meth] = constants.CALI_METH[3]

        try:
            with zipfile.ZipFile(self.CEA_PATH+'.zip', 'r') as zip_obj:
                zip_obj.extractall(self.CEA_PATH)
        except BaseException:
            pass

    def test_mla_geometry_estimate(self):

        pat_types = ['rec', 'hex']
        max_dim = 30
        pitch = 1

        for flip in [False, True]:
            for pat_type in pat_types:
                pseudo_grid = GridFitter.grid_gen(dims=[max_dim, max_dim], pat_type=pat_type, hex_odd=False)
                pseudo_grid = pseudo_grid[:, :2][:, ::-1] if flip else pseudo_grid
                sorter = CentroidSorter(centroids=pseudo_grid)
                pattern = sorter._estimate_mla_geometry(pitch=pitch)
                self.assertEqual(pat_type, pattern, 'Pattern detection failed')

        return True

    def test_grid_gen(self):

        dim = 5
        x = np.linspace(-.5, .5, dim)
        i = np.linspace(0, dim-1, dim)
        coords = np.concatenate([np.meshgrid(x.T, x)[::-1], np.meshgrid(i.T, i)[::-1]], axis=0).reshape(-1, dim**2).T

        pseudo_grid = GridFitter.grid_gen(dims=[dim, dim], pat_type='rec', hex_odd=False, normalize=True)

        rmse = np.sqrt(np.sum(np.square(coords-pseudo_grid)))

        self.assertEqual(rmse, 0, 'Grid generation failed')

    def test_grid_rotation_fit(self):

        # test grid generation
        dims = [122, 122]
        pat_type = 'rec'
        grid = GridFitter.grid_gen(dims=dims, pat_type=pat_type)

        # parameters for regression
        rvecs = [15*np.random.rand(3) for _ in range(5)]
        compose, affine, flip_xy = [False] * 3
        compose = False

        for rvec in rvecs:

            # create transformation matrix
            rvec = rvec/180*np.pi
            rmat = GridFitter.euler2mat(*rvec)
            rmat[-1, -1] = 1

            # apply transformation
            xpts = GridFitter.apply_transform(rmat, grid.copy(), affine, flip_xy)

            # grid regression
            gf = GridFitter(xpts, compose=compose, affine=affine, flip_xy=flip_xy)
            gf.main()

            # rotation matrix assertion
            all_close = np.allclose(gf.pmat, rmat, rtol=1e-01, atol=1e-01)
            self.assertTrue(all_close, 'Grid estimation failed')

            # decomposition matrix assertion
            xrmat = gf.decompose(gf.pmat)[0]
            all_close = np.allclose(rmat, xrmat, rtol=1e-01, atol=1e-01)
            self.assertTrue(all_close, 'QR-decomposition failed')

            # euler angles assertion
            angles = gf.mat2euler(xrmat)
            all_close = np.allclose(angles, rvec)
            self.assertTrue(all_close, 'Angle estimation failed')

    def test_decomposition(self):

        for _ in range(100):

            rvec = np.random.randn(3)/180*np.pi
            rmat = GridFitter.euler2mat(*rvec)
            kmat = np.diag(np.array([*np.random.rand(2)*2 + 1, 1]))
            pmat = np.dot(rmat, kmat)

            xvec = GridFitter.mat2euler(rmat)
            all_close = np.allclose(rvec, xvec)
            self.assertTrue(all_close, 'Angle extraction failed')

            xrmat, xkmat, xtvec = GridFitter.decompose(pmat)
            all_close = np.allclose([rmat, kmat], [xrmat, xkmat])
            self.assertTrue(all_close, 'Decomposition failed')

            xvec = GridFitter.mat2euler(xrmat)
            all_close = np.allclose(rvec, xvec)
            self.assertTrue(all_close, 'Angle decomposition failed')

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

        # estimate MLA dimensions
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


if __name__ == '__main__':
    unittest.main()
