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

import numpy as np


class ClsRefoSlices(object):

    def __init__(self, *args, **kwargs):

        self._rf_img_arr = kwargs['rf_img_arr'].astype('float64') if 'rf_img_arr' in kwargs else None
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()
        self._M = self.cfg.params[self.cfg.ptc_leng]
        self._C = self._M // 2

    @property
    def rf_img_arr(self):
        return self._rf_img_arr

    @rf_img_arr.setter
    def rf_img_arr(self, rf_img_arr):
        self._rf_img_arr = rf_img_arr

    def proc_refo_arr(self, fun, **kwargs):
        ''' process viewpoint images based on provided function handle and argument data '''

        # percentage indices for tasks having sub-processes
        iter_num = kwargs['iter_num'] if 'iter_num' in kwargs else 0
        iter_tot = kwargs['iter_tot'] if 'iter_tot' in kwargs else 1

        # status message handling
        if iter_num == 0:
            msg = kwargs['msg'] if 'msg' in kwargs else 'Refocusing process'
            self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_prnt])

        args = self.remove_proc_keys(kwargs, data_type=list)

        try:
            if len(self.rf_img_arr.shape) == 4:
                for j in range(self._rf_img_arr.shape[0]):
                    self._rf_img_arr[j, ...] = fun(self._rf_img_arr[j, ...], *args)

                    # progress update
                    percent = (j*self._rf_img_arr.shape[1]+1)/np.dot(*self._rf_img_arr.shape[:2])
                    percent = percent / iter_tot + iter_num / iter_tot
                    self.sta.progress(percent*100, self.cfg.params[self.cfg.opt_prnt])
        except:
            if len(self.rf_img_arr.shape) != 4:
                raise NotImplementedError
