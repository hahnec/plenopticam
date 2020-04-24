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
from plenopticam import misc
from plenopticam.cfg import constants as c

# external libs
import numpy as np
import os


class LfpScheimpflug(object):

    def __init__(self, refo_stack=None, lfp_img=None, cfg=None, sta=None):

        self.refo_stack = refo_stack
        self.lfp_img = lfp_img
        self.cfg = cfg
        self.sta = sta

        self.fp = os.path.join(os.path.splitext(self.cfg.params[self.cfg.lfp_path])[0], 'scheimpflug')

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # print status
        self.sta.status_msg('Scheimpflug extraction \n', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # create output folder
        misc.mkdir_p(self.fp)

        # iterate through directions
        for direction in list(c.PFLU_VALS):
            self.cfg.params[self.cfg.opt_pflu] = direction
            self.sta.status_msg(direction+':')

            if self.refo_stack is not None:
                self.scheimpflug_from_stack()
            elif self.lfp_img is not None:
                self.scheimpflug_from_scratch()

        return True

    def scheimpflug_from_stack(self):

        a_start, a_stop = (0, len(self.refo_stack))

        if len(self.refo_stack[0].shape) == 3:
            m, n, p = self.refo_stack[0].shape
        else:
            m, n, p = (self.refo_stack[0].shape[0], self.refo_stack[0].shape[1], 1)

        scheimpflug_img = np.zeros([m, n, p])

        # map generation
        a_x = np.linspace(0, a_stop-a_start, n+2, dtype='int')[1:-1]      # flooring via integer type while excluding
        a_y = np.linspace(0, a_stop-a_start, m+2, dtype='int')[1:-1]
        a_map_x = np.outer(np.ones(m, dtype='int'), a_x)
        a_map_y = np.outer(a_y, np.ones(n, dtype='int'))

        # vertical orientation (default)
        a_map = a_map_y
        # horizontal orientation
        if self.cfg.params[self.cfg.opt_pflu] == c.PFLU_VALS[1]:
            a_map = a_map_x
        # diagonal orientation
        elif self.cfg.params[self.cfg.opt_pflu] == (c.PFLU_VALS[2] or c.PFLU_VALS[3]):
            # swap refocusing directions if option set
            if self.cfg.params[self.cfg.opt_pflu] == c.PFLU_VALS[3]:
                a_map_x, a_map_y = a_map_x[::-1], a_map_y[::-1]
            a_map = np.mean(np.stack([a_map_x, a_map_y]), dtype='int', axis=0)

        for y in range(m):
            for x in range(n):
                scheimpflug_img[y, x] = self.refo_stack[a_map[y, x]][y, x]

                # check interrupt status
                if self.sta.interrupt:
                    return False

                # print status
                percentage = (((y*n+x+1)/(m*n))*100)
                self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

        # write image file to hard drive
        a_ran = self.cfg.params[self.cfg.ran_refo]
        fn = 'scheimpflug_' + str(a_ran[0]) + '_' + str(a_ran[-1]) + '_' + self.cfg.params[self.cfg.opt_pflu] + '.png'
        misc.save_img_file(misc.Normalizer(scheimpflug_img).uint16_norm(), os.path.join(self.fp, fn))

        return True

    def scheimpflug_from_scratch(self):

        patch_len = self.cfg.params[self.cfg.ptc_leng]
        a_start, a_stop = self.cfg.params[self.cfg.ran_refo]

        img = self.lfp_img.astype('float') / patch_len
        m, n, P = self.lfp_img.shape
        overlap = int(abs(a_stop) * (patch_len - 1))
        #tilt_vec_y = np.linspace(a_start, planes, m).astype('uint')
        a_x = np.linspace(a_start, a_stop, n + overlap).astype('int') # flooring values instead of rounding => 1st round, then int()
        a_y = np.zeros(m).astype('int')#np.linspace(a_start, planes, m).astype('uint')
        a_xy = np.ones([m, n + overlap]).astype('int') * a_x

        # initialize matrices for intermediate and plane results
        hor_refo = np.zeros([m, n + overlap, P], dtype='float')
        ver_refo = np.zeros([m + overlap, n + overlap, P], dtype='float')
        fraction_vec = np.zeros([patch_len, P], dtype='float')

        # horizontal scheimpflug shift and integration
        for y in range(m):
            for x in range(n):

                # prevent from taking adjacent pixel being beyond image border
                if x + patch_len < n:
                    adj_idx = x + patch_len
                else:
                    adj_idx = x

                for p in range(P):
                    fraction_vec[:, p] = np.linspace(img[y, x, p], img[y, adj_idx, p], patch_len)

                # load refocus value at x,y
                a = a_xy[y, x]

                # consider negative shift
                negative_a = int((patch_len - 1) * abs(a)) if a < 0 else 0

                # centralize row
                row_shift = int((a_y.max() - a)*(patch_len - 1)/2)

                newX = int(x + np.mod(x, patch_len) * (a - 1) + negative_a) + row_shift
                hor_refo[y, newX:newX + patch_len, :] = hor_refo[y, newX:newX + patch_len, :] + fraction_vec

            # check interrupt status
            if self.sta.interrupt:
                return False

            # print progress status
            self.sta.progress((y+1)/m*50, self.cfg.params[self.cfg.opt_prnt])

        # vertical scheimpflug shift and integration
        new_n = n + int(abs(a_x.max()) * (patch_len - 1))
        for x in range(new_n):
            for y in range(m):

                if y + patch_len < m:
                    adj_idx = y + patch_len
                else:
                    adj_idx = y

                frac_vec = np.zeros([patch_len, int(n + abs(a_x.max()) * (patch_len - 1)), P], dtype='float')
                for p in range(P):
                    frac_vec[:, x, p] = np.linspace(hor_refo[y, x, p], hor_refo[adj_idx, x, p], patch_len)

                # load refocus value at x,y
                a = a_xy[y, x]

                # consider negative shift
                negative_a = int((patch_len - 1) * abs(a)) if a < 0 else 0

                # centralize column
                column_shift = int((a_x.max()-a)*(patch_len-1)/2)

                # put interpolated vector to refocusing plane
                newY = int(y + np.mod(y, patch_len) * (a - 1) + negative_a) + column_shift
                ver_refo[newY:newY + patch_len, :, :] = ver_refo[newY:newY + patch_len, :, :] + frac_vec

            # print progress status
            self.sta.progress(((x+1)/new_n+.5)*100, self.cfg.params[self.cfg.opt_prnt])

        # write image file to hard drive
        img = misc.Normalizer(ver_refo).uint16_norm()
        misc.save_img_file(img, os.path.join(self.fp, 'scheimpflug_' + str(patch_len) + 'px.tiff'))

        return True
