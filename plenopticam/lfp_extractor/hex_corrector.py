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
import os
from scipy.interpolate import interp1d

from plenopticam import misc
from plenopticam.lfp_extractor import LfpViewpoints
from plenopticam.lfp_aligner.lfp_resampler import LfpResampler


class HexCorrector(LfpViewpoints):

    def __init__(self, *args, **kwargs):
        super(HexCorrector, self).__init__(*args, **kwargs)

        self.ref_img = kwargs['ref_img'] if 'ref_img' in kwargs else self.central_view
        self.method = kwargs['method'] if 'method' in kwargs else 'cubic'

        if self.cfg.calibs[self.cfg.mic_list] is not None:
            # analyse
            self.hex_odd = LfpResampler.get_hex_direction(np.asarray(self.cfg.calibs[self.cfg.mic_list]))
        else:
            # reset pattern type to skip hex correction process
            self.cfg.calibs[self.cfg.pat_type] = 'rec'

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # remove hexagonal artifact
        if self.cfg.calibs[self.cfg.pat_type] == 'hex':
            self.proc_vp_arr(self.ver_hex_bulge, msg='Hexagonal artifact removal')

        # normalize light-field
        self.vp_img_arr = misc.Normalizer(self.vp_img_arr).uint16_norm()

        return True

    def hex_interp_1d(self, img):

        hex_stretch = 2 / np.sqrt(3)
        m, n, ch = img.shape if len(img.shape) == 3 else img.shape + (1,)
        s_check = [0, 1] if self.hex_odd else [1, 0]
        final = np.zeros([m, int(np.round(n * hex_stretch)), ch])
        new_l = int(np.round(img.shape[1] * hex_stretch))

        img = img.astype('float')/img.max()
        for p in range(ch):
            for j in range(2):
                s = -0.5 * s_check[j]
                for i in range(img.shape[0])[j::2]:
                    fun = interp1d(np.arange(len(img[i, :, p])), img[i, :, p], kind=self.method, fill_value="extrapolate")
                    final[i, ..., p] = fun(np.linspace(0, len(img[i, :, p])-1, new_l)+s)

        return final

    def ver_hex_bulge(self, img):

        # variable init
        img = np.divide(img.astype('float'), img.max(), out=np.zeros_like(img), where=img != 0)
        m, n, ch = img.shape if len(img.shape) == 3 else img.shape + (1,)

        # j for shifted and i represents truth (unshifted)
        i, j = [1, 0] if self.hex_odd else [0, 1]

        # gradient between shifted and unshifted (responsive to hex artifacts)
        if img[i::2, ...].shape[0] == img[j::2, ...].shape[0]:
            dif = img[j::2, ...]-img[i::2, ...]
        elif img[j::2, ...].shape[0] == img[i::2, ...].shape[0]+1:
            dif = img[j::2, ...][:-1]-img[i::2, ...]
        elif img[j::2, ...].shape[0]+1 == img[i::2, ...].shape[0]:
            dif = img[j::2, ...] - img[i::2, ...][:-1]
        else:
            self.sta.error('Image dimension mismatch')
            return False

        # gradient between unshifted (responsive to real object edges)
        edg = img[i::2, ...][:-1]-img[i+2::2, ...]
        edg *= 0.75

        # absolute values
        dif = abs(dif)
        edg = abs(edg)

        # (don't throw away channel information)
        dif = dif.sum(2)
        edg = edg.sum(2)

        # deduct actual edges
        karr = dif - edg if dif.shape[0] == edg.shape[0] else dif[:-1, ...] - edg
        karr = np.divide(karr, karr.max(), out=np.zeros_like(karr), where=karr != 0)
        karr[karr < 0] = 0
        if self.cfg.params[self.cfg.opt_dbug]:
            misc.save_img_file(karr, os.path.join(self.cfg.exp_path, 'karr.png'))

        # replicate mask to 3 color channels
        arr = np.zeros(karr.shape+(3,))
        for p in range(ch):
            arr[..., p] = karr

        # threshold values with insufficient difference
        mask = np.divide(arr, arr.max(), out=np.zeros_like(arr), where=arr != 0)
        th = 0.1
        mask[mask < th] = 0
        mask[mask >= th] = 1

        # ignore small regions
        mask = self.retain_connected(mask, n=4)

        # generate mask
        if self.cfg.params[self.cfg.opt_dbug]:
            full_mask = np.zeros(img.shape)
            if full_mask[j::2, ...].shape[0] == mask.shape[0]:
                full_mask[j::2, ...] = mask
            else:
                full_mask[j::2, ...][:-1] = mask
            misc.save_img_file(full_mask, os.path.join(self.cfg.exp_path, 'hex_filter_mask.png'), tag=True)

        # generate image indicating which pixels were treated
        if self.cfg.params[self.cfg.opt_dbug]:
            tes = img.copy()
            for p in range(ch):
                if tes[j::2, ...].shape[0] == mask.shape[0]:
                    tes[j::2, :, p][mask[..., p] != 0] = tes.max()
                else:
                    tes[j::2, :, p][:-1][mask[..., p] != 0] = tes.max()
            tes_out = np.divide(tes, tes.max(), out=np.zeros_like(tes), where=tes != 0)
            misc.save_img_file(tes_out, os.path.join(self.cfg.exp_path, 'ident.png'), tag=True)

        idxs = np.array(mask.nonzero())
        r = 1
        valid_idx = np.where((idxs[0] > r) & (idxs[1] > r) & (img[j::2].shape[0]-idxs[0] > r) & (img.shape[1]-idxs[1] > r))[0]
        idxs_vals = list(zip(idxs[0][valid_idx], idxs[1][valid_idx], idxs[2][valid_idx]))

        res = img.copy()
        for idx in idxs_vals:
            new_val = np.mean(img[i::2, ...][idx[0]:idx[0]+2, idx[1], idx[2]], axis=0)
            res[j::2, ...][idx[0], idx[1], idx[2]] = new_val

        if self.cfg.params[self.cfg.opt_dbug]:
            misc.save_img_file(res, os.path.join(self.cfg.exp_path, 'hex-corr.png'))

        return res

    @staticmethod
    def retain_connected(mask, n):

        w = mask.copy().T.ravel().astype('bool')

        idx = np.flatnonzero(np.r_[True, ~w, True])
        lens = np.diff(idx) - 1
        comb = np.vstack(list(zip(idx, lens)))
        filt = comb[comb[:, 1] >= n]
        vals = np.zeros_like(w)
        for f in filt:
            vals[f[0]:f[0]+f[1]] = 1

        return np.reshape(vals, mask.T.shape).T.astype('uint8')
