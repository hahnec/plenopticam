#!/usr/bin/env python
import plenopticam.misc.clr_spc_conv

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

from plenopticam.lfp_aligner.lfp_microlenses import LfpMicroLenses
from plenopticam import misc
from plenopticam.misc.type_checks import rint

import numpy as np
from scipy.signal import convolve2d


class LfpDevignetter(LfpMicroLenses):

    def __init__(self, *args, **kwargs):
        super(LfpDevignetter, self).__init__(*args, **kwargs)

        # threshold from white image intensity distribution (key to find balance between edges turning black or white)
        default_thresh = np.mean(self._wht_img/self._wht_img.max()) - np.std(self._wht_img/self._wht_img.max())
        self._th = kwargs['th'] if 'th' in kwargs else default_thresh

        # noise level for decision making whether division by raw image or fit values
        self._noise_lev = kwargs['noise_lev'] if 'noise_lev' in kwargs else None
        self._noise_th = 0.1

        self._patch_mode = False

        self._lfp_div = np.zeros(self._lfp_img.shape)

        # white balance
        if len(self._wht_img.shape) == 3:
            # balance RGB channels in white image
            #self._wht_img = misc.eq_channels(self._wht_img)
            self._wht_img = misc.rgb2gray(self._wht_img)[..., np.newaxis]

        # check for same dimensionality
        self._wht_img = self._wht_img if len(self._wht_img.shape) == len(self._lfp_img.shape) else misc.rgb2gray(self._wht_img)

    def main(self):

        # analyse noise in white image
        self._noise_lev = self._estimate_noise_level() if self._noise_lev is None else self._noise_lev

        # print status
        self.sta.status_msg('De-vignetting', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # based on provided noise level in white image
        if self._patch_mode:
            # perform fitted white micro image division (high noise)
            self.proc_lens_iter(self.patch_devignetting, msg='De-vignetting')
        else:
            # perform raw white image division (low noise)
            self.wht_img_divide()

        ## identify pixels requiring treatment from significantly large intensity variations
        #self._lfp_div[self._lfp_div > self._lfp_img.max()] = self._lfp_img.max()
        #lfp_vgn = self._lfp_div - self._lfp_img
        #lfp_vgn[lfp_vgn < 0] = 0
        ##lfp_vgn = self._lfp_div
##
        ##import os
        ##misc.save_img_file(self._lfp_img, file_path=os.path.join(os.getcwd(), 'lfp_img.bmp'))
        ##misc.save_img_file(lfp_vgn, file_path=os.path.join(os.getcwd(), 'lfp_vgn.bmp'))
##
        #thresh = np.mean(lfp_vgn) - np.std(lfp_vgn)
        #lfp_vgn[lfp_vgn < thresh] = 0
##
        ## add selected pixels to light-field image
        #self._lfp_img += lfp_vgn*.5

        self._lfp_img = self._lfp_div#misc.Normalizer(self._lfp_div).uint16_norm()

        #misc.save_img_file(lfp_vgn, file_path=os.path.join(os.getcwd(), 'lfp_vgn_thresh.bmp'))
        #misc.save_img_file(self._lfp_img, file_path=os.path.join(os.getcwd(), 'lfp_out.bmp'))

    def wht_img_divide(self, th=None):

        self._th = th if th is not None else self._th

        # normalize white image
        self._wht_img /= np.percentile(self._wht_img, q=99.9)
        self._wht_img[self._wht_img > 1] = 1

        # threshold dark areas to prevent large number after division
        self._th = .15
        self._wht_img[self._wht_img < self._th] = self._th

        # divide light-field image
        self._lfp_div = self._lfp_img / self._wht_img

        # status
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def compose_vandermonde(self, x, y, deg=2):
        if deg == 1:
            return np.array([np.ones(len(x)), x, y]).T
        elif deg == 2:
            return np.array([np.ones(len(x)), x, y, x * y, x ** 2, y ** 2, x ** 2 * y, x * y ** 2, x ** 2 * y ** 2]).T
        elif deg == 3:
            return np.array([np.ones(len(x)), x, y, x * y, x ** 2, y ** 2, x ** 2 * y, x * y ** 2, x ** 2 * y ** 2,
                             x ** 3, y ** 3, x ** 3 * y, x * y ** 3, x ** 3 * y ** 2, x ** 2 * y ** 3,
                             x ** 3 * y ** 3]).T

    def fit_patch(self, patch, th=None):

        self._th = th if th is not None else self._th

        x = np.linspace(0, 1, patch.shape[1])
        y = np.linspace(0, 1, patch.shape[0])
        X, Y = np.meshgrid(x, y, copy=False)

        X = X.flatten()
        Y = Y.flatten()
        b = plenopticam.misc.clr_spc_conv.yuv_conv(patch)[..., 0].flatten() if len(patch.shape) == 3 else patch.flatten()

        A = self.compose_vandermonde(X, Y, deg=3)

        # Solve for a least squares estimate via pseudo inverse and coefficients in beta
        coeffs = np.dot(np.linalg.pinv(A), b)

        # create weighting window
        weight_win = np.dot(A, coeffs).reshape(patch.shape[1], patch.shape[0])[..., np.newaxis]
        weight_win /= weight_win.max()

        return coeffs, weight_win

    def apply_fit(self, patch, coeffs):

        x = np.linspace(0, 1, patch.shape[1])
        y = np.linspace(0, 1, patch.shape[0])
        X, Y = np.meshgrid(x, y, copy=False)

        X = X.flatten()
        Y = Y.flatten()
        A = self.compose_vandermonde(X, Y, deg=3)

        surf_z = np.dot(A, coeffs).reshape(patch.shape[1], patch.shape[0])

        f = surf_z[..., np.newaxis]

        patch /= f

        return patch

    def patch_devignetting(self, ly, lx):

        # find MIC by indices
        mic = self.get_coords_by_idx(ly=ly, lx=lx)

        # slice images
        margin = 1
        wht_win = self._extract_win(self._wht_img, mic, margin)
        lfp_win = self._extract_win(self._lfp_img, mic)
        div_win = self._extract_win(self._lfp_div, mic)

        # fit micro image
        if self._noise_lev > self._noise_th:
            _, weight_win = self.fit_patch(wht_win)
        else:
            weight_win = wht_win/wht_win.max()

        # thresholding (to prevent too large numbers in corrected image)
        th = .15
        weight_win[weight_win < th] = th

        # apply vignetting correction
        div_win += lfp_win / weight_win[margin:-margin, margin:-margin]

        return True

    def _extract_win(self, img, mic, margin=0):
        win = img[rint(mic[0]) - self._C-margin:rint(mic[0]) + self._C+margin+1,
                  rint(mic[1]) - self._C-margin:rint(mic[1]) + self._C+margin+1]
        return win

    def _estimate_noise_level(self):
        ''' estimate white image noise level '''

        # print status
        self.sta.status_msg('Estimate white image noise level', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        M = np.mean(self.cfg.calibs[self.cfg.ptc_mean])
        lp_kernel = misc.create_gauss_kernel(l=M)
        bw_img = misc.rgb2gray(self._wht_img) if len(self._wht_img.shape) == 3 else self._wht_img
        flt_img = convolve2d(bw_img, lp_kernel, 'same')

        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return np.std(bw_img-flt_img)
