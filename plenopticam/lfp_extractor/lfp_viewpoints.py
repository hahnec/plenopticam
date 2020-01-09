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
from plenopticam import misc

import numpy as np
from scipy.interpolate import interp2d


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
        ''' process viewpoint images based on provided function handle and argument data '''

        # percentage indices for tasks having sub-processes
        iter_num = kwargs['iter_num'] if 'iter_num' in kwargs else 0
        iter_tot = kwargs['iter_tot'] if 'iter_tot' in kwargs else 1

        # status message handling
        if iter_num == 0:
            msg = kwargs['msg'] if 'msg' in kwargs else 'Viewpoint process'
            self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_prnt])

        args = self.remove_proc_keys(kwargs, data_type=list)

        new_shape = fun(self._vp_img_arr[0, 0, ...], *args).shape
        new_array = np.zeros(self._vp_img_arr.shape[:2] + new_shape)

        #try:
        for j in range(self._vp_img_arr.shape[0]):
            for i in range(self._vp_img_arr.shape[1]):

                res = fun(self._vp_img_arr[j, i, ...], *args)

                if res.shape == self._vp_img_arr.shape:
                    self._vp_img_arr[j, i, ...] = res
                else:
                    new_array[j, i, ...] = res
                    #shape_diff = np.array(res.shape) - np.array(self._vp_img_arr[j, i, ...].shape)
                    #pad_vec = [(0, x) for x in shape_diff]
                    #np.pad(self._vp_img_arr[j, i, ...], self._vp_img_arr[j, i, ...].shape-res.shape)
                    #self._vp_img_arr[j, i, ...] = res

                # progress update
                percent = (j*self._vp_img_arr.shape[1]+i+1)/np.dot(*self._vp_img_arr.shape[:2])
                percent = percent / iter_tot + iter_num / iter_tot
                self.sta.progress(percent*100, self.cfg.params[self.cfg.opt_prnt])

            # check interrupt status
            if self.sta.interrupt:
                return False
        #except:
        #    if len(self.vp_img_arr.shape) != 5:
        #        raise NotImplementedError

        if new_array.sum() != 0:
            self._vp_img_arr = new_array

        return True

    def get_move_coords(self, pattern, arr_dims, r=None):

        # parameter initialization
        pattern = 'circle' if pattern is None else pattern
        r = r if r is not None else self._C
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
                        mask[self._C + y][self._C + x] = 1

        # extract coordinates from mask
        coords_table = [(y, x) for y in range(len(mask)) for x in range(len(mask)) if mask[y][x]]

        # sort coordinates in angular order
        coords_table.sort(key=lambda coords: np.arctan2(coords[0] - self._C, coords[1] - self._C))

        return coords_table

    def reorder_vp_arr(self, pattern=None, lf_radius=None):

        # parameter initialization
        pattern = 'circle' if pattern is None else pattern
        arr_dims = self.vp_img_arr.shape[:2]
        move_coords = self.get_move_coords(pattern, arr_dims, r=lf_radius)

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
        ''' concatenation of all sub-aperture images for single image representation '''
        return np.moveaxis(np.concatenate(np.moveaxis(np.concatenate(np.moveaxis(self.vp_img_arr, 1, 2)), 0, 2)), 0, 1)

    def hex_align(self):

        # translate every other row via 2D interpolations (principle resembles linocut)
        #self.proc_vp_arr(self.hex_linocut, msg='Hex resampling')
        #self.proc_vp_arr(self.spatial_hex_interp, msg='Hex resampling')
        #self.proc_vp_arr(self.bilinear_hex_interp, msg='Hex resampling')
        #self.proc_vp_arr(self.hex_dans, msg='Hex resampling')
        self.proc_vp_arr(self.ver_hex_bulge, msg='Hex correction')

        self.vp_img_arr = misc.Normalizer(self.vp_img_arr).uint16_norm()

        return True

    def hex_dans2d(self, img):

        from scipy.interpolate import interp1d, interp2d
        from plenopticam.lfp_aligner.lfp_resampler import LfpResampler

        method = 'cubic'
        hex_stretch = 2 / np.sqrt(3)
        m, n, ch = img.shape if len(img.shape) == 3 else img.shape + (1,)
        hex_odd = LfpResampler()._get_hex_direction(np.asarray(self.cfg.calibs[self.cfg.mic_list]))
        s_check = [0, 1] if hex_odd else [1, 0]
        final = np.zeros([m, int(np.round(n * hex_stretch)), ch])
        new_l = int(np.round(img.shape[1] * hex_stretch))
        R = 3/np.sqrt(3)
        img = img.astype('float') / img.max()
        img_list = [img[0::2, ...], img[1::2, ...]]

        # 1D vertical stretching
        for k, ref in enumerate(img_list):
            vwa = np.zeros((int(np.round(ref.shape[0]*R)), ref.shape[1], ch))
            for p in range(ch):
                for i in range(img.shape[1]):
                    fun = interp1d(np.arange(len(ref[:, i, p])), ref[:, i, p], kind=method, fill_value="extrapolate")
                    vwa[:, i, p] = fun(np.linspace(0, len(ref[:, i, p])-1, int(np.round(ref[:, i, p].shape[0]*R))))
            img_list[k] = vwa

        final = img_list[0]+img_list[1]

        # 2D horizontal stretching
        for k, ref in enumerate(img_list):
            hwa = np.zeros([ref.shape[0], int(np.round(n * hex_stretch)), ch])
            for p in range(ch):
                s = -0.5 * s_check[k]
                fun = interp2d(range(ref.shape[1]), range(ref.shape[0]), ref[..., p], kind=method)
                hwa[..., p] = fun(np.linspace(0, ref.shape[1]-1, new_l)+s, np.arange(ref.shape[0]))
            img_list[k] = hwa

        # 2D vertical shrinkage
        mrg = np.zeros((img_list[0].shape[0]+img_list[1].shape[0], img_list[0].shape[1], ch))
        #mrg[0::2, ...] = img_list[0]
        #mrg[1::2, ...] = img_list[1]
        #mrg = np.vstack(img_list).reshape((-1, img_list[0].shape[1], ch), order='F')
        for v in range(img_list[0].shape[0]+img_list[1].shape[0]-2):
            mrg[v, ...] = img_list[0][v//2, ...] if np.mod(v, 2) == 0 else img_list[1][v//2, ...]
        for p in range(ch):
            fun = interp2d(range(mrg.shape[1]), range(mrg.shape[0]), mrg[..., p], kind=method)
            final[..., p] = fun(np.arange(mrg.shape[1]), np.linspace(0, mrg.shape[1]-1, int(np.round(mrg.shape[0]/R))))

        return final

    def hex_dans(self, img):

        from scipy.interpolate import interp2d, interp1d
        from plenopticam.lfp_aligner.lfp_resampler import LfpResampler

        method = 'cubic'
        hex_stretch = 2 / np.sqrt(3)
        m, n, ch = img.shape if len(img.shape) == 3 else img.shape + (1,)
        hex_odd = LfpResampler()._get_hex_direction(np.asarray(self.cfg.calibs[self.cfg.mic_list]))
        s_check = [0, 1] if hex_odd else [1, 0]
        final = np.zeros([m, int(np.round(n * hex_stretch)), ch])
        new_l = int(np.round(img.shape[1] * hex_stretch))

        img = img.astype('float')/img.max()
        for p in range(ch):
            for j in range(2):
                s = -0.5 * s_check[j]
                for i in range(img.shape[0])[j::2]:
                    fun = interp1d(np.arange(len(img[i, :, p])), img[i, :, p], kind=method, fill_value="extrapolate")
                    final[i, ..., p] = fun(np.linspace(0, len(img[i, :, p])-1, new_l)+s)

        return final

    def bilinear_hex_interp(self, img):

        from plenopticam import misc
        hex_stretch = 2 / np.sqrt(3)
        method = 'quintic'
        m, n, ch = img.shape if len(img.shape) == 3 else img.shape + (1,)
        final = np.zeros([m, int(np.round(n * hex_stretch)), ch])
        R = np.sqrt(3) / 3  # hexagonal height width ratio
        T = 2+R*2   # total for weight norm

        # get interpolation weights
        tb_weight = R/T
        lr_weight = 1/T

        img = img.astype('float')/img.max()
        for i in range(img.shape[0])[1::2]:
            row_u = img[i-1, ...] if i >= 1 else np.zeros(img.shape[1:])
            row_l = img[i, ...]
            row_r = np.vstack((img[i, 1:], row_l[-1, ...])) if len(row_l.shape) > 1 else np.append(img[i, 1:], row_l[-1])
            row_b = img[i+1, ...] if i < img.shape[0]-1 else np.zeros(img.shape[1:])
            # bilinear interpolation for hex arrangement
            img[i, ...] = tb_weight*(row_u+row_b)+lr_weight*(row_l+row_r)

        #for p in range(ch):
        #    final[..., p] = misc.img_resize(img[..., p], x_scale=hex_stretch, y_scale=1, method=method)[..., 0]
        final = img

        return final

    def spatial_hex_interp(self, img):

        from scipy.interpolate import interp2d, interp1d
        from plenopticam.lfp_aligner.lfp_resampler import LfpResampler

        method = 'cubic'
        m, n, ch = img.shape if len(img.shape) == 3 else img.shape + (1,)
        hex_odd = LfpResampler()._get_hex_direction(np.asarray(self.cfg.calibs[self.cfg.mic_list]))
        s = -0.5 + hex_odd
        hex_stretch = 2 / np.sqrt(3)
        final = np.zeros([m, int(np.round(n*hex_stretch)), ch])
        R = 2*np.sqrt(3)/3

        img = img.astype('float')/img.max()
        for p in range(ch):

            orig = img.copy()
            pos = img.copy()

            # translate every other row
            #fun = interp2d(range(orig[0::2, :].shape[1]), range(orig[0::2, :].shape[0]), orig[0::2, :, p], kind=method)
            #pos[0::2, :, p] = fun(np.arange(orig[0::2, :].shape[1])+s, np.arange(orig[0::2, :].shape[0])+s)
            for i, row in enumerate(orig[0::2, :, p]):
                fun = interp1d(range(orig[0::2, :].shape[1]), row, kind=method)
                pos[2*i, :, p] = fun(np.arange(orig[0::2, :].shape[1])+s)
            #pos[..., p] = self.bilinear_hex_interp(orig[..., p])

            # linear vertical stretching (for equal weights in subsequent hex stretching)
            vwa = np.zeros((int(np.round(pos.shape[0]*R)), pos.shape[1]))
            for i, col in enumerate(pos[..., p].T):
                fun = interp1d(range(len(col)), col, kind=method)
                vwa[..., i] = fun(np.linspace(0, len(col)-1, int(np.round(len(col)*R))))

            #fun = interp2d(range(vwa.shape[1]), range(str.shape[0]), vwa, kind=method)
            #vwa = fun(np.arange(vwa.shape[1])-s, np.arange(vwa.shape[0])-s)

            str = misc.img_resize(vwa, x_scale=hex_stretch, y_scale=1, method=method)[..., 0]

            # linear vertical shrinking (for equal weights in subsequent hex stretching)
            vwa = np.zeros((int(np.round(str.shape[0]/R)), str.shape[1]))
            for i, col in enumerate(str.T):
                fun = interp1d(range(len(col)), col, kind=method)
                vwa[..., i] = fun(np.linspace(0, len(col)-1, int(np.round(len(col)/R))))

            final[..., p] = vwa

        return final

    def hex_linocut(self, img):

        from scipy.interpolate import interp2d
        from plenopticam import misc

        method = 'quintic'
        m, n, ch = img.shape if len(img.shape) == 3 else img.shape + (1,)
        s = -0.5
        hex_stretch = 2 / np.sqrt(3)
        final = np.zeros([m, int(np.round(n*hex_stretch)), ch])

        img = img.astype('float')/img.max()
        for p in range(ch):

            orig = img.copy()
            pos = img.copy()

            # translate every other row
            fun = interp2d(range(orig[0::2, :].shape[1]), range(orig[0::2, :].shape[0]), orig[0::2, :, p], kind=method)
            pos[0::2, :, p] = fun(np.arange(orig[0::2, :].shape[1])+s, np.arange(orig[0::2, :].shape[0])+s)

            # do horizontal stretching
            str = misc.img_resize(pos[..., p], x_scale=hex_stretch, y_scale=1, method=method)[..., 0]

            # translate back
            fun = interp2d(range(str.shape[1]), range(str.shape[0]), str, kind=method)
            new_img = fun(np.arange(str.shape[1])-s, np.arange(str.shape[0])-s)

            # shrink horizontally and copy every other row
            new_sqr = misc.img_resize(new_img, x_scale=1./hex_stretch, y_scale=1, method=method)[..., 0]
            orig[1::2, :-1, p] = new_sqr[1::2, ...]

            # do forward stretching
            final[..., p] = misc.img_resize(orig[..., p], x_scale=hex_stretch, y_scale=1, method=method)[..., 0]
            final[1::2, :, p] = new_img[1::2, ...]

        # import matplotlib.pyplot as plt
        # from plenopticam import misc
        # plt.imshow(misc.Normalizer(img[0::2, :]).uint8_norm())

        return final

    def ver_hex_corr(self, img):

        from plenopticam import misc
        method = 'quintic'
        m, n, ch = img.shape if len(img.shape) == 3 else img.shape + (1,)
        R = np.sqrt(3) / 3  # hexagonal height width ratio
        T = 2+R*2   # total for weight norm

        # get interpolation weights
        tb_weight = .2/2#R/T
        lr_weight = .8#1/T

        img = img.astype('float')/img.max()
        for i in range(img.shape[0])[1::2]:
            row_u = img[i-1, ...] if i >= 1 else np.ones(img.shape[1:])*.5
            row_m = img[i, ...]
            row_b = img[i+1, ...] if i < img.shape[0]-1 else np.ones(img.shape[1:])*.5
            # vertical interpolation for hex arrangement
            img[i, ...] = tb_weight*(row_u+row_b)+lr_weight*row_m

        return img

    def ver_hex_bulge(self, img):

        import matplotlib.pyplot as plt
        import os
        from scipy.signal import medfilt

        from plenopticam import misc
        method = 'cubic'
        m, n, ch = img.shape if len(img.shape) == 3 else img.shape + (1,)
        from plenopticam.lfp_aligner.lfp_resampler import LfpResampler
        hex_odd = LfpResampler()._get_hex_direction(np.asarray(self.cfg.calibs[self.cfg.mic_list]))
        i, j = [1, 0] if hex_odd else [0, 1]    # j for shifted and i represents truth (unshifted)

        # vertically interpolate pixels to get reference
        img = img.astype('float') / img.max()
        phi = np.zeros((img[i::2, ...].shape[0], img.shape[1], img.shape[2]))
        shi = img.copy()
        for p in range(ch):
            fun = interp2d(range(img[i::2, ...].shape[1]), range(img[i::2, ...].shape[0]), img[i::2, :, p], kind=method)
            #shi[..., p] = fun(np.arange(img.shape[1]), np.linspace(0, img[i::2, ...].shape[0]+s, img[i::2, ...].shape[0]))
            phi[..., p] = fun(np.arange(img.shape[1]), np.linspace(0, img[i::2, ...].shape[0]+.5, img[i::2, ...].shape[0]))
        shi[j::2, ...] = phi
        #shi = img[:-1, ...].copy()

        # difference and ratio
        dif = shi[j::2, ...]-img[j::2, ...]
        rat = shi[j::2, ...]/img[j::2, ...]

        # difference and ratio
        dif = img[i::2, ...]-img[j::2, ...] #if hex_odd else img[i::2, ...][:-1]-img[j::2, ...]
        rat = img[i::2, ...]/img[j::2, ...] #if hex_odd else img[i::2, ...][:-1]/img[j::2, ...]

        # form long col vector as we are only interested in vertical direction
        dif_vec = dif.copy().T.ravel()
        rat_vec = rat.copy().T.ravel()

        # remove spikes (fast peaks in vertical direction)
        #rat_dif = np.append(np.diff(rat_vec), 0)
        #rat_vec[rat_dif>rat_dif.max()*8] = 0
        dif_med = medfilt(dif_vec, 3)
        rat_med = medfilt(rat_vec, 3)

        # 1-D low pass to eliminate hi freq noise
        gauss = misc.create_gauss_kernel(10, sig=1)[:, 3]
        dif_gau = np.convolve(dif_med, gauss, 'same')
        rat_gau = np.convolve(rat_med, gauss, 'same')

        rat_res = dif_gau.reshape(dif.T.shape).T
        #rat_res = rat_gau.reshape(rat.T.shape).T

        #rat_vec = rat_res.copy().ravel()
        ##rat_med = medfilt(rat_vec, 3)
        #rat_gau = np.convolve(rat_vec, gauss, 'same')
        #rat_gau = rat_gau.reshape(rat.T.shape).T
        #rat_res -= rat_gau

        rat_res -= np.mean(rat_res)
        rat_res = np.abs(rat_res)
        rat_res /= rat_res.max()
        #rat_res[rat_res < 0.15] = 0

        misc.save_img_file(rat_res, os.path.join(self.cfg.exp_path, 'img_filter.png'), tag=True)

        #np.hstack(rat_res, np.zeros((img.shape[1], 3)))
        mask = rat_res.sum(2)/rat_res.sum(2).max()  # don't throw away this information
        mask[mask < 0.2] = 0
        mask[mask >= 0.2] = 1

        tes = img.copy()
        if hex_odd:
            tes[j::2][:-1][mask != 0] = np.array([tes.max(), tes.max(), tes.max()])
        else:
            tes[j::2][mask != 0] = np.array([tes.max(), tes.max(), tes.max()])
            #tes[j::2][mask != 0] = np.array([tes.max(), tes.max(), tes.max()])

        misc.save_img_file(tes / tes.max(), os.path.join(self.cfg.exp_path, 'ident.png'), tag=True)

        idxs = np.array(mask.nonzero())
        r = 1
        valid_idx = np.where((idxs[0] > r) & (idxs[1] > r) & (img[j::2].shape[0]-idxs[0] > r) & (img.shape[1]-idxs[1] > r))[0]
        idxs_vals = list(zip(idxs[0][valid_idx], idxs[1][valid_idx]))

        res = img.copy()
        for idx in idxs_vals:
            new_val = phi[idx[0], idx[1]]#np.mean(img[i::2, ...][idx[0]:idx[0]+2, idx[1]], axis=0)
            res[j::2, ...][idx[0], idx[1]] = new_val#np.array([255, 255, 255])#
        misc.save_img_file(res, os.path.join(self.cfg.exp_path, 'hex-corr.png'))

        return res
