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


class LfpMicroLenses(object):

    def __init__(self, *args, **kwargs):

        # variables
        self._lfp_img = kwargs['lfp_img'] if 'lfp_img' in kwargs else None
        self._wht_img = kwargs['wht_img'] if 'wht_img' in kwargs else None
        self._lfp_img_align = kwargs['lfp_img_align'] if 'lfp_img_align' in kwargs else None
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else misc.PlenopticamStatus()

        # convert to float
        self._lfp_img = self._lfp_img.astype('float64') if self._lfp_img is not None else None
        self._wht_img = self._wht_img.astype('float64') if self._wht_img is not None else None

        if self.cfg.calibs:
            # micro lens array variables
            self._CENTROIDS = np.asarray(self.cfg.calibs[self.cfg.mic_list])
            self._LENS_Y_MAX = int(max(self._CENTROIDS[:, 2])+1)    # +1 to account for index 0
            self._LENS_X_MAX = int(max(self._CENTROIDS[:, 3])+1)    # +1 to account for index 0

            # micro image size evaluation
            self._M = self.pitch_max(self.cfg.calibs[self.cfg.mic_list])
            self._M = self.pitch_eval(self._M, self.cfg.params[self.cfg.ptc_leng], self.sta)
            self._C = self._M//2

        try:
            self._DIMS = self._lfp_img.shape if len(self._lfp_img.shape) == 3 else self._lfp_img.shape + (1,)
        except (TypeError, AttributeError):
            pass
        except IndexError:
            self.sta.status_msg('Incompatible image dimensions: Please either use KxLx3 or KxLx1 array dimensions')
            self.sta.error = True

    @property
    def lfp_img(self):
        return self._lfp_img.copy() if self._lfp_img is not None else False

    def proc_lens_iter(self, fun, **kwargs):
        ''' process light-field based on provided function handle and argument data '''

        # status message handling
        msg = kwargs['msg'] if 'msg' in kwargs else 'Light-field alignment process'
        self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_prnt])

        args = [kwargs[key] for key in kwargs.keys() if key not in ('cfg', 'sta', 'msg')]

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

    def get_coords_by_idx(self, ly, lx):

        # filter mic by provided indices
        mic = self._CENTROIDS[(self._CENTROIDS[:, 2] == ly) & (self._CENTROIDS[:, 3] == lx), [0, 1]]

        return mic

    @staticmethod
    def pitch_eval(mean_pitch, patch_size, sta=None):
        ''' provide odd patch size that is safe to use '''

        sta = sta if sta is not None else misc.PlenopticamStatus()

        # ensure patch size and mean patch size are odd
        patch_size += np.mod(patch_size, 2)-1
        mean_pitch += np.mod(mean_pitch, 2)-1
        patch_safe = 3

        # comparison of patch size and mean size
        msg_str = None
        if 3 < patch_size <= mean_pitch+2:
            patch_safe = patch_size
        elif patch_size > mean_pitch:
            patch_safe = mean_pitch
            msg_str = 'Patch size ({0} px) is larger than micro image size and reduced to {1} pixels.'
        elif patch_size < 3 < mean_pitch:
            patch_safe = mean_pitch
            msg_str = 'Patch size ({0} px) is too small and increased to {1} pixels.'
        elif patch_size < 3 and mean_pitch < 3:
            sta.interrupt = True
            raise Exception('Micro image dimensions are too small for light field computation.')

        if msg_str:
            # status update
            sta.status_msg(msg_str.format(patch_size, mean_pitch), True)

        return patch_safe

    @staticmethod
    def pitch_max(centroids):

        # convert to numpy array
        centroids = np.asarray(centroids)

        # estimate maximum patch size
        central_row_idx = int(max(centroids[:, 3])/2)
        mean_pitch = int(np.ceil(np.mean(np.diff(centroids[centroids[:, 3] == central_row_idx, 0]))))

        # ensure mean patch size is odd
        mean_pitch += np.mod(mean_pitch, 2)-1

        return mean_pitch

    def pitch_analyse(self, shape):

        # estimate patch size
        lens_max_x = self._CENTROIDS[:, 2].max() + 1     # +1 to account for index 0
        pitch_estimate = shape[0]/lens_max_x

        if pitch_estimate-int(pitch_estimate) != 0:
            msg = 'Micro image patch size error. Remove output folder or select re-calibration in settings.'
            self.sta.status_msg(msg=msg, opt=self.cfg.params[self.cfg.opt_prnt])
            self.sta.error = True
        else:
            pitch_estimate = int(pitch_estimate)

        return pitch_estimate

    def lfp_align_pitch_guess(self):

        if self._lfp_img_align is None:
            return False

        # iterate through potential (uneven) micro image size candidates
        for d in np.arange(3, 51, 2):
            # take pitch where remainder of ratio between aligned image dimensions and candidate size is zero
            if (self._lfp_img_align.shape[0] / d) % 1 == 0 and (self._lfp_img_align.shape[1] / d) % 1 == 0:
                self._M = int(d)
                break

        return self._M
