#!/usr/bin/env python

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

# local imports
from plenopticam.lfp_calibrator.non_max_supp import NonMaxSuppression
from plenopticam.lfp_calibrator.centroid_refiner import CentroidRefiner
from plenopticam.misc import create_gauss_kernel
from plenopticam.misc.status import PlenopticamStatus

# external libs
import numpy as np
import scipy

DR = 1  # down-sample rate

class CentroidExtractor(object):

    def __init__(self, img, cfg, sta=None, M=None, method=None):

        # input variables
        self._img = img
        self._cfg = cfg
        self._sta = sta if sta is not None else PlenopticamStatus()
        self._M = M if M is not None else 9
        self._method = method if method is not None else 'area'

        # private variables
        self._peak_img = self._img.copy()
        self._centroids = []

    def main(self):

        # compute LoG to remove high frequency noise and carve out peaks
        self.compute_log()

        # find micro image centers
        self.compute_centroids()

        if self._method is not None:
            # refine centroids with sub-pixel precision using provided method
            ref_obj = CentroidRefiner(self._img, self._centroids, self._cfg, self._sta, self._M, method=self._method)
            ref_obj.main()
            self._centroids = ref_obj.centroids_refined
            del ref_obj

        return True

    def compute_log(self):
        ''' compute Laplacian of Gaussian (LoG) '''

        # print status
        self._sta.status_msg('Compute LoG', self._cfg.params[self._cfg.opt_prnt])

        # Gaussian sigma
        sig = int(self._M/4)/1.18#int(self._M/2)/np.sqrt(2)

        # convolutions
        laplace_kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
        gauss_kernel = create_gauss_kernel(int(sig*6), sig)
        mexican_hat = -scipy.signal.convolve2d(gauss_kernel, laplace_kernel)[2:-2, 2:-2] #sig**2 *
        self._peak_img = scipy.signal.convolve2d(self._img, mexican_hat, 'same')

        # print progress
        self._sta.progress(100, self._cfg.params[self._cfg.opt_prnt])

        return True

    def compute_centroids(self):
        ''' find coordinates of micro image centers '''

        # compute local maxima with non-maximum suppression (NMS) using Down-sampling Rate (DR)
        nms_obj = NonMaxSuppression(self._peak_img[::DR, ::DR], self._cfg, self._sta)
        nms_obj.main()
        max_idx = nms_obj.idx * DR   # multiply by DR to compensate for index
        del nms_obj

        # remove indices at image borders and create list of valid integer centroid values
        h, w = self._peak_img.shape[:2]
        r = int(self._M/2)-1  # pixel distance from image border telling which maxima are excluded
        valid_idx = np.where((max_idx[0] > r) & (max_idx[1] > r) & (h-max_idx[0] > r) & (w-max_idx[1] > r))[0]
        self._centroids = list(zip(max_idx[0][valid_idx], max_idx[1][valid_idx]))

        return True

    @property
    def centroids(self):
        return self._centroids
