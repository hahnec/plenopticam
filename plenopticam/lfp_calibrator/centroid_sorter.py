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
from plenopticam.lfp_calibrator.find_centroid import find_centroid
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc.status import PlenopticamStatus

# external libs
import numpy as np


class CentroidSorter(object):

    def __init__(self, centroids, cfg=None, sta=None, bbox=None):

        # input variables
        self._centroids = np.asarray(centroids)     # list of unsorted maxima
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else PlenopticamStatus()
        self._bbox = bbox if bbox is not None and len(bbox) == 2 else None

        # internal variables
        self._lens_x_max = None  # maximum number of "complete" micro image centers in a row
        self._lens_y_max = None  # maximum number of "complete" micro image centers in a column
        self._upper_l = None
        self._lower_r = None

        # output variables
        self._mic_list = []                     # list of micro image centers with indices assigned
        self._pattern = None                    # pattern typ of micro lens array
        self._pitch = None                      # average pitch in horizontal and vertical direction

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # initialize parameters
        self._init_var()

        # estimate micro image pitch lengths and pattern type
        self._get_mla_pitch()

        try:
            # get maximum number of micro images in horizontal and vertical direction
            self._mla_dims()
        except IndexError:
            self.sta.status_msg("Error in MLA dimension estimation indicating arbitrarily spaced centroids")
            self.sta.error = True
            return False

        # sort MICs and assign 2-D indices to them
        self._assign_mic_idx()

        return True

    def _init_var(self):
        """ find most up-left and most bottom-right micro image centers """

        # iterate through all micro image centers and add up x and y coordinates
        sum_mic = sum([self._centroids[:, 0].astype(float, copy=False), self._centroids[:, 1].astype(float, copy=False)])

        # center coordinates of micro image being top and most left
        self._upper_l = self._centroids[np.where(sum_mic == sum_mic.min())[0][0]]

        # center coordinates of micro image being bottom and most right
        self._lower_r = self._centroids[np.where(sum_mic == sum_mic.max())[0][0]]

        # set bounding box of micro image center field
        self._bbox = (self._lower_r - self._upper_l).astype('int') if not self._bbox else self._bbox

        return True

    def _mla_dims(self):
        """ search for complete rows and columns and count number of lenses in each direction """

        # set max top and upper right
        x_max_t, upper_r, self._upper_l = self._get_lens_max(self._upper_l, 1)

        # set max left and lower right
        y_max_l, lower_l, self._upper_l = self._get_lens_max(self._upper_l, 0)

        # set max right
        for _ in range(5):      # jump some columns left
            new_centroid = find_centroid(self._centroids, upper_r, self._pitch, 1, 'rec', backwards=True)
            if new_centroid.size == 2:
                upper_r = new_centroid
        y_max_r = self._get_lens_max(upper_r, 0)[0]

        # set max bottom
        odd = True
        for _ in range(5):      # jump some rows up
            new_centroid = find_centroid(self._centroids, lower_l, self._pitch, 0, self._pattern, odd, backwards=True)
            if new_centroid.size == 2:
                lower_l = new_centroid
                odd = not odd
        x_max_b = self._get_lens_max(lower_l, 1)[0]

        # set maximum number of micro lenses in each direction
        self._lens_y_max, self._lens_x_max = min(y_max_l, y_max_r), min(x_max_t, x_max_b)

        return True

    def _assign_mic_idx(self):

        # reorder MIC list by neighbour relationship
        last_neighbor = self._upper_l
        self._mic_list = []
        self._mic_list.append([last_neighbor[0], last_neighbor[1], 0, 0])
        j = 0
        odd = self.estimate_odd(self._upper_l, axis=0)
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

    def _estimate_mla_geometry(self, pitch):
        """ This function determines whether the geometric arrangement of micro lenses is rectangular or hexagonal.

        :param pitch: scalar of type int or float representing the spacing between micro image centers
        :return: pattern, e.g. 'hex' or 'rec'
        """

        # pick arbitrary micro image center in middle of centroid list
        ref_point = self._centroids[len(self._centroids)//2]

        # obtain list of adjacent centroids
        adj_pts = np.array([pt for pt in self._centroids if pitch*.5 < sum((pt-ref_point)**2)**.5 < pitch*1.5])

        # create vectors and references at 45 degrees
        vectors = np.abs(adj_pts-ref_point)
        ref_vec = np.repeat(np.array([1, 1])[..., None], vectors.shape[0], axis=1).T

        # element-wise vector normalization
        vec_a_arr = ref_vec / np.linalg.norm(ref_vec, axis=-1)[..., None]
        vec_b_arr = vectors / np.linalg.norm(vectors, axis=-1)[..., None]

        # element-wise dot product for angles
        angles = np.arccos(np.einsum('ij,ij->i', vec_a_arr, vec_b_arr))*180/np.pi

        # numeric angle reduction to account for tolerances
        angles = np.rint(angles / 15)

        # hexagonal angles (at least 2 neighbours at 15 deg)
        if sum(angles == 1) > 1 and sum(angles == 3) > 1:
            self._pattern = 'hex'
        # rectangular angles (at least 2 neighbours at 0 deg and 2 neighbours at 45 deg)
        elif sum(angles == 0) > 1 and sum(angles == 3) > 1:
            self._pattern = 'rec'
        else:
            self.sta.status_msg("Geometric MLA arrangement unrecognized")
            self.sta.error = True
            return False

        return self._pattern

    def _get_mla_pitch(self):

        # get aspect ratio of bounding box
        aspect_ratio = self._bbox[1] / self._bbox[0]

        # get micro lens array dimensions
        J = np.sqrt(len(self._centroids) * aspect_ratio**-1)
        H = np.sqrt(len(self._centroids) * aspect_ratio)

        # get horizontal spacing estimate (pitch in px)
        if len(self._centroids) > 30**2:
            # use aspect ratio for "many" micro images
            pitch_x = self._bbox[1] / H
        else:
            # for fewer micro images use average pitch analysis
            pitch_diff = np.diff(self._centroids[:, 1])
            pitch_diff = pitch_diff[pitch_diff > 0]
            sig = 1
            pitch_x = np.mean(pitch_diff[(pitch_diff < np.mean(pitch_diff) + sig*np.std(pitch_diff)) &
                                         (pitch_diff > np.mean(pitch_diff) - sig*np.std(pitch_diff))])

        # estimate MLA packing geometry
        self._estimate_mla_geometry(pitch_x)

        # get vertical spacing estimate (pitch in px) under consideration of packing type
        if self._pattern == 'rec':
            pitch_y = pitch_x
        elif self._pattern == 'hex':
            pitch_y = pitch_x * np.sqrt(3)/2
        else:
            pitch_y = pitch_x

        # store pitch values
        self._pitch = [pitch_y, pitch_x]

        return True

    def _get_lens_max(self, start_mic, axis=0):

        cur_mic = start_mic
        lens_max = 1    # start with 1 to account for upper left centroid
        odd = self.estimate_odd(start_mic, axis)

        # check if column of upper left is complete
        while cur_mic[axis] < self._lower_r[axis] + self._pitch[axis]/2:
            # get adjacent MIC
            found_center = find_centroid(self._centroids, cur_mic, self._pitch, axis, self._pattern, odd)
            odd = not odd
            if len(found_center) != 2:
                if len(found_center) > 2:
                    # average of found centroids
                    found_center = np.mean(found_center.reshape(-1, 2), axis=0)
                else:
                    if cur_mic[axis] > (self._bbox[axis] - self._pitch[axis]/2):
                        break
                    else:
                        odd = self.estimate_odd(start_mic, axis)
                        start_mic = find_centroid(self._centroids, start_mic, self._pitch, not axis, self._pattern, not odd)
                        found_center = start_mic
                        lens_max = 0
            lens_max += 1
            cur_mic = found_center

        return lens_max, cur_mic, start_mic

    def estimate_odd(self, cur_mic, axis):
        return find_centroid(self._centroids, cur_mic, self._pitch, axis, 'hex', odd=False).size == 0

    @property
    def mic_list(self):
        return self._mic_list

    @property
    def pattern(self):
        return self._pattern

    @property
    def pitch(self):
        return self._pitch
