#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2021 Christopher Hahne <info@christopherhahne.de>

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
from scipy.spatial.distance import cdist

from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc.status import PlenopticamStatus
from plenopticam.lfp_calibrator.centroid_sorter import CentroidSorter
from plenopticam.lfp_calibrator.grid_fitter import GridFitter


class CentroidFitSorter(CentroidSorter, GridFitter):

    # force hexagonal shift of second row to be on the right of the upper left
    #_hex_odd = True

    def __init__(self, *args, **kwargs):
        super(CentroidFitSorter, self).__init__(*args, **kwargs)

        self.corner_mics = []

        self.keep_pts_opt = False if 'keep_pts_opt' not in kwargs else kwargs['keep_pts_opt']

    def corner_fit(self, norm_type: int = 1):

        # estimate MLA dimensions
        self._mla_dims()
        self._get_mla_pitch()
        self._estimate_mla_geometry(self._pitch[0])

        # extract MLA corner centroids
        self.corner_mics = np.vstack([self._upper_l, self._upper_r, self._lower_l, self._lower_r])
        self.corner_mics = np.hstack([self.corner_mics, np.array([[0, 0], [0, 1], [1, 0], [1, 1]])])

        # 4-corners (8 coordinate) projection fit
        corner_fitter = GridFitter(coords_list=self.corner_mics, pat_type=self.pattern, hex_odd=None, normalize=norm_type)
        corner_fitter._MAX_X = self._lens_x_max
        corner_fitter._MAX_Y = self._lens_y_max
        corner_fitter.coeff_fit(euclid_opt=False)
        coeffs = corner_fitter._coeffs

        # generate grid based on 4-corner (8 coordinate) fit
        ruff_pts = GridFitter.grid_gen(dims=[self._lens_y_max, self._lens_x_max], pat_type=self.pattern, hex_odd=None, normalize=norm_type)
        ruff_fit = corner_fitter.apply_transform(coeffs, ruff_pts.copy())
        del corner_fitter

        # validation
        for pts in [self._centroids, ruff_fit]:
            dres = cdist(pts[:, :2], self.corner_mics[:, :2], 'euclidean')
            self.idxs = np.argmin(dres, axis=0)
            assert np.sum(np.square(pts[self.idxs, :2] - self.corner_mics[:, :2])) < min(self._pitch)/2

        # validate centroid index assignments
        assert ruff_fit[self.idxs][0][2] == 0 and ruff_fit[self.idxs][0][3] == 0
        assert ruff_fit[self.idxs][1][2] == 0 and ruff_fit[self.idxs][1][3] == max(ruff_fit[:, 3])
        assert ruff_fit[self.idxs][2][2] == max(ruff_fit[:, 2]) and ruff_fit[self.idxs][2][3] == 0
        assert ruff_fit[self.idxs][3][2] == max(ruff_fit[:, 2]) and ruff_fit[self.idxs][3][3] == max(ruff_fit[:, 3])

        return ruff_fit.tolist()

    def match_points(self, centroids, fit_points):

        sorted_mics = fit_points.copy()
        centroid_rows = int(max(fit_points[:, 2]))

        # iterate through centroid rows (cdist array can easily require large amounts of memory)
        for i in range(centroid_rows):

            # select next row of indexed points
            frow = fit_points[fit_points[:, 2] == i]

            # measure distance between fitted and actual centroids
            dres = cdist(centroids[:, :2], frow[:, :2], 'euclidean')

            # determine indices and distance of closest actual centroids to each fitted/index point
            idxs = np.argmin(dres, axis=0)
            mins = np.min(dres, axis=0)

            # use threshold to exclude points which are too far away
            thrs = mins < min(self._pitch)/2

            # copy actual centroid peaks (fulfilling euclidean threshold) to the fitted grid
            sorted_mics[sorted_mics[:, 2] == i][thrs, :2] = self._centroids[:, :2][idxs][thrs, :2]

        return sorted_mics

    def main(self, keep_pts_opt=None):

        self.keep_pts_opt = keep_pts_opt if keep_pts_opt is not None else self.keep_pts_opt

        ruff_fit = self.corner_fit()
        if self.keep_pts_opt:
            self._mic_list = self.match_points(self._centroids, np.array(ruff_fit))
        else:
            self._mic_list = ruff_fit

        # attach results to config object if present
        if hasattr(self, 'cfg') and hasattr(self.cfg, 'calibs'):
            self.cfg.calibs[self.cfg.mic_list] = self._mic_list
            self.cfg.calibs[self.cfg.pat_type] = self._pattern
            self.cfg.calibs[self.cfg.ptc_mean] = self._pitch

        return ruff_fit