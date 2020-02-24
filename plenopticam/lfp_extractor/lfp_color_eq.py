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

# external libs
import numpy as np

from plenopticam.lfp_extractor import LfpViewpoints
from plenopticam.lfp_aligner.cfa_processor import CfaProcessor
from plenopticam import misc

try:
    from scipy.signal import medfilt
    from scipy.ndimage import median_filter
except ImportError:
    raise ImportError('Please install scipy package.')


class LfpColorEqualizer(LfpViewpoints):

    def __init__(self, *args, **kwargs):
        super(LfpColorEqualizer, self).__init__(*args, **kwargs)

        self._ref_img = kwargs['ref_img'] if 'ref_img' in kwargs else self.central_view
        self.prop_type = kwargs['prop_type'] if 'prop_type' in kwargs else 'central'

    def main(self):

        if self.vp_img_arr is not None and not self.sta.interrupt:
            self.apply_ccm()
            self._ref_img = self.central_view

        # color transfer functions to be iterated through
        funs = (self.hist_match, self.mk_transfer, self.hist_match)
        n = len(funs)

        for i, fun in enumerate(funs):
            if self.prop_type == 'central':
                self.proc_vp_arr(fun=fun, ref=self._ref_img, msg='Color equalization', iter_num=i, iter_tot=n)
            elif self.prop_type == 'axial':
                self.proc_ax_propagate_2d(fun=fun, msg='Color equalization', iter_num=i, iter_tot=n)

        # zero-out sub-apertures suffering from cross-talk (e.g. to exclude them in refocusing)
        self._exclude_crosstalk_views()

    def apply_ccm(self):

        # color matrix correction
        if 'ccm' in self.cfg.lfpimg.keys():

            # ccm mat selection
            if 'ccm_wht' in self.cfg.lfpimg:
                ccm_arr = self.cfg.lfpimg['ccm_wht']
            elif 'ccm' in self.cfg.lfpimg:
                #ccm_arr = self.cfg.lfpimg['ccm']
                ccm_arr = np.array([2.4827811717987061, -1.1018080711364746, -0.38097298145294189,
                                    -0.36761483550071716, 1.6667767763137817, -0.29916191101074219,
                                    -0.18722048401832581, -0.73317205905914307, 1.9203925132751465])
            else:
                ccm_arr = np.diag(np.ones(3))

            # normalize
            self.vp_img_arr /= self.vp_img_arr.max()

            if 'exp' in self.cfg.lfpimg:
                sat_lev = 2 ** (-self.cfg.lfpimg['exp'])
            else:
                sat_lev = 1
            self.vp_img_arr *= sat_lev

            # transpose and flip ccm_mat for RGB order
            ccm_mat = np.reshape(ccm_arr, (3, 3)).T
            self._vp_img_arr = CfaProcessor().correct_color(self._vp_img_arr.copy(), ccm_mat=ccm_mat)

            # remove potential NaNs
            self._vp_img_arr[self._vp_img_arr < 0] = 0
            self._vp_img_arr[self._vp_img_arr > sat_lev] = sat_lev
            #self._vp_img_arr /= sat_lev
            self._vp_img_arr /= self._vp_img_arr.max()

        return True

    @staticmethod
    def hist_match(src, ref):
        ''' channel-wise histogram matching inspired by Matthew Perry's implementation '''

        # parameter init
        src = src if len(src.shape) == 3 else src[..., np.newaxis]
        ref = ref if len(ref.shape) == 3 else ref[..., np.newaxis]
        result = np.zeros_like(src)

        for ch in range(src.shape[2]):

            # convert to 1D arrays
            src_vec = src[..., ch].ravel()
            ref_vec = ref[..., ch].ravel()

            # analyze histograms
            _, src_idxs, src_cnts = np.unique(src_vec, return_inverse=True, return_counts=True)
            ref_vals, ref_cnts = np.unique(ref_vec, return_counts=True)

            # compute cumulative distribution functions
            src_cdf = np.cumsum(src_cnts).astype(np.float64) / src_vec.size
            ref_cdf = np.cumsum(ref_cnts).astype(np.float64) / ref_vec.size

            # do the histogram mapping
            interp_vals = np.interp(src_cdf, ref_cdf, ref_vals)
            result[..., ch] = interp_vals[src_idxs].reshape(src[..., ch].shape)

        return result

    def mk_transfer(self, src, ref):

        if src.shape[2] != 3 or ref.shape[2] != 3:
            self.sta.status_msg(msg='Image must have 3 dimensions')
            self.sta.interrupt = True

        X0 = np.reshape(src, [-1, src.shape[2]])
        X1 = np.reshape(ref, [-1, ref.shape[2]])

        A = np.cov(X0.T)
        B = np.cov(X1.T)

        T = self.mkl(A, B)

        mX0 = np.repeat(np.mean(X0, axis=0)[..., np.newaxis], X0.shape[0], axis=1).T
        mX1 = np.repeat(np.mean(X1, axis=0)[..., np.newaxis], X1.shape[0], axis=1).T

        XR = np.dot((X0 - mX0), T) + mX1
        IR = np.reshape(XR, src.shape)
        IR = misc.Normalizer(IR).uint16_norm()

        return IR

    @staticmethod
    def mkl(A, B):

        [Da2, Ua] = np.linalg.eig(A)
        Ua = np.array([Ua[:, 2] * -1, Ua[:, 1], Ua[:, 0] * -1]).T
        # Da2 = np.diag(Da2)
        Da2[Da2 < 0] = 0
        # Da = np.diag(np.sqrt(Da2) + np.spacing(1))  # + eps
        Da = np.diag(np.sqrt(Da2[::-1]))
        C = np.dot(Da, np.dot(Ua.T, np.dot(B, np.dot(Ua, Da))))
        [Dc2, Uc] = np.linalg.eig(C)
        # Uc = np.array([Uc[:, 2] * -1, Uc[:, 1], Uc[:, 0] * -1]).T
        # Dc2 = np.diag(Dc2)
        Dc2[Dc2 < 0] = 0
        # Dc = np.diag(np.sqrt(Dc2) + np.spacing(1))    #  + eps
        Dc = np.diag(np.sqrt(Dc2))  # [::-1]
        Da_inv = np.diag(1. / (np.diag(Da + np.spacing(1))))
        T = np.dot(Ua, np.dot(Da_inv, np.dot(Uc, np.dot(Dc, np.dot(Uc.T, np.dot(Da_inv, Ua.T))))))

        return T

    def _exclude_crosstalk_views(self):

        ratio = self.vp_img_arr.shape[3]/self.vp_img_arr.shape[2]
        r = self._M // 2
        mask = np.zeros([2*r+1, 2*r+1])

        # determine mask for affected views
        for x in range(-r, r + 1):
            for y in range(-r, r + 1):
                if int(np.round(np.sqrt(x ** 2 + y ** 2 * ratio))) > r + 2:
                    mask[r + y][r + x] = 1

        # extract coordinates from mask
        coords_table = [(y, x) for y in range(len(mask)) for x in range(len(mask)) if mask[y][x]]

        # zero-out selected views
        for coords in coords_table:
            self.vp_img_arr[coords[0], coords[1], ...] = np.zeros(self.vp_img_arr.shape[2:])

        return True
