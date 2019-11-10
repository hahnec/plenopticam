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

try:
    from scipy.signal import medfilt
    from scipy.ndimage import median_filter
except ImportError:
    raise ImportError('Please install scipy package.')


class LfpColorEqualizer(LfpViewpoints):

    def __init__(self, *args, **kwargs):
        super(LfpColorEqualizer, self).__init__(*args, **kwargs)

        self._ref_img = kwargs['ref_img'] if 'ref_img' in kwargs else self.central_view

        self.proc_type = 'proc_ax_prop'

    def main(self):

        if self.proc_type == 'proc_vp_arr':
            self.proc_vp_arr(self.hist_match, ref=self._ref_img, msg='Color equalization')
        elif 'proc_ax_prop':
            self.proc_ax_propagate_2d(fun=self.hist_match, msg='Color equalization')

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
