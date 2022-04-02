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

import numpy as np
import operator

from plenopticam.lfp_calibrator.find_centroid import find_centroid
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc.status import PlenopticamStatus


class CentroidSorter(object):

    def __init__(self, centroids, cfg=None, sta=None, bbox=None):
        super(CentroidSorter, self).__init__()

        # input variables
        self._centroids = np.asarray(centroids)     # list of unsorted maxima
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else PlenopticamStatus()
        self._bbox = bbox if bbox is not None and len(bbox) == 2 else None

        # internal variables
        self._lens_x_max = None  # maximum number of "complete" micro image centers in a row
        self._lens_y_max = None  # maximum number of "complete" micro image centers in a column
        self._upper_l = None     # upper left centroid
        self._lower_r = None     # lower right centroid
        self._upper_r = None     # upper right centroid
        self._lower_l = None     # lower left centroid

        # output variables
        self._mic_list = []                     # list of micro image centers with indices assigned
        self._pattern = None                    # pattern typ of micro lens array
        self._pitch = None                      # average pitch in horizontal and vertical direction
        self._hex_odd = True                    # hexagonal shift of second row on the right (True) or left (False)

        # initialize parameters
        self._init_var()

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        try:
            # get maximum number of micro images in horizontal and vertical direction
            self._mla_dims()
        except IndexError:
            self.sta.status_msg(msg="Error in MLA dimension estimation", opt=self.cfg.params[self.cfg.opt_prnt])
            self.sta.error = True
            return False

        # sort MICs and assign 2-D indices to them
        self._assign_mic_idx()

        # attach results to config object if present
        if hasattr(self, 'cfg') and hasattr(self.cfg, 'calibs'):
            self.cfg.calibs[self.cfg.mic_list] = self._mic_list
            self.cfg.calibs[self.cfg.pat_type] = self._pattern
            self.cfg.calibs[self.cfg.ptc_mean] = self._pitch

        return True

    def _init_var(self):
        """ find most up-left and most bottom-right micro image centers """

        # iterate through all micro image centers and add up x and y coordinates
        sum_mic = sum([self._centroids[:, 0], self._centroids[:, 1]])

        # center coordinates of micro image being top and most left
        self._upper_l = self._centroids[np.argmin(sum_mic)]

        # center coordinates of micro image being bottom and most right
        self._lower_r = self._centroids[np.argmax(sum_mic)]

        # set bounding box of micro image center field
        self._bbox = (self._lower_r - self._upper_l).astype('int') if not self._bbox else self._bbox

        # estimate micro image pitch lengths and pattern type
        self._get_mla_pitch()

        # determine if hexagonal shift of second row on the right (True) or left (False)
        self._hex_odd = not self.estimate_odd(self._upper_l, 0, inv_dir=0)

        return True

    def _mla_dims(self, counterclockwise_opt: bool = True):
        """ search for complete rows and columns and count number of centroids in each direction """

        y_max_l, y_max_r, x_max_t, x_max_b = [0, 0, 0, 0]
        self._upper_r = self._lower_r
        self._lower_l = self._upper_l

        # walk along rectangle in a clock-wise manner to find valid corners with complete row/col (twice for upper_l)
        for _ in range(2):
            # top row (west to east)
            x_max_t, self._upper_r, self._upper_l = self._get_lens_count(self._upper_l, self._upper_r, axis=1, inv_dir=0, inwards=0)
            # most right column (north to south)
            y_max_r, self._lower_r, self._upper_r = self._get_lens_count(self._upper_r, self._lower_r, axis=0, inv_dir=0, inwards=1)
            # bottom row (east to west)
            x_max_b, self._lower_l, self._lower_r = self._get_lens_count(self._lower_r, self._lower_l, axis=1, inv_dir=1, inwards=1)
            # most left column (south to north)
            y_max_l, self._upper_l, self._lower_l = self._get_lens_count(self._lower_l, self._upper_l, axis=0, inv_dir=1, inwards=0)

        # counter-clockwise
        if counterclockwise_opt:
            # most left column (north to south)
            y_max_l, self._lower_l, self._upper_l = self._get_lens_count(self._upper_l, self._lower_l, axis=0, inv_dir=0, inwards=0)
            # bottom row (west to east)
            x_max_b, self._lower_r, self._lower_l = self._get_lens_count(self._lower_l, self._lower_r, axis=1, inv_dir=0, inwards=1)
            # most right column (south to north)
            y_max_r, self._upper_r, self._lower_r = self._get_lens_count(self._lower_r, self._upper_r, axis=0, inv_dir=1, inwards=1)
            # top row (east to west)
            x_max_t, self._upper_l, self._upper_r = self._get_lens_count(self._upper_r, self._upper_l, axis=1, inv_dir=1, inwards=0)

        # set safe number of micro lenses in each direction
        self._lens_y_max, self._lens_x_max = min(y_max_l, y_max_r), min(x_max_t, x_max_b)

        return self._lens_y_max, self._lens_x_max

    def _assign_mic_idx(self):

        # reorder MIC list by neighbour relationship
        last_neighbor = self._upper_l
        self._mic_list = []
        self._mic_list.append([last_neighbor[0], last_neighbor[1], 0, 0])
        j = 0
        odd = self._hex_odd
        row_len_odd = True

        # print status
        self.sta.status_msg('Sort micro image centers', self.cfg.params[self.cfg.opt_prnt])

        # jump to the next row
        for ly in range(self._lens_y_max):
            # find all centers in one row
            for lx in range(self._lens_x_max-1):    # -1 to account for first row center which is already found
                # get adjacent MIC
                found_center = find_centroid(self._centroids, last_neighbor, self._pitch, 1, 'rec', None)
                # retrieve single MIC
                if len(found_center) != 2:
                    if len(found_center) > 2:
                        # average of found centroids
                        found_center = np.mean(found_center.reshape(-1, 2), axis=0)
                    else:
                        # skip when looking for last MIC with unequal row length
                        if lx == self._lens_x_max-1 and (row_len_odd or self._pattern == 'rec'):
                            break
                        # create missing centroid
                        found_center = self._mic_list[j][:2]+np.array([0, self._pitch[1]])
                j += 1
                self._mic_list.append([found_center[0], found_center[1], ly, lx+1])
                last_neighbor = found_center
            # find most-left center of next row
            if ly < self._lens_y_max-1:
                # get adjacent MIC
                found_center = find_centroid(self._centroids, self._upper_l, self._pitch, 0, self._pattern, odd)
                # retrieve single MIC
                if len(found_center) != 2:
                    if len(found_center) > 2:
                        # average of found centroids
                        found_center = np.mean(found_center.reshape(-1, 2), axis=0)
                    else:
                        # create missing centroid (considering MLA packing)
                        if self._pattern == 'rec':
                            found_center = self._upper_l + np.array([self._pitch[0], 0])
                        elif self._pattern == 'hex':
                            if odd:
                                found_center = self._upper_l + np.array([self._pitch[0], +self._pitch[1]/2])
                            else:
                                found_center = self._upper_l + np.array([self._pitch[0], -self._pitch[1]/2])
                j += 1
                self._mic_list.append([found_center[0], found_center[1], ly+1, 0])
                last_neighbor = found_center
                self._upper_l = found_center
                odd = not odd

            # check interrupt status
            if self.sta.interrupt:
                return False

            # print progress status on console
            self.sta.progress((ly+1)/self._lens_y_max*100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def _estimate_mla_geometry(self, pitch: float = None):
        """ This function determines whether the geometric arrangement of micro lenses is rectangular or hexagonal.

        :param pitch: scalar of type int or float representing the spacing between micro image centers
        :return: pattern, e.g. 'hex' or 'rec'
        """

        # pick arbitrary micro image center in middle of centroid list
        ref_point = self._centroids[len(self._centroids)//2][:2]

        # obtain list of adjacent centroids
        euc_dst = np.sum((self._centroids[:, :2]-ref_point)**2, axis=1)**.5
        adj_cnd = (pitch*.5 < euc_dst) & (pitch*1.5 > euc_dst)
        adj_pts = self._centroids[:, :2][adj_cnd]

        # place adjacent points at origin
        vecs = np.abs(adj_pts-ref_point)

        # create reference vectors at 45 degrees
        refs = np.repeat(np.array([1, 1])[..., None], vecs.shape[0], axis=1).T

        # element-wise dot product for angles
        angles = np.arccos(np.einsum('ij,ij->i', refs, vecs)/np.sqrt(2*np.einsum('ij,ij->i', vecs, vecs)))*180/np.pi

        # numeric angle reduction to account for tolerances (0 => 45 degs; 1 => 30 degs; 2 => 15 degs; 3 => 0 degs)
        angles = np.rint(angles / 15)

        # hexagonal angles
        if (sum(angles == 1) >= 1 and sum(angles == 3) >= 1) or (sum(angles == 2) >= 1 and sum(angles == 0) >= 1):
            self._pattern = 'hex'
        # rectangular angles
        elif sum(angles == 0) >= 0 and sum(angles == 3) >= 1:
            self._pattern = 'rec'
        else:
            self.sta.status_msg("Geometric MLA arrangement not recognized", opt=self.cfg.params[self.cfg.opt_prnt])
            self.sta.error = True
            return False

        return self._pattern

    def _get_mla_pitch(self):
        """
        get horizontal spacing estimate (pitch in px)
        """

        # use aspect ratio for "many" micro images
        if len(self._centroids) > 30**2:

            # get aspect ratio of bounding box
            aspect_ratio = self._bbox[1] / self._bbox[0]

            # get micro lens array dimensions
            J = np.sqrt(len(self._centroids) * aspect_ratio**-1)
            H = np.sqrt(len(self._centroids) * aspect_ratio)

            # use aspect ratio for pitch estimate
            pitch_x = self._bbox[1] / H

        # for fewer micro images use average pitch analysis
        else:
            pitch_diff = np.diff(self._centroids[:, 1])
            pitch_diff = pitch_diff[pitch_diff > 0]
            pitch_x = np.mean(pitch_diff[(pitch_diff <= np.mean(pitch_diff) + np.std(pitch_diff)) &
                                         (pitch_diff >= np.mean(pitch_diff) - np.std(pitch_diff))])

        # estimate MLA packing geometry
        self._estimate_mla_geometry(pitch_x)

        # get vertical spacing estimate (pitch in px) under consideration of packing type
        pitch_y = pitch_x * np.sqrt(3)/2 if self._pattern == 'hex' else pitch_x

        # store pitch values
        self._pitch = [pitch_y, pitch_x]

        return True

    def _get_lens_count(self, start_mic, opposite_mic, axis=0, inv_dir=0, inwards=0):

        cur_mic = start_mic
        lens_max = 1    # start to count from 1 to take existing centroid into account
        odd = self._hex_odd and not inwards if not inv_dir else not (self._hex_odd and inwards)
        start_odd = odd
        comp_a, comp_b = (operator.gt, operator.lt) if inv_dir else (operator.lt, operator.gt)
        pm_a, pm_b = (operator.sub, operator.add) if inv_dir else (operator.add, operator.sub)

        # iterate through row or column (as long as possible)
        while comp_a(cur_mic[axis], pm_a(opposite_mic[axis], self._pitch[axis]/2)):
            # get adjacent MIC
            found_center = find_centroid(self._centroids, cur_mic, self._pitch, axis=axis,
                                         pattern=self._pattern, odd=odd, inv_dir=inv_dir)
            if len(found_center) != 2:
                if len(found_center) > 2:
                    # average found centroids
                    found_center = np.mean(found_center.reshape(-1, 2), axis=0)
                else:
                    # restart with new row / column (extend search window e to ensure new start_mic is found)
                    start_odd = not start_odd   # reset hex search direction (flip for next not odd)
                    start_mic = find_centroid(self._centroids, start_mic, self._pitch, axis=not axis,
                                              pattern=self._pattern, odd=start_odd, e=3.5, inv_dir=inwards)
                    found_center = start_mic
                    lens_max = 0    # assign zero as number is incremented directly hereafter
                    odd = start_odd
            lens_max += 1
            cur_mic = found_center
            odd = not odd

            # stop if close to border (represented by opposite centroid)
            if comp_b(cur_mic[axis], pm_b(opposite_mic[axis], 1 * self._pitch[axis] / 4)):
                break

        return lens_max, cur_mic, start_mic

    def estimate_odd(self, mic, axis, inv_dir=0):
        # look if hex shift in next row/col is left/top of the MIC and yield True if so
        return find_centroid(self._centroids, mic, self._pitch, axis, 'hex', odd=0, inv_dir=inv_dir).size == 0

    @property
    def mic_list(self):
        return self._mic_list

    @property
    def pattern(self):
        return self._pattern

    @property
    def pitch(self):
        return self._pitch
