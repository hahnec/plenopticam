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

# local imports
from plenopticam.misc import uint8_norm, save_img_file, rgb2gray
from plenopticam.cfg import Config

class CentroidDrawer(object):

    def __init__(self, img, centroids, cfg=None):

        # input variables
        self._img = uint8_norm(rgb2gray(img.copy()))
        self._centroids = np.asarray(centroids)
        self.cfg = cfg if cfg is not None else Config()


    def write_centroids_img(self, fn='default_filename.png'):

        # draw MICs in binary image and save image file for debug purposes
        if self.cfg.params[self.cfg.opt_dbug]:

            plot_img = self.draw_centroids_img()
            save_img_file(plot_img, os.path.join(os.path.splitext(self.cfg.params[self.cfg.lfp_path])[0], fn))
            # plot_centroids(img, centroids)

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
        ''' prevent wrap-around for np.array() '''

        x = (a - b)
        x[b > a] = 0

        return x

    # def plot_centroids(self):
    #
    #     try:
    #         import matplotlib.pyplot as plt
    #     except ImportError:
    #         raise ImportError("Package matplotlib wasn't found.")
    #
    #     plt.figure()
    #     plt.imshow(self._img)
    #     plt.plot(self._centroids[:, 1], self._centroids[:, 0], 'rx')
    #     plt.show()
    #     #plt.savefig('input+mics.png')
    #
    #     return True