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
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else misc.PlenopticamStatus()
        self._hex_odd = None
        self._lfp_img = kwargs['lfp_img'] if 'lfp_img' in kwargs else None
        self._wht_img = kwargs['wht_img'] if 'wht_img' in kwargs else None
        self._lfp_img_align = kwargs['lfp_img_align'] if 'lfp_img_align' in kwargs else None
        self._flip = kwargs['flip'] if 'flip' in kwargs else False

        # convert to float
        self._lfp_img = self._lfp_img.astype('float64') if self._lfp_img is not None else None
        self._wht_img = self._wht_img.astype('float64') if self._wht_img is not None else None

        if self.cfg.calibs:
            # micro lens array variables
            self._CENTROIDS = np.asarray(self.cfg.calibs[self.cfg.mic_list])
            self._LENS_Y_MAX = int(max(self._CENTROIDS[:, 2])+1)    # +1 to account for index 0
            self._LENS_X_MAX = int(max(self._CENTROIDS[:, 3])+1)    # +1 to account for index 0
            self._PAT_TYPE = self.cfg.calibs[self.cfg.pat_type] if self.cfg.pat_type in self.cfg.calibs else 'rec'
            self._hex_odd = self.get_hex_direction(self._CENTROIDS)

        # initialize micro image size and respective centers
        self._size_pitch = 0
        self._cent_pitch = 0

        # get pitch from aligned light field
        self._limg_pitch = self.lfp_align_pitch()

        # get mean pitch from centroids
        self._cavg_pitch = self.centroid_avg_pitch()

        # evaluate pitch sizes from aligned image, centroid list and user definition to obtain safe pitch
        self._size_pitch = self.safe_pitch_eval(
                                                cavg_pitch=min(self._cavg_pitch),
                                                limg_pitch=min(self._limg_pitch),
                                                user_pitch=int(self.cfg.params[self.cfg.ptc_leng]),
                                                )
        # micro image centers
        self._cent_pitch = self._size_pitch // 2

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
            # iterate through each micro lens centroid
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

    def safe_pitch_eval(self, cavg_pitch: float, limg_pitch: float, user_pitch: int) -> int:
        """ evaluate pitch size that is safe to use """

        safe_pitch = 3

        # comparison of user selected pitch and average centroid size
        if safe_pitch <= user_pitch <= cavg_pitch+2:  # allow user pitch to be slightly bigger than estimate
            safe_pitch = user_pitch
        elif user_pitch > cavg_pitch:
            safe_pitch = cavg_pitch
            msg_str = 'User size ({0} px) is larger than micro image size and reduced to {1} pixels.'
            self.sta.status_msg(msg_str.format(user_pitch, cavg_pitch), self.cfg.params[self.cfg.opt_prnt])
        elif user_pitch < safe_pitch < cavg_pitch:
            safe_pitch = cavg_pitch
            msg_str = 'User size ({0} px) is too small and increased to {1} pixels.'
            self.sta.status_msg(msg_str.format(user_pitch, cavg_pitch), self.cfg.params[self.cfg.opt_prnt])
        elif user_pitch < safe_pitch and cavg_pitch < safe_pitch:
            self.sta.status_msg('Micro image dimensions are too small for light field computation.', True)
            self.sta.interrupt = True

        # if chosen safe micro image size is larger than in the aligned image
        if 0 < limg_pitch < safe_pitch:
            # remove existing pickle file
            fp = os.path.join(self.cfg.exp_path, 'lfp_img_align.pkl')
            os.remove(fp)
            # status update
            self.sta.status_msg('Angular resolution mismatch in previous alignment. Redo process')
            self.sta.interrupt = True
        # check if micro image size in valid range
        elif limg_pitch >= safe_pitch > 0:
            self.cfg.params[self.cfg.ptc_leng] = safe_pitch
        # check if micro image size not set
        elif limg_pitch == 0:
            self._size_pitch = safe_pitch
            self.cfg.params[self.cfg.ptc_leng] = safe_pitch

        return int(safe_pitch)

    def centroid_avg_pitch(self) -> np.ndarray:
        """ estimate micro image pitch only from centroids """

        if not hasattr(self, '_CENTROIDS'):
            return np.zeros(2)

        # convert to numpy array
        centroids = np.asarray(self._CENTROIDS)

        # estimate maximum patch size
        central_row_idx = int(max(centroids[:, 2])/2)
        central_col_idx = int(max(centroids[:, 3])/2)
        mean_pitch_x = int(np.ceil(np.mean(np.diff(centroids[centroids[:, 2] == central_row_idx, 1]))))
        mean_pitch_y = int(np.ceil(np.mean(np.diff(centroids[centroids[:, 3] == central_col_idx, 0]))))

        return np.array([mean_pitch_y, mean_pitch_x])

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

    def lfp_align_pitch(self) -> np.ndarray:
        """ estimate pitch size from aligned light-field """

        # initialize output variable (return zero if aligned light field not present)
        self._limg_pitch = np.zeros(2, dtype='int')
        if self._lfp_img_align is None:
            return self._limg_pitch

        # obtain micro image size from both dimensions (horizontal accounts for hexagonal stretching)
        if hasattr(self, '_LENS_Y_MAX') and hasattr(self, '_LENS_X_MAX'):
            h = np.sqrt(3)/2 if self._PAT_TYPE == 'hex' else 1
            self._limg_pitch[0] = int(round(self._lfp_img_align.shape[0] / self._LENS_Y_MAX))
            self._limg_pitch[1] = int(round(self._lfp_img_align.shape[1] / self._LENS_X_MAX * h))
        else:
            for axis in [0, 1]:
                # take pitch where remainder of ratio between aligned image dimensions and candidate size is zero
                self._limg_pitch[axis] = self.remainder_ratio(num=self._lfp_img_align.shape[axis])

        return self._limg_pitch.astype('int')

    @staticmethod
    def remainder_ratio(num: int) -> int:
        # iterate through potential (odd or even) micro image size candidates
        for d in np.arange(3, 151, 1):
            if (num / d) % 1 == 0:
                return int(d)

        return 0

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
