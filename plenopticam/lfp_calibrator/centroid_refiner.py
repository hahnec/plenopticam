#!/usr/bin/env python
from __future__ import division

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

import numpy as np

# local imports
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc.status import PlenopticamStatus
from plenopticam.lfp_calibrator.centroid_drawer import CentroidDrawer

DR = 1


class CentroidRefiner(object):

    def __init__(self, img, centroids, cfg=None, sta=None, M=None, method=None):
        """

        This class takes a list of integer coordinates as centroids and an intensity map as inputs and re-computes

        :param img: image used as basis for coordinate refinement calculation
        :param centroids: iterable (list or np.ndarray) with coordinates of integer type
        :param cfg: PlenoptiCam configuration object
        :param sta: PlenoptiCam status object
        :param M: micro image size
        :param method: 'area' or 'peak'
        """

        # input variables
        self._img = np.asarray(img)
        self._centroids = np.array(centroids)
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else PlenopticamStatus()
        self._M = M
        self._r = self._M//2//DR if M is not None else None
        self._method = cfg.params[cfg.cal_meth] if cfg is not None else method if method is not None else 'area'

        # internal variables
        self._t = self._s = 0

        # output variables
        self._centroids_refined = []

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # status message handling
        self.sta.status_msg('Refine micro image centers', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        fun = self._peak_centroid if self._method == 'peak' else self._area_centroid

        # image normalization
        self._img = (self._img - self._img.min()) / (self._img.max() - self._img.min())

        # coordinate and image downsampling preparation
        self._centroids = [(x//DR, y//DR) for x, y in self._centroids] if DR > 1 else self._centroids
        img_scale = self._img[::DR, ::DR]

        self._centroids_refined = []

        # iterate through all centroids for refinement procedure
        for i, m in enumerate(self._centroids):

            # check interrupt status
            if self.sta.interrupt:
                return False

            # compute refined coordinates based on given method
            fun(img_scale[int(m[0])-self._r:int(m[0])+self._r+1, int(m[1])-self._r:int(m[1])+self._r+1], m)
            self._centroids_refined.append(self._get_coords())

            # print status
            self.sta.progress((i+1)/len(self._centroids)*100, self.cfg.params[self.cfg.opt_prnt])

        # coordinate upsampling to compensate for downsampling
        self._centroids_refined = [(x*DR, y*DR) for x, y in self._centroids_refined] if DR > 1 else self._centroids_refined

        # remove centroids at image boundaries
        self.exclude_marginal_centroids()

        # write centroids image to hard drive (if option set)
        if self.cfg.params[self.cfg.opt_dbug] and not self.sta.interrupt:
            draw_obj = CentroidDrawer(self._img, self._centroids, self.cfg)
            draw_obj.write_centroids_img(fn='wht_img+mics_refi.png')
            del draw_obj

        return True

    def _thresholding(self, input_win):

        # parameter init
        weight_win = input_win / input_win.max()

        # window thresholding
        th_img = np.zeros_like(input_win, dtype='bool')
        th_val = np.percentile(weight_win, 75)
        th_img[weight_win > th_val] = 1

        # validate that binary region exists
        if np.sum(th_img) == 0:
            raise Exception('Binary object not found')

        return th_img

    def _area_centroid(self, input_win, p):

        th_img = self._thresholding(input_win)

        # binary centroid calculation in window
        count = (th_img == 1).sum()
        self._t, self._s = np.argwhere(th_img == 1).sum(0)/count if count > 0 else (float('nan'), float('nan'))
        self._t += p[0]-self._r
        self._s += p[1]-self._r

        return True

    def _peak_centroid(self, input_win, p, threshold_opt=False):

        # parameter init
        input_win *= self._thresholding(input_win) if threshold_opt is True else 1
        weight_win = input_win / input_win.sum()
        self._t = self._s = 0

        # generate coordinate indices
        iss = np.tile(np.arange(weight_win.shape[0]), weight_win.shape[1])
        jss = np.tile(np.arange(weight_win.shape[1]), weight_win.shape[0])

        # compute moment
        self._t = sum((iss+p[0]-self._r) * weight_win.T.flatten())
        self._s = sum((jss+p[1]-self._r) * weight_win.flatten())

        return True

    def exclude_marginal_centroids(self):
        """ remove centroids being closer to image border than half the micro image size M """

        h, w = self._img.shape[:2]

        if isinstance(np.version.version, str):
            # use numpy vectorization
            self._centroids_refined = np.array(self._centroids_refined)
            valid_idx = (self._r < self._centroids_refined[:, 0]) & (self._centroids_refined[:, 0] < h - self._r) & \
                        (self._r < self._centroids_refined[:, 1]) & (self._centroids_refined[:, 1] < w - self._r)
            self._centroids_refined = list(self._centroids_refined[valid_idx])
        else:
            # inline for loop
            self._centroids_refined = [c for c in self._centroids_refined
                                       if self._r < c[0] < h-self._r and self._r < c[1] < w-self._r]

        return True

    def _get_coords(self):
        return self._t, self._s

    @property
    def centroids_refined(self):
        return np.asarray(self._centroids_refined)
