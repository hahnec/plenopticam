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

from plenopticam.lfp_extractor.lfp_viewpoints import LfpViewpoints
from plenopticam.lfp_aligner.lfp_microlenses import LfpMicroLenses

import numpy as np

class LfpCropper(LfpViewpoints):

    def __init__(self, lfp_img_align=None, *args, **kwargs):
        super(LfpCropper, self).__init__(*args, **kwargs)

        self._lfp_img_align = lfp_img_align if lfp_img_align is not None else None

        self.var_init()

    def var_init(self):

        # get maximum (M) and desired (Mn) micro image pitches
        self._M = self.pitch_max(self.cfg.calibs[self.cfg.mic_list])
        self._Mn = self.pitch_eval(self._M, self.cfg.params[self.cfg.ptc_leng], self.sta)
        self.cfg.params[self.cfg.ptc_leng] = self._Mn

        # get viewpoint dimensions
        self._lens_y_max = int(self._lfp_img_align.shape[0]/self._M)
        self._lens_x_max = int(self._lfp_img_align.shape[1]/self._M)

    def main(self):

        # reduce light field in angular domain (depending on settings)
        if self._Mn < self._M:
            self.reduce_angular_domain()

    def reduce_angular_domain(self):

        # print status
        self.sta.status_msg('Render angular domain', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        Mn = self._Mn
        M = self._M
        k = int((self._M - self._Mn)/2)

        m, n, p = self._lfp_img_align.shape if len(self._lfp_img_align.shape) == 3 else (self._lfp_img_align.shape[0], self._lfp_img_align.shape[1], 1)
        new_lfp_img = np.zeros([int(self._Mn*self._lens_y_max), int(self._Mn*self._lens_x_max), p], dtype=self._lfp_img_align.dtype)

        # iterate through micro image coordinates
        for j in range(self._lens_y_max):
            for i in range(self._lens_x_max):

                # crop micro image patches
                new_lfp_img[j*Mn:j*Mn+Mn, i*Mn:i*Mn+Mn] = self._lfp_img_align[k+j*M:j*M+M-k, k+i*M:i*M+M-k]

                # print status
                percentage = ((j*self._lens_x_max+i+1)/(self._lens_y_max*self._lens_x_max)*100)
                self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

                # check interrupt status
                if self.sta.interrupt:
                    return False

        self._lfp_img_align = new_lfp_img

        return True

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
        if patch_size <= mean_pitch+2 and patch_size > 3:
            patch_safe = patch_size
        elif patch_size > mean_pitch:
            patch_safe = mean_pitch
            msg_str = 'Patch size ({0} px) is larger than micro image size and reduced to {1} pixels.'
        elif patch_size < 3 and mean_pitch > 3:
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

    @property
    def lfp_img_align(self):
        return self._lfp_img_align.copy()