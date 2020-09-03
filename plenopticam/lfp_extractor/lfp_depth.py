#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2020 Christopher Hahne <info@christopherhahne.de>

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

from plenopticam.lfp_extractor import LfpViewpoints
from plenopticam.misc import img_resize

from depthy.lightfield import epi_depth
from depthy.misc import disp2pts, save_ply, save_pfm, plot_point_cloud
from os.path import join
import warnings

try:
    from mpl_toolkits.mplot3d import Axes3D
except ImportError as e:
    warnings.warn('matplotlib is not installed')


class LfpDepth(LfpViewpoints):

    def __init__(self, *args, **kwargs):
        super(LfpDepth, self).__init__(*args, **kwargs)

        # initialization
        self.depth_map = None

    def main(self):

        # print status
        self.sta.status_msg('Compute depth map', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # compute depth
        self.depth_map = epi_depth(lf_img_arr=self.vp_img_arr.copy(), lf_wid=1, primal_opt=True, perc_clip=1)
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        # export data
        self.sta.status_msg('Write depth data', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])
        pts = disp2pts(self.depth_map)
        save_ply(pts, file_path=join(self.cfg.exp_path, 'depth.ply'))
        save_pfm(self.depth_map, scale=1, file_path=join(self.cfg.exp_path, 'depth.pfm'))
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

    def plot_point_cloud(self, rgb_img=None, down_scale: int = 4, view_angles: (int, int) = (50, 70)) -> Axes3D:

        rgb_img = self.central_view if rgb_img is None else rgb_img
        ax = None

        # downsample via interpolation
        rgb_img = img_resize(rgb_img.copy(), x_scale=1./down_scale)
        dpt_map = img_resize(self.depth_map.copy(), x_scale=1./down_scale)

        if self.depth_map is not None:
            ax = plot_point_cloud(dpt_map, rgb_img=rgb_img, down_scale=1, view_angles=view_angles)
        else:
            self.sta.status_msg(msg='Depth map variable is empty')

        return ax
