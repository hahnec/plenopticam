#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "inbox@christopherhahne.de"
__license__ = """
    Copyright (c) 2020 Christopher Hahne <inbox@christopherhahne.de>

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
from depthy.misc.pfm_handler import load_pfm

from plenopticam.lfp_extractor.lfp_depth import LfpDepth
from plenopticam.misc import load_img_file, PlenopticamError


class PlenopticamTesterPlt(unittest.TestCase):

    def setUp(self):

        self.depth_map = np.ones([6, 6])
        self.lfp_depth_obj = LfpDepth(depth_map=self.depth_map)

        self.plot_opt = False

    def test_real_data(self):

        self.depth_map, _ = load_pfm('../examples/data/gradient_rose_close/depth.pfm')
        self.rgb_img = load_img_file('../examples/data/gradient_rose_close/thumbnail.png')
        self.lfp_depth_obj = LfpDepth(depth_map=self.depth_map)

        # test invalid downscale parameters
        for i in range(-1, 5):
            print(i)
            try:
                self.lfp_depth_obj.plot_point_cloud(rgb_img=self.rgb_img, down_scale=i)
            except PlenopticamError as e:
                self.assertTrue(e, PlenopticamError)

        # test Axes3D argument
        import matplotlib.pyplot as plt
        fig, ax = plt.figure(), plt.axes(projection='3d')
        self.lfp_depth_obj.plot_point_cloud(down_scale=4, view_angles=(50, 70), ax=ax)

    def test_point_cloud(self):

        # test case where rgb image missing
        self.lfp_depth_obj.plot_point_cloud(rgb_img=None, down_scale=1)

        # test case for image dimension mismatch
        self.lfp_depth_obj.plot_point_cloud(rgb_img=np.zeros([3, 3, 3]), down_scale=1)

        # test valid case
        self.lfp_depth_obj.plot_point_cloud(rgb_img=np.zeros_like(self.depth_map), down_scale=2)

    def test_all(self):

        self.test_point_cloud()
