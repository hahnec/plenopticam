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

class LfpViewpoints(object):

    def __init__(self, *args, **kwargs):

        self._vp_img_arr = kwargs['vp_img_arr'].astype('float64') if 'vp_img_arr' in kwargs else None
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()
        self._M = self.cfg.params[self.cfg.ptc_leng]
        self._C = self._M // 2

    @property
    def vp_img_arr(self):
        return self._vp_img_arr

    @vp_img_arr.setter
    def vp_img_arr(self, vp_img_arr):
        self._vp_img_arr = vp_img_arr

    @property
    def central_view(self):
        return self.vp_img_arr[self._C, self._C, ...].copy() if self._vp_img_arr is not None else None

    def proc_vp_arr(self, fun, **kwargs):
        ''' process viewpoint images based on provided function handle and argument data '''

        # status message handling
        msg = kwargs['msg'] if 'msg' in kwargs else 'Viewpoint process'
        self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_prnt])

        args = [kwargs[key] for key in kwargs.keys() if key not in ('cfg', 'sta', 'msg')]

        try:
            for j in range(self._vp_img_arr.shape[0]):
                for i in range(self._vp_img_arr.shape[1]):

                    self._vp_img_arr[j, i, :, :, :] = fun(self._vp_img_arr[j, i, :, :, :], *args)

                    # progress update
                    percent = (j*self._vp_img_arr.shape[1]+i+1)/np.dot(*self._vp_img_arr.shape[:2])*100
                    self.sta.progress(percent, self.cfg.params[self.cfg.opt_dbug])

                # check interrupt status
                if self.sta.interrupt:
                    return False

        except:
            if len(self.vp_img_arr.shape) != 5:
                raise NotImplementedError

        return True

    @staticmethod
    def get_move_coords(pattern, arr_dims):

        # parameter initialization
        pattern = 'circle' if pattern is None else pattern
        r = int(min(arr_dims) / 2)
        mask = [[0] * arr_dims[1] for _ in range(arr_dims[0])]

        if pattern == 'square':
            mask[0, :] = 1
            mask[:, 0] = 1
            mask[-1, :] = 1
            mask[:, -1] = 1
        if pattern == 'circle':
            for x in range(-r, r + 1):
                for y in range(-r, r + 1):
                    if int(np.sqrt(x ** 2 + y ** 2)) == r:
                        mask[y + r][x + r] = 1

        # extract coordinates from mask
        coords_table = [(y, x) for y in range(len(mask)) for x in range(len(mask)) if mask[y][x]]

        # sort coordinates in angular order
        coords_table.sort(key=lambda coords: np.arctan2(coords[0] - r, coords[1] - r))

        return coords_table

    def reorder_vp_arr(self, pattern=None):

        # parameter initialization
        pattern = 'circle' if pattern is None else pattern
        arr_dims = self.vp_img_arr.shape[:2]
        move_coords = self.get_move_coords(pattern, arr_dims)

        vp_img_set = []
        for coords in move_coords:
            vp_img_set.append(self.vp_img_arr[coords[0], coords[1], ...])

        return vp_img_set

    def proc_ax_propagate_1d(self, fun, idx=None, axis=None, **kwargs):
        ''' apply provided function along axis direction '''

        # status message handling
        if 'msg' in kwargs:
            self.sta.status_msg(kwargs['msg'], self.cfg.params[self.cfg.opt_prnt])

        axis = 0 if axis is None else axis
        j = 0 if idx is None else idx
        m, n = (0, 1) if axis == 0 else (1, 0)
        p, q = (1, -1) if axis == 0 else (-1, 1)

        for i in range(self._C):

            # swap axes indices
            j, i = (i, j) if axis == 1 else (j, i)

            #print("j-src:"+str(self._c+j+m)+", i-src:"+str(self._c+i+n)+", j-ref:"+str(self._c+j)+", i-ref:"+str(self._c+i))
            #print("j-src:"+str(self._c+(j+m)*p)+", i-src:"+str(self._c+(i+n)*q)+", j-ref:"+str(self._c+j*p)+", i-ref:"+str(self._c+i*q))

            ref_pos = self.vp_img_arr[self._C + j, self._C + i, ...]
            ref_neg = self.vp_img_arr[self._C + j * p, self._C + i * q, ...]

            self._vp_img_arr[self._C + j + m, self._C + i + n, ...] = \
                fun(self.vp_img_arr[self._C + j + m, self._C + i + n, ...], ref_pos, **kwargs)
            self._vp_img_arr[self._C + (j + m) * p, self._C + (i + n) * q, ...] = \
                fun(self.vp_img_arr[self._C + (j + m) * p, self._C + (i + n) * q, ...], ref_neg, **kwargs)

            # swap axes indices
            j, i = (i, j) if axis == 1 else (j, i)

            # check interrupt status
            if self.sta.interrupt:
                return False

        return True

    def proc_ax_propagate_2d(self, fun, **kwargs):
        ''' apply provided function along axes '''

        # status message handling
        msg = kwargs['msg'] if 'msg' in kwargs else 'Viewpoint process'
        self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_prnt])

        kwargs = dict((key, kwargs[key]) for key in kwargs if key not in ('cfg', 'sta', 'msg'))

        self.proc_ax_propagate_1d(fun, idx=0, axis=0, **kwargs)

        for j in range(-self._C, self._C + 1):

            # apply histogram matching along entire column
            self.proc_ax_propagate_1d(fun, idx=j, axis=1, **kwargs)

            # progress update
            percent = (j + self._C + 1) / self._vp_img_arr.shape[0] * 100
            self.sta.progress(percent, self.cfg.params[self.cfg.opt_prnt])

            # check interrupt status
            if self.sta.interrupt:
                return False

        return True

    @property
    def views_stacked_img(self):
        ''' concatenation of all sub-aperture images for single image representation '''
        return np.moveaxis(np.concatenate(np.moveaxis(np.concatenate(np.moveaxis(self.vp_img_arr, 1, 2)), 0, 2)), 0, 1)
