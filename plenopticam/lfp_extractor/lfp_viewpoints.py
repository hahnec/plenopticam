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
from plenopticam.misc.circle_drawer import bresenham_circle

import numpy as np


class LfpViewpoints(object):

    def __init__(self, *args, **kwargs):

        self._vp_img_arr = kwargs['vp_img_arr'] if 'vp_img_arr' in kwargs else None
        self._vp_img_arr = self.vp_img_arr.astype('float64') if self.vp_img_arr is not None else None
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()
        self._M = self.cfg.params[self.cfg.ptc_leng]
        self._C = self._M // 2

        try:
            self._DIMS = self._vp_img_arr.shape if len(self._vp_img_arr.shape) == 3 else self._vp_img_arr.shape + (1,)
        except (TypeError, AttributeError):
            pass
        except IndexError:
            self.sta.status_msg('Incompatible image dimensions: Please either use KxLx3 or KxLx1 array dimensions')
            self.sta.error = True

    @property
    def vp_img_arr(self):
        return self._vp_img_arr

    @vp_img_arr.setter
    def vp_img_arr(self, vp_img_arr):
        self._vp_img_arr = vp_img_arr

    @property
    def central_view(self):
        return self._vp_img_arr[self._C, self._C, ...].copy() if self._vp_img_arr is not None else None

    @staticmethod
    def remove_proc_keys(kwargs, data_type=None):

        data_type = dict if not data_type else data_type
        keys_to_remove = ('cfg', 'sta', 'msg', 'iter_num', 'iter_tot')

        if data_type == dict:
            output = dict((key, kwargs[key]) for key in kwargs if key not in keys_to_remove)
        elif data_type == list:
            output = list(kwargs[key] for key in kwargs.keys() if key not in keys_to_remove)
        else:
            output = None

        return output

    def proc_vp_arr(self, fun, **kwargs):
        """ process viewpoint images based on provided function handle and argument data """

        # percentage indices for tasks having sub-processes
        iter_num = kwargs['iter_num'] if 'iter_num' in kwargs else 0
        iter_tot = kwargs['iter_tot'] if 'iter_tot' in kwargs else 1

        # status message handling
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])
        if iter_num == 0:
            msg = kwargs['msg'] if 'msg' in kwargs else 'Viewpoint process'
            self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_prnt])

        args = self.remove_proc_keys(kwargs, data_type=list)

        # light-field shape handling
        if len(self.vp_img_arr.shape) != 5:
            raise NotImplementedError
        new_shape = fun(self._vp_img_arr[0, 0, ...].copy(), *args).shape
        new_array = np.zeros(self._vp_img_arr.shape[:2] + new_shape)

        for j in range(self._vp_img_arr.shape[0]):
            for i in range(self._vp_img_arr.shape[1]):

                # check interrupt status
                if self.sta.interrupt:
                    return False

                res = fun(self._vp_img_arr[j, i, ...], *args)

                if res.shape == self._vp_img_arr.shape:
                    self._vp_img_arr[j, i, ...] = res
                else:
                    new_array[j, i, ...] = res

                # progress update
                percent = (j*self._vp_img_arr.shape[1]+i+1)/np.dot(*self._vp_img_arr.shape[:2])
                percent = percent / iter_tot + iter_num / iter_tot
                self.sta.progress(percent*100, self.cfg.params[self.cfg.opt_prnt])

        if new_array.sum() != 0:
            self._vp_img_arr = new_array

        return True

    @staticmethod
    def get_move_coords(arr_dims: (int, int) = (None, None), pattern: str = None, r: int = None) -> list:
        """ compute view coordinates that are used for loop iterations """

        # parameter initialization
        pattern = 'circle' if pattern is None else pattern
        r = r if r is not None else min(arr_dims)//2
        mask = [[0] * arr_dims[1] for _ in range(arr_dims[0])]

        if pattern == 'square':
            mask[0, :] = 1
            mask[:, 0] = 1
            mask[-1, :] = 1
            mask[:, -1] = 1
        if pattern == 'circle':
            mask = bresenham_circle(arr_dims, r=r)

        # extract coordinates from mask
        coords_table = [(y, x) for y in range(len(mask)) for x in range(len(mask)) if mask[y][x]]

        # sort coordinates in angular order
        coords_table.sort(key=lambda coords: np.arctan2(coords[0] - arr_dims[0]//2, coords[1] - arr_dims[1]//2))

        return coords_table

    def reorder_vp_arr(self, pattern=None, lf_radius=None):

        # parameter initialization
        pattern = 'circle' if pattern is None else pattern
        move_coords = self.get_move_coords(arr_dims=self.vp_img_arr.shape[:2], pattern=pattern, r=lf_radius)

        vp_img_set = []
        for coords in move_coords:
            vp_img_set.append(self.vp_img_arr[coords[0], coords[1], ...])

        return vp_img_set

    def proc_ax_propagate_1d(self, fun, idx=None, axis=None, **kwargs):
        """ apply provided function along axis direction """

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
        """ apply provided function along axes """

        # percentage indices for tasks having sub-processes
        iter_num = kwargs['iter_num'] if 'iter_num' in kwargs else 0
        iter_tot = kwargs['iter_tot'] if 'iter_tot' in kwargs else 1

        # status message handling
        if iter_num == 0:
            msg = kwargs['msg'] if 'msg' in kwargs else 'Viewpoint process'
            self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_prnt])

        kwargs = self.remove_proc_keys(kwargs, data_type=dict)

        self.proc_ax_propagate_1d(fun, idx=0, axis=0, **kwargs)

        for j in range(-self._C, self._C + 1):

            # apply histogram matching along entire column
            self.proc_ax_propagate_1d(fun, idx=j, axis=1, **kwargs)

            # progress update
            percent = (j + self._C + 1) / self._vp_img_arr.shape[0]
            percent = percent / iter_tot + iter_num / iter_tot
            self.sta.progress(percent*100, self.cfg.params[self.cfg.opt_prnt])

            # check interrupt status
            if self.sta.interrupt:
                return False

        return True

    @property
    def views_stacked_img(self):
        """ concatenation of all sub-aperture images for single image representation """
        return np.moveaxis(np.concatenate(np.moveaxis(np.concatenate(np.moveaxis(self.vp_img_arr, 1, 2)), 0, 2)), 0, 1)

    def circular_view_aperture(self, offset=None, ellipse=None):

        # initialize variables
        offset = offset if offset is not None else 0
        ratio = self.vp_img_arr.shape[3]/self.vp_img_arr.shape[2] if ellipse else 1
        r = self._M // 2
        mask = np.zeros([2*r+1, 2*r+1])

        # determine mask for affected views
        for x in range(-r, r + 1):
            for y in range(-r, r + 1):
                if int(np.round(np.sqrt(x ** 2 + y ** 2 * ratio))) > r + offset:
                    mask[r + y][r + x] = 1

        # extract coordinates from mask
        coords_table = [(y, x) for y in range(len(mask)) for x in range(len(mask)) if mask[y][x]]

        # zero-out selected views
        for coords in coords_table:
            self.vp_img_arr[coords[0], coords[1], ...] = np.zeros(self.vp_img_arr.shape[2:])

        return True
