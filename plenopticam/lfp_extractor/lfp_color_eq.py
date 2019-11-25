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

        # color transfer functions to be iterated through
        funs = (self.hist_match, self.mk_transfer, self.hist_match)
        n = len(funs)

        for i, fun in enumerate(funs):
            if self.prop_type == 'central':
                self.proc_vp_arr(fun=fun, ref=self._ref_img, msg='Color equalization', iter_num=i, iter_tot=n)
            elif self.prop_type == 'axial':
                self.proc_ax_propagate_2d(fun=fun, msg='Color equalization', iter_num=i, iter_tot=n)

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
