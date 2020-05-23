#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
Copyright (c) 2019 Christopher Hahne <info@christopherhahne.de>

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
import scipy

from plenopticam.lfp_calibrator.centroid_drawer import CentroidDrawer
from plenopticam.misc import PlenopticamStatus
from plenopticam.cfg import PlenopticamConfig


class LfpRotator(object):

    def __init__(self, lfp_img, mic_list, rad=None, cfg=None, sta=None):

        # input and output variable
        self._lfp_img = lfp_img
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else PlenopticamStatus()

        # internal variables
        self._centroids = np.asarray(mic_list)
        self._rad = rad

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # determine rotation angle (radians) of micro image centers (skip if angle already set)
        self._estimate_rad() if self._rad is None else None

        # rotate image
        self._rotate_img()

        # rotate centroids
        self._rotate_centroids()

        # write plot img to hard drive (debug only)
        if self.cfg.params[self.cfg.opt_dbug] and not self.sta.interrupt:
            self.sta.status_msg('Save rotated image (debug mode)')
            self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])
            CentroidDrawer(self._lfp_img, self._centroids, self.cfg).write_centroids_img(fn='lfp_rotated.png')
            self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def _estimate_rad(self, regression=True):

        # status update
        self.sta.status_msg('Rotation angle estimation', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # middle row and column indices
        self._mid_row_idx = int(self._centroids[:, 2].max()/2)
        self._mid_col_idx = int(self._centroids[:, 3].max()/2)

        # get central row and column
        mid_row = self._centroids[self._centroids[:, 2] == self._mid_row_idx][:, :2]
        mid_col = self._centroids[self._centroids[:, 3] == self._mid_col_idx][:, :2]
        mid_col = mid_col[0::2]     # leave out every other centroid in column to compensate for hexagonal array

        if regression:
            # ordinary least-squares linear regression
            slope_row, slope_col = self._regress_method(mid_row, mid_col)
        else:
            # mean gradient (for validation)
            slope_row, slope_col = self._gradient_method(mid_row, mid_col)

        # convert to radians
        rad_row = np.arctan(slope_row)
        rad_col = np.arctan(slope_col)

        # set rotation angle by averaging along both dimensions
        self._rad = (rad_row+rad_col*-1)/2

        # status update
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    @staticmethod
    def _regress_method(mid_row, mid_col):
        """ get slopes via ordinary least-squares linear regression """

        # horizontal slope
        A = np.vstack([np.ones(len(mid_row[:, 1])), mid_row[:, 1]]).T
        b = mid_row[:, 0]
        x = np.dot(np.linalg.pinv(A), b)
        slope_row = x[1]

        # vertical slope
        A = np.vstack([np.ones(len(mid_col[:, 0])), mid_col[:, 0]]).T
        b = mid_col[:, 1]
        x = np.dot(np.linalg.pinv(A), b)
        slope_col = x[1]

        return slope_row, slope_col

    @staticmethod
    def _gradient_method(mid_row, mid_col):
        """ get slopes for rotation using mean gradient """

        slope_row = np.mean(np.diff(mid_row[:, 0])/np.diff(mid_row[:, 1]))     # mean(diff(y)/diff(x))
        slope_col = np.mean(np.diff(mid_col[:, 1])/np.diff(mid_col[:, 0]))

        return slope_row, slope_col

    def _rotate_img(self):

        # status update
        self.sta.status_msg('Rotate image', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # convert radians to degrees
        deg_angle = self._rad*180/np.pi

        if deg_angle != 0:
            # rotate images (counter-clockwise) without reshape to retain shape of array
            self._lfp_img = scipy.ndimage.rotate(self._lfp_img, angle=deg_angle, reshape=False, order=3)

        # status update
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def _rotate_centroids(self):
        """ transformation of centroids via translation and rotation """

        # status update
        self.sta.status_msg('Rotate centroids', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # get image center coordinates
        img_center = (np.asarray(self._lfp_img.shape[:2])-1)/2.  # -1 for .5 decrement compensation in scipy rotate

        # translate data points to origin
        self._centroids[:, :2] -= img_center

        # matrix for counter-clockwise rotation around z-axis
        Rz = np.array([[np.cos(self._rad), -np.sin(self._rad)], [np.sin(self._rad), np.cos(self._rad)]])
        #Rz = np.array([[np.cos(self._rad), np.sin(self._rad)], [-np.sin(self._rad), np.cos(self._rad)]]) #clock-wise

        # rotate data points around z-axis
        self._centroids[:, :2] = np.dot(Rz, self._centroids[:, :2].T).T

        # translate data points back to image center
        self._centroids[:, :2] += img_center

        # status update
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    @property
    def lfp_img(self):
        return self._lfp_img.copy()

    @property
    def centroids(self):
        return self._centroids.tolist()

    def _rota_plot(self, slope):
        """ plots for debug purposes only """

        import matplotlib.pyplot as plt
        plt.figure()
        plt.imshow(self._lfp_img)
        plt.plot(np.array(self._centroids)[:, 1], np.array(self._centroids)[:, 0], 'rx')

        central_centroid = self._centroids[(self._centroids[:, 2] == self._mid_row_idx) &
                                           (self._centroids[:, 3] == self._mid_col_idx)].ravel()

        p1 = central_centroid[:2]
        p2 = ((self._lfp_img.shape[1]-central_centroid[1])*slope+central_centroid[0], self._lfp_img.shape[1])

        plt.plot((p1[1], p2[1]), (p1[0], p2[0]), 'b-')

        p3 = (self._lfp_img.shape[0], (self._lfp_img.shape[0]-central_centroid[0])*slope+central_centroid[1])

        plt.plot((p1[1], p3[1]), (p1[0], p3[0]), 'b-')
