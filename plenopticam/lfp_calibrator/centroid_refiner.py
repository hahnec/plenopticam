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
from plenopticam.misc.status import PlenopticamStatus

DR = 1

class CentroidRefiner(object):

    def __init__(self, img, centroids, cfg, sta=None, M=None, method=None):

        # input variables
        self._img = img
        self._centroids = centroids
        self.cfg = cfg
        self.sta = sta if sta is not None else PlenopticamStatus()
        self._M = M
        self._method = method if method is not None else 'area'

        # internal variables
        self._t = self._s = 0

        # output variables
        self._centroids_refined = []

    def main(self):

        # status message handling
        self.sta.status_msg('Refine micro image centers', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        fun = self._peak_centroid if self._method == 'peak' else self._area_centroid

        # coordinate and image downsampling preparation
        self._centroids = [(x//DR, y//DR) for x, y in self._centroids]
        img_scale = self._img[::DR, ::DR]

        r = self._M//2//DR
        self._centroids_refined = []

        # iterate through all centroids for refinement procedure
        for i, m in enumerate(self._centroids):

            # check interrupt status
            if self.sta.interrupt:
                return False

            # compute refined coordinates based on given method
            fun(img_scale[m[0]-r:m[0]+r+1, m[1]-r:m[1]+r+1], m)
            self._centroids_refined.append(self._get_coords())

            # print status
            self.sta.progress((i+1)/len(self._centroids)*100, self.cfg.params[self.cfg.opt_prnt])

        # coordinate upsampling to compensate for downsampling
        self._centroids_refined = [(x*DR, y*DR) for x, y in self._centroids_refined]

        return True

    def _area_centroid(self, input_win, p):

        # parameter init
        r = int(input_win.shape[0]/2)
        weight_win = input_win / input_win.max()

        # window thresholding
        th_img = np.zeros_like(input_win, dtype=np.bool)
        th_val = np.percentile(weight_win, 50)
        th_img[weight_win > th_val] = 1
        if np.sum(th_img) == 0:
            raise Exception('Binary object not found')

        # binary centroid calculation in window
        count = (th_img == 1).sum()
        self._t, self._s = np.argwhere(th_img == 1).sum(0)/count if count > 0 else (float('nan'), float('nan'))
        self._t += p[0]-r
        self._s += p[1]-r

        return True

    def _peak_centroid(self, input_win, p):

        # parameter init
        r = int(input_win.shape[0]/2)
        weight_win = input_win / input_win.sum()
        self._t = self._s = 0

        # weighted centroid calculation in window
        for i in range(weight_win.shape[0]):
            for j in range(weight_win.shape[1]):
                self._t += (i+p[0]-r)*weight_win[i, j]
                self._s += (j+p[1]-r)*weight_win[i, j]

        #plt.plot(s-(x-r), t-(y-r), 'xb') # for validation
        return True

    def _get_coords(self):
        return self._t, self._s

    @property
    def centroids_refined(self):
        return self._centroids_refined
