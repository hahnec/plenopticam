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

from plenopticam.cfg import PlenopticamConfig
from plenopticam import misc

import numpy as np
import os


class LfpMicroLenses(object):

    def __init__(self, *args, **kwargs):

        # variables
        self._lfp_img = kwargs['lfp_img'] if 'lfp_img' in kwargs else None
        self._wht_img = kwargs['wht_img'] if 'wht_img' in kwargs else None
        self._lfp_img_align = kwargs['lfp_img_align'] if 'lfp_img_align' in kwargs else None
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else misc.PlenopticamStatus()
        self._M = 0
        self._C = 0

        # convert to float
        self._lfp_img = self._lfp_img.astype('float64') if self._lfp_img is not None else None
        self._wht_img = self._wht_img.astype('float64') if self._wht_img is not None else None

        if self.cfg.calibs:
            # micro lens array variables
            self._CENTROIDS = np.asarray(self.cfg.calibs[self.cfg.mic_list])
            self._LENS_Y_MAX = int(max(self._CENTROIDS[:, 2])+1)    # +1 to account for index 0
            self._LENS_X_MAX = int(max(self._CENTROIDS[:, 3])+1)    # +1 to account for index 0

        # get pitch from aligned light field
        self._M = self.lfp_align_pitch() if hasattr(self, '_lfp_img') else self._M

        # get mean pitch from centroids
        mean_pitch = self.centroid_avg_pitch(self._CENTROIDS) if hasattr(self, '_CENTROIDS') else self._M

        # evaluate mean pitch size and user pitch size
        self._Mn = self.safe_pitch_eval(mean_pitch=mean_pitch, user_pitch=int(self.cfg.params[self.cfg.ptc_leng]))

        # check if chosen micro image size too large
        if 0 < self._M < self._Mn:
            # remove existing pickle file
            fp = os.path.join(self.cfg.exp_path, 'lfp_img_align.pkl')
            os.remove(fp)
            # status update
            self.sta.status_msg('Angular resolution mismatch in previous alignment. Redo process')
            self.sta.error = True
        # check if micro image size in valid range
        elif self._M >= self._Mn > 0:
            self.cfg.params[self.cfg.ptc_leng] = self._Mn
        # check if micro image size not set
        elif self._M == 0:
            self._M = self._Mn
            self.cfg.params[self.cfg.ptc_leng] = self._Mn

        self._C = self._M // 2

        try:
            self._DIMS = self._lfp_img.shape if len(self._lfp_img.shape) == 3 else self._lfp_img.shape + (1,)
        except (TypeError, AttributeError):
            pass
        except IndexError:
            self.sta.status_msg('Incompatible image dimensions: Please either use KxLx3 or KxLx1 array dimensions')
            self.sta.error = True

    def proc_lens_iter(self, fun, **kwargs):
        """ process light-field based on provided function handle and argument data """

        # status message handling
        msg = kwargs['msg'] if 'msg' in kwargs else 'Light-field alignment process'
        usr_prnt = kwargs['prnt'] if 'prnt' in kwargs else True
        if usr_prnt:
            self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_prnt])

        args = [kwargs[key] for key in kwargs.keys() if key not in ('cfg', 'sta', 'msg', 'prnt')]

        try:
            # iterate over each MIC
            for ly in range(self._LENS_Y_MAX):
                for lx in range(self._LENS_X_MAX):

                    # perform provided function
                    fun(ly, lx, *args)

                # print progress status
                self.sta.progress((ly + 1) / self._LENS_Y_MAX * 100, self.cfg.params[self.cfg.opt_prnt])

                # check interrupt status
                if self.sta.interrupt:
                    return False

        except Exception as e:
            raise e

        return True

    def get_coords_by_idx(self, ly: int, lx: int) -> (float, float):
        """ yields micro image center in 2-D image coordinates """

        # filter mic by provided indices
        mic = self._CENTROIDS[(self._CENTROIDS[:, 2] == ly) & (self._CENTROIDS[:, 3] == lx), [0, 1]]

        return mic[0], mic[1]

    def safe_pitch_eval(self, mean_pitch: float, user_pitch: int) -> int:
        """ provide odd pitch size that is safe to use """

        # ensure patch size and mean patch size are odd
        mean_pitch += np.mod(mean_pitch, 2) - 1
        user_pitch += np.mod(user_pitch, 2) - 1
        safe_pitch = 3

        # comparison of patch size and mean size
        if safe_pitch <= user_pitch <= mean_pitch+2:  # allow user pitch to be slightly bigger than estimate
            safe_pitch = user_pitch
        elif user_pitch > mean_pitch:
            safe_pitch = mean_pitch
            msg_str = 'Patch size ({0} px) is larger than micro image size and reduced to {1} pixels.'
            self.sta.status_msg(msg_str.format(user_pitch, mean_pitch), self.cfg.params[self.cfg.opt_prnt])
        elif user_pitch < safe_pitch < mean_pitch:
            safe_pitch = mean_pitch
            msg_str = 'Patch size ({0} px) is too small and increased to {1} pixels.'
            self.sta.status_msg(msg_str.format(user_pitch, mean_pitch), self.cfg.params[self.cfg.opt_prnt])
        elif user_pitch < safe_pitch and mean_pitch < safe_pitch:
            self.sta.status_msg('Micro image dimensions are too small for light field computation.', True)
            self.sta.interrupt = True

        return int(safe_pitch)

    @staticmethod
    def centroid_avg_pitch(centroids: (list, np.ndarray)) -> int:
        """ estimate micro image pitch only from centroids """

        # convert to numpy array
        centroids = np.asarray(centroids)

        # estimate maximum patch size
        central_row_idx = int(max(centroids[:, 3])/2)
        mean_pitch = int(np.ceil(np.mean(np.diff(centroids[centroids[:, 3] == central_row_idx, 0]))))

        # ensure mean patch size is odd
        mean_pitch += np.mod(mean_pitch, 2)-1

        return int(mean_pitch)

    def centroid_align_pitch(self) -> int:
        """ obtain micro image pitch of aligned light-field from number of centroids """

        # estimate patch size
        lens_max_y = self._CENTROIDS[:][2].max() + 1     # +1 to account for index 0
        lens_max_x = self._CENTROIDS[:][3].max() + 1     # +1 to account for index 0
        pitch_estimate_y = self._lfp_img.shape[0]/lens_max_y
        pitch_estimate_x = self._lfp_img.shape[1]/lens_max_x

        if pitch_estimate_y-int(pitch_estimate_y) != 0 or pitch_estimate_x-int(pitch_estimate_x) != 0:
            msg = 'Micro image patch size error. Remove output folder or select re-calibration in settings.'
            self.sta.status_msg(msg=msg, opt=self.cfg.params[self.cfg.opt_prnt])
            self.sta.error = True

        return int(pitch_estimate_y)

    def lfp_align_pitch(self) -> int:
        """ estimate pitch size from aligned light-field (when centroids not available) """

        # initialize output variable (return zero if light field not present)
        res = 0
        if self._lfp_img_align is None:
            return res

        # use vertical dimension only (as horizontal may differ from hexagonal stretching)
        if hasattr(self, '_LENS_Y_MAX'):
            res = int(self._lfp_img_align.shape[0] / self._LENS_Y_MAX)
        else:
            # iterate through potential (uneven) micro image size candidates
            for d in np.arange(3, 51, 2):
                # take pitch where remainder of ratio between aligned image dimensions and candidate size is zero
                if (self._lfp_img_align.shape[0] / d) % 1 == 0 and (self._lfp_img_align.shape[1] / d) % 1 == 0:
                    res = int(d)
                    break

        return res

    @staticmethod
    def get_hex_direction(centroids: np.ndarray) -> bool:
        """ check if lower neighbor of upper left micro image center is shifted to left or right in hex grid

        :param centroids: phased array data
        :return: True if shifted to right
        """

        # get upper left MIC
        first_mic = centroids[(centroids[:, 2] == 0) & (centroids[:, 3] == 0), [0, 1]]

        # retrieve horizontal micro image shift (to determine search range borders)
        central_row_idx = int(centroids[:, 3].max()/2)
        mean_pitch = np.mean(np.diff(centroids[centroids[:, 3] == central_row_idx, 0]))

        # try to find MIC in lower left range (considering hexagonal order)
        found_mic = centroids[(centroids[:, 0] > first_mic[0]+mean_pitch/2) &
                              (centroids[:, 0] < first_mic[0]+3*mean_pitch/2) &
                              (centroids[:, 1] < first_mic[1]) &
                              (centroids[:, 1] > first_mic[1]-3*mean_pitch/4)].ravel()

        # true if MIC of next row lies on the right (false otherwise)
        hex_odd = True if found_mic.size == 0 else False

        return hex_odd

    @property
    def lfp_img(self):
        return self._lfp_img.copy() if self._lfp_img is not None else False

    @property
    def lfp_img_align(self):
        return self._lfp_img_align.copy() if self._lfp_img_align is not None else None
