#!/usr/bin/env python
import os

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2017 Christopher Hahne <info@christopherhahne.de>

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

# external libs
import numpy as np
from color_space_converter import rgb2gry

# local imports
from plenopticam.misc import Normalizer, save_img_file, PlenopticamStatus
from plenopticam.cfg import PlenopticamConfig


class CentroidDrawer(object):

    def __init__(self, img, centroids, cfg=None, sta=None):

        # input variables
        self._img = rgb2gry(img.copy())[..., 0] if len(img.shape) == 3 else img.copy()
        self._img = Normalizer(self._img).uint8_norm()
        self._centroids = np.asarray(centroids)
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else PlenopticamStatus()

    def write_centroids_img(self, fn='centroids_img.png'):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # status message handling
        self.sta.status_msg(msg='Save centroids image', opt=self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # draw MICs in binary image and save image file for debug purposes
        plot_img = self.draw_centroids_img()
        save_img_file(plot_img, os.path.join(os.path.splitext(self.cfg.params[self.cfg.lfp_path])[0], fn))
        # self.plot_centroids()

        # status message handling
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def draw_centroids_img(self):

        # draw centroids in single channel image
        centroid_mask = np.zeros(self._img.shape[:2], dtype=np.uint8)
        idx = np.round(self._centroids[:, 0]).astype(int), np.round(self._centroids[:, 1]).astype(int)
        centroid_mask[idx] = np.iinfo(centroid_mask.dtype).max

        # merge image and centroids to form RGB image
        diff_mask = self.non_wrap_subtract(self._img, centroid_mask)
        plot_img = np.zeros([self._img.shape[0], self._img.shape[1], 3], dtype=np.uint8)
        plot_img[..., :2] = np.concatenate((diff_mask[..., np.newaxis], diff_mask[..., np.newaxis]), axis=2)
        plot_img[..., 2] = centroid_mask            # move centroid_mask to blue channel

        return plot_img

    @staticmethod
    def non_wrap_subtract(a, b):
        """ prevent wrap-around for np.ndarray """

        x = (a - b)
        x[b > a] = 0

        return x
