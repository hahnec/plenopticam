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

from plenopticam.lfp_extractor import LfpViewpoints
from plenopticam.misc import PlenopticamError


class LfpRearranger(LfpViewpoints):

    def __init__(self, lfp_img_align=None, *args, **kwargs):
        super(LfpRearranger, self).__init__(*args, **kwargs)

        self._lfp_img_align = lfp_img_align if lfp_img_align is not None else None
        self._dtype = self._lfp_img_align.dtype if self._lfp_img_align is not None else self._vp_img_arr.dtype

    def _init_vp_img_arr(self):
        """ initialize viewpoint output image array """

        if len(self._lfp_img_align.shape) == 3:
            m, n, p = self._lfp_img_align.shape
        elif len(self._lfp_img_align.shape) == 2:
            m, n, p = self._lfp_img_align.shape[:2] + (1,)
        else:
            raise PlenopticamError('Dimensions %s of provided light-field not supported', self._lfp_img_align.shape)

        self._vp_img_arr = np.zeros([int(self._M), int(self._M), int(m/self._M), int(n/self._M), p], dtype=self._dtype)

    def _init_lfp_img_align(self):
        """ initialize micro image output image array """

        if len(self._vp_img_arr.shape) == 5:
            m, n, p = self._vp_img_arr.shape[2:]
        elif len(self._vp_img_arr.shape) == 4:
            m, n, p = self._vp_img_arr.shape[2:] + (1,)
        else:
            raise PlenopticamError('Dimensions %s of provided light-field not supported', self._vp_img_arr.shape)

        m *= self._vp_img_arr.shape[0]
        n *= self._vp_img_arr.shape[1]

        # create empty array
        self._lfp_img_align = np.zeros([m, n, p], dtype=self._dtype)

        # update angular resolution parameter
        self._M = self._vp_img_arr.shape[0] if self._vp_img_arr.shape[0] == self._vp_img_arr.shape[1] else float('inf')

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # rearrange light-field to viewpoint representation
        self.compose_viewpoints()

    def compose_viewpoints(self):
        """
        Conversion from aligned micro image array to viewpoint array representation. The fundamentals behind the
        4-D light-field transfer were derived by Levoy and Hanrahans in their paper 'Light Field Rendering' in Fig. 6.
        """

        # print status
        self.sta.status_msg('Viewpoint composition', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # initialize basic light-field parameters
        self._init_vp_img_arr()

        # rearrange light field to multi-view image representation
        for j in range(self._M):
            for i in range(self._M):

                # check interrupt status
                if self.sta.interrupt:
                    return False

                # extract viewpoint by pixel rearrangement
                self._vp_img_arr[j, i, ...] = self._lfp_img_align[j::self._M, i::self._M, :]

                # print status
                percentage = (j*self._M+i+1)/self._M**2
                self.sta.progress(percentage*100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def decompose_viewpoints(self):
        """
        Conversion from viewpoint image array to aligned micro image array representation. The fundamentals behind the
        4-D light-field transfer were derived by Levoy and Hanrahans in their paper 'Light Field Rendering' in Fig. 6.
        """

        # print status
        self.sta.status_msg('Viewpoint decomposition', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # initialize basic light-field parameters
        self._init_lfp_img_align()

        # rearrange light field to multi-view image representation
        for j in range(self._M):
            for i in range(self._M):

                # check interrupt status
                if self.sta.interrupt:
                    return False

                # extract viewpoint by pixel rearrangement
                self._lfp_img_align[j::self._M, i::self._M, :] = self._vp_img_arr[j, i, :, :, :]

                # print status
                percentage = (j*self._M+i+1)/self._M**2
                self.sta.progress(percentage*100, self.cfg.params[self.cfg.opt_prnt])

        return True
