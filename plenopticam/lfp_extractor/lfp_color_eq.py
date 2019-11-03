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

try:
    from scipy.signal import medfilt
    from scipy.ndimage import median_filter
except ImportError:
    raise ImportError('Please install scipy package.')

class LfpColorEqualizer(LfpViewpoints):

    def __init__(self, *args, **kwargs):
        super(LfpColorEqualizer, self).__init__(*args, **kwargs)

        self._ref_img = kwargs['ref_img'] if 'ref_img' in kwargs else self.central_view

        self.proc_type = 'proc_vp_arr'

    def main(self):

        if self.proc_type == 'proc_vp_arr':
            self.proc_vp_arr(self.hist_match, ref=self._ref_img, msg='Color equalization')
        elif 'prop_ax':
            self.hist_ax_propagation()

    def hist_match(self, src, ref):
        ''' channel-wise histogram matching inspired by Matthew Perry's implementation '''

        # parameter init
        src = src if len(src.shape) == 3 else src[..., np.newaxis]
        result = np.zeros_like(src)

        for ch in range(src.shape[2]):

            # convert to 1D arrays
            src_vec = src[..., ch].ravel()
            ref_vec = ref[..., ch].ravel()

            # analyze histograms
            src_vals, src_idxs, src_cnts = np.unique(src_vec, return_inverse=True, return_counts=True)
            ref_vals, ref_cnts = np.unique(ref_vec, return_counts=True)

            # compute cumulative distribution functions
            src_cdf = np.cumsum(src_cnts).astype(np.float64) / src_vec.size
            ref_cdf = np.cumsum(ref_cnts).astype(np.float64) / ref_vec.size

            # do the histogram mapping
            interp_vals = np.interp(src_cdf, ref_cdf, ref_vals)
            result[..., ch] = interp_vals[src_idxs].reshape(src[..., ch].shape)

            # check interrupt status
            if self.sta.interrupt:
                return False

        return result

    def proc_ax_propagation(self, fun, idx=None, axis=None):
        ''' apply provided function along axes direction '''

        axis = 0 if axis is None else axis
        j = 0 if idx is None else idx
        m, n = (0, 1) if axis == 0 else (1, 0)
        p, q = (1, -1) if axis == 0 else (-1, 1)

        for i in range(self._c):

            # swap axes indices
            j, i = (i, j) if axis == 1 else (j, i)

            print("j-src:"+str(self._c+j+m)+", i-src:"+str(self._c+i+n)+", j-ref:"+str(self._c+j)+", i-ref:"+str(self._c+i))
            print("j-src:"+str(self._c+(j+m)*p)+", i-src:"+str(self._c+(i+n)*q)+", j-ref:"+str(self._c+j*p)+", i-ref:"+str(self._c+i*q))

            ref_pos = self.vp_img_arr[self._c+j, self._c+i, ...]
            ref_neg = self.vp_img_arr[self._c+j*p, self._c+i*q, ...]

            self._vp_img_arr[self._c+j+m, self._c+i+n, ...] = fun(self.vp_img_arr[self._c+j+m, self._c+i+n, ...], ref_pos)
            self._vp_img_arr[self._c+(j+m)*p, self._c+(i+n)*q, ...] = fun(self.vp_img_arr[self._c+(j+m)*p, self._c+(i+n)*q, ...], ref_neg)

            # swap axes indices
            j, i = (i, j) if axis == 1 else (j, i)

            # check interrupt status
            if self.sta.interrupt:
                return False

        return True

    def hist_ax_propagation(self):
        ''' apply provided histogram matching along axes '''

        self.proc_ax_propagation(self.hist_match, idx=0, axis=0)

        for j in range(-self._c, self._c+1):

            # apply histogram matching along entire column
            self.proc_ax_propagation(self.hist_match, idx=j, axis=1)

            # progress update
            percent = (j+self._c+1) / self._vp_img_arr.shape[0] * 100
            self.sta.progress(percent, self.cfg.params[self.cfg.opt_prnt])

            # check interrupt status
            if self.sta.interrupt:
                return False

        return True
