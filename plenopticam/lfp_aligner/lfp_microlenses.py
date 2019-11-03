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
from plenopticam.misc import PlenopticamStatus

from plenopticam.lfp_extractor.lfp_cropper import LfpCropper

import numpy as np

class LfpLensIter(object):

    def __init__(self, *args, **kwargs):

        # input variables
        self._lfp_img = kwargs['lfp_img'] if 'lfp_img' in kwargs else None
        self._wht_img = kwargs['wht_img'] if 'wht_img' in kwargs else None
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()

        # add 3rd axis for 2D image
        self._lfp_img = self._lfp_img[..., np.newaxis] if len(self._lfp_img.shape) == 2 else self._lfp_img

        # convert to float
        self._lfp_img = self._lfp_img.astype('float64')
        self._wht_img = self._wht_img.astype('float64')

        self._CENTROIDS = np.asarray(self.cfg.calibs[self.cfg.mic_list])
        self._M = LfpCropper.pitch_max(self.cfg.calibs[self.cfg.mic_list])
        self._C = int((self._M-1)/2)
        self._LENS_Y_MAX = int(max(self._CENTROIDS[:, 2]))
        self._LENS_X_MAX = int(max(self._CENTROIDS[:, 3]))
        self._DIMS = self._lfp_img.shape if len(self._lfp_img.shape) == 3 else None

    @property
    def lfp_img(self):
        return self._lfp_img.copy() if self._lfp_img is not None else False

    def proc_lfp_img(self, fun, **kwargs):
        ''' process light-field based on provided function handle and argument data '''

        msg = kwargs['msg'] if 'msg' in kwargs else 'Light-field alignment process'

        self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_dbug])

        args = [kwargs[key] for key in kwargs.keys() if key not in ('cfg', 'sta', 'msg')]

        try:
            # iterate over each MIC
            for ly in range(self._LENS_Y_MAX):
                for lx in range(self._LENS_X_MAX):

                    # find MIC by indices
                    mic = self._get_coords_by_idx(ly=ly, lx=lx)

                    # perform provided function
                    fun(mic, *args)

                # print progress status
                self.sta.progress((ly + 1) / self._LENS_Y_MAX * 100, self.cfg.params[self.cfg.opt_prnt])

                # check interrupt status
                if self.sta.interrupt:
                    return False

        except Exception as e:
            raise e

        return True

    def _get_coords_by_idx(self, ly, lx):

        # filter mic by provided indices
        mic = self._CENTROIDS[(self._CENTROIDS[:, 2] == ly) & (self._CENTROIDS[:, 3] == lx), [0, 1]]

        return mic
