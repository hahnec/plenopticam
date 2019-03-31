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
from plenopticam.lfp_calibrator.find_centroid import find_centroid, find_centroid_backwards
from plenopticam.misc.status import PlenopticamStatus

# external libs
import numpy as np

class CentroidSorter(object):

    def __init__(self, centroids, cfg, sta=None):

        # input variables
        self._centroids = np.asarray(centroids)     # list of unsorted maxima
        self.cfg = cfg                              # config file
        self.sta = sta if sta is not None else PlenopticamStatus()

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
        self._calc_mla_struc()

        # get maximum number of micro images in horizontal and vertical direction
        self._mla_dims()

        # sort MICs and assign 2-D indices to them
        self._assign_mic_idx()

        return True

    def _init_var(self):
        ''' find most up-left and most bottom-right micro image centers '''

        # iterate through all micro image centers and add up x and y coordinates
        sum_mic = sum([self._centroids[:, 0].astype(float, copy=False), self._centroids[:, 1].astype(float, copy=False)])

        # center coordinates of micro image being top and most left
        self._upper_l = self._centroids[np.where(sum_mic == sum_mic.min())[0][0]]

        # center coordinates of micro image being bottom and most right
        self._lower_r = self._centroids[np.where(sum_mic == sum_mic.max())[0][0]]

        # set bounding box of micro image center field
        self._bounding_box = (self._lower_r-self._upper_l).astype('int')

        return True

    def _mla_dims(self):
        ''' search for complete rows and columns and count number of lenses in each direction '''

        # set max top and upper right
        x_max_t, upper_r, self._upper_l = self._get_lens_max(self._upper_l, 1)   #self.mic_row_check(self._upper_l)

        # set max left and lower right
        y_max_l, lower_l, self._upper_l = self._get_lens_max(self._upper_l, 0)   #self.mic_col_check(self._upper_l)

        # set max right
        for i in range(5): # jump some columns left
            new_centroid = find_centroid_backwards(self._centroids, upper_r, self._pitch, 1, 'rec')
            if new_centroid.size is 2:
                upper_r = new_centroid
        y_max_r = self._get_lens_max(upper_r, 0)[0]  #self.mic_col_check(upper_r)[0]

        # set max bottom
        odd = True
        for i in range(5): # jump some rows up (even number for hex pattern?)
            new_centroid = find_centroid_backwards(self._centroids, lower_l, self._pitch, 0, self._pattern, odd)
            if new_centroid.size is 2:
                lower_l = new_centroid
                odd = not odd
        x_max_b = self._get_lens_max(lower_l, 1)[0]  #self.mic_row_check(lower_l)[0]

        # set maximum number of micro lenses in each direction
        self._lens_y_max, self._lens_x_max = min(y_max_l, y_max_r), min(x_max_t, x_max_b)

        return True

    def _assign_mic_idx(self):

        # reorder MIC list by neighbour relationship
        last_neighbor = self._upper_l
        self._mic_list = []
        self._mic_list.append([last_neighbor[0], last_neighbor[1], 0, 0]) # = np.concatenate([[1, 1], last_neighbor])
        j = 0
        odd = True if find_centroid(self._centroids, self._upper_l, self._pitch, 0, 'hex', False).size == 0 else False

        # print status
        self.sta.status_msg('Sort micro image centers', self.cfg.params[self.cfg.opt_prnt])

        # jump to the next row
        for ly in range(self._lens_y_max):
            # find all centers in one row
            for lx in range(self._lens_x_max-1):
                # get adjacent MIC
                found_center = find_centroid(self._centroids, last_neighbor, self._pitch, 1, 'rec', None)
                # retrieve missing MIC
                if len(found_center) != 2:
                    if len(found_center) > 2:
                        found_center = np.mean(found_center.reshape(-1, 2), axis=0) # average over found centroids
                    else:
                        found_center = self._mic_list[j][:2]+np.array([0, self._pitch[1]])
                j += 1
                self._mic_list.append([found_center[0], found_center[1], ly, lx+1])
                last_neighbor = found_center
            # find most-left center of next row
            if ly < self._lens_y_max-1:
                # get adjacent MIC
                found_center = find_centroid(self._centroids, self._upper_l, self._pitch, 0, self._pattern, odd)
                # retrieve missing MIC
                if len(found_center) != 2:
                    if len(found_center) > 2:
                        found_center = np.mean(found_center.reshape(-1, 2), axis=0) # average over found centroids
                    else:
                        if self._pattern == 'rec':
                            found_center = self._upper_l + np.array([self._pitch[0], 0])
                        elif self._pattern == 'hex':
                            if odd:
                                found_center = self._upper_l + np.array([self._pitch[0], +self._pitch[1]/2])
                            else:
                                found_center = self._upper_l + np.array([self._pitch[0], -self._pitch[1]/2])
                elif len(found_center) > 2:
                    found_center = found_center[:2]
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

    def _calc_pattern(self, pitch):

        point = self._centroids[int(len(self._centroids)/2)]
        diff_vertical = []
        pattern_list = ['rec', 'hex']

        for pattern in pattern_list:
            k = 1 if pattern == 'rec' else np.sqrt(3) / 2
            adj_vertical = find_centroid(self._centroids, point, [k*pitch, pitch], axis=0, pattern=pattern)
            if list(adj_vertical):
                diff_vertical.append(abs(k*pitch - abs(adj_vertical[0] - point[0])))
            else:
                diff_vertical.append(float('inf'))

        self._pattern = pattern_list[np.array(diff_vertical).argmin()]

        return True

    def _calc_mla_struc(self):

        # get aspect ratio of bounding box
        aspect_ratio = self._bounding_box[1] / self._bounding_box[0]

        # estimate array dimensions under consideration of aspect ratio
        s = t = np.sqrt(len(self._centroids))
        tol = 3
        fun = lambda x: aspect_ratio - x[1] / x[0]
        min_val = round(fun([t, s]), tol)
        while(min_val != 0):
            if min_val > 0:
                s += .1
            elif min_val < 0:
                s -= .1
            t = len(self._centroids)/s
            min_val = round(fun([t, s]), tol)

        # estimate horizontal spacing (pitch in px)
        pitch_x = self._bounding_box[1] / s

        # estimate pattern
        self._calc_pattern(pitch_x)

        # estimate vertical spacing (pitch in px) under consideration of pattern type
        if self._pattern == 'rec':
            pitch_y = self._bounding_box[0] / t
        elif self._pattern == 'hex':
            pitch_y = self._bounding_box[0] / t * np.sqrt(3)/2
        else:
            pitch_y = pitch_x

        # store pitch values
        self._pitch = [pitch_y, pitch_x]

        return True

    def _get_lens_max(self, start_mic, axis=0):

        lens_max = 0
        cur_mic = start_mic
        odd = True if find_centroid(self._centroids, start_mic, self._pitch, axis, 'hex', False).size == 0 else False

        # check if column of upper left is complete
        while cur_mic[axis] < self._bounding_box[axis]:
            # get adjacent MIC
            found_center = find_centroid(self._centroids, cur_mic, self._pitch, axis, self._pattern, odd)
            odd = not odd
            lens_max += 1
            if len(found_center) != 2:
                if len(found_center) > 2:
                    found_center = np.mean(found_center.reshape(-1, 2), axis=0)  # average over found centroids
                else:
                    if cur_mic[axis] > (self._bounding_box[axis] - 1.5*self._pitch[axis]):
                        break
                    else:
                        found_center = find_centroid(self._centroids, cur_mic, self._pitch, axis, self._pattern, odd)
                        if len(found_center) != 2:
                            if len(found_center) > 2:
                                found_center = np.mean(found_center.reshape(-1, 2), axis=0)  # average over found centroids
                            else:
                                if self._pattern == 'rec':
                                    start_mic = start_mic + np.array([self._pitch[0], 0])
                                elif self._pattern == 'hex':
                                    if odd:
                                        start_mic = start_mic + np.array([self._pitch[0], +self._pitch[1]/2])
                                    else:
                                        start_mic = start_mic + np.array([self._pitch[0], -self._pitch[1]/2])
                                found_center = start_mic
                        else:
                            start_mic = found_center
                        #odd = not odd
                        lens_max = 0
            cur_mic = found_center

        return lens_max, cur_mic, start_mic

    @property
    def mic_list(self):
        return self._mic_list

    @property
    def pattern(self):
        return self._pattern

    @property
    def pitch(self):
        return self._pitch
