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

from plenopticam.lfp_aligner.lfp_microlenses import LfpMicroLenses
from plenopticam import misc
from plenopticam.misc.type_checks import rint

import numpy as np
from scipy.signal import convolve2d
from color_space_converter import rgb2gry


class LfpDevignetter(LfpMicroLenses):

    def __init__(self, *args, **kwargs):
        super(LfpDevignetter, self).__init__(*args, **kwargs)

        self._wht_img = np.ones(self._lfp_img.shape) if self._wht_img is None else self._wht_img

        # config for decision making whether division by raw image or fit values
        self.noise_lev = kwargs['noise_lev'] if 'noise_lev' in kwargs else None
        self.noise_th = 0.05
        self.patch_mode = False

        # add noise
        self.test = False
        if self.test:
            self._wht_img += np.random.normal(0, .15, self._wht_img.shape)

        # white balance
        if len(self._wht_img.shape) == 3:
            # balance RGB channels in white image
            self._wht_img = rgb2gry(self._wht_img) if self._wht_img.shape[2] == 3 else self._wht_img

        # check for same dimensionality
        self._wht_img = self._wht_img if len(self._wht_img.shape) == len(self._lfp_img.shape) else rgb2gry(self._wht_img)

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # normalize white image to upper percentile
        self._wht_img /= np.percentile(self._wht_img, q=99.9)

        # analyse noise in white image
        self.noise_lev = self._estimate_noise_level() if self.noise_lev is None else self.noise_lev

        # print status
        self.sta.status_msg('De-vignetting', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # de-vignetting based on mode and present noise level in white image
        if self.patch_mode and self.noise_lev > self.noise_th:
            # perform fitted white micro image division (to reduce noise propagation)
            self.proc_lens_iter(self.patch_devignetting, prnt=False)
        else:
            # perform ordinary de-vignetting from raw white image (low noise)
            self.wht_img_divide()

        return True

    def wht_img_divide(self):
        """ ordinary devignetting using raw white image division """

        # divide light-field image
        init_arr = np.zeros_like(self._lfp_img)
        self._lfp_img = np.divide(self._lfp_img.copy(), self._wht_img, out=init_arr, where=self._wht_img != 0)

        # status
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def patch_devignetting(self, ly, lx, margin=1):
        """ patch-wise devignetting via white image patch from least-squares regression """

        # find MIC by indices
        mic = self.get_coords_by_idx(ly=ly, lx=lx)

        # slice images
        wht_win = self._extract_win(self._wht_img, mic, margin)
        lfp_win = self._extract_win(self._lfp_img, mic, margin)

        # fit micro image
        if self.noise_lev > self.noise_th:
            _, weight_win = self.fit_patch(wht_win)
        else:
            weight_win = wht_win/wht_win.max()

        # apply vignetting correction
        div_win = np.divide(lfp_win, weight_win, out=np.zeros_like(weight_win), where=weight_win != 0)
        olap = self._C + margin
        self._lfp_img[rint(mic[0])-olap:rint(mic[0])+olap+1, rint(mic[1])-olap:rint(mic[1])+olap+1] = div_win

        return True

    def _extract_win(self, img, mic, margin=0):
        win = img[rint(mic[0]) - self._C-margin:rint(mic[0]) + self._C+margin+1,
                  rint(mic[1]) - self._C-margin:rint(mic[1]) + self._C+margin+1]
        return win

    def fit_patch(self, patch):
        """ compute polynomial coefficients and intensity map of 2-D image via least-squares regression """

        x = np.linspace(0, 1, patch.shape[1])
        y = np.linspace(0, 1, patch.shape[0])
        X, Y = np.meshgrid(x, y, copy=False)

        X = X.flatten()
        Y = Y.flatten()
        b = rgb2gry(patch)[..., 0].flatten() if len(patch.shape) == 3 else patch.flatten()

        A = self.compose_vandermonde_2d(X, Y, deg=3)

        # solve for a least squares estimate via pseudo inverse and coefficients in b
        coeffs = np.dot(np.linalg.pinv(A), b)

        # create weighting window
        weight_map = np.dot(A, coeffs).reshape(patch.shape[1], patch.shape[0])
        weight_map /= weight_map.max()

        return coeffs, weight_map

    @staticmethod
    def compose_vandermonde_2d(x, y, deg=2):
        """ compute Vandermonde matrix based on two coordinate dimensions and degree """

        if deg == 1:
            return np.array([np.ones(len(x)), x, y]).T
        elif deg == 2:
            return np.array([np.ones(len(x)), x, y, x * y, x ** 2, y ** 2, x ** 2 * y, x * y ** 2, x ** 2 * y ** 2]).T
        elif deg == 3:
            return np.array([np.ones(len(x)), x, y, x * y, x ** 2, y ** 2, x ** 2 * y, x * y ** 2, x ** 2 * y ** 2,
                             x ** 3, y ** 3, x ** 3 * y, x * y ** 3, x ** 3 * y ** 2, x ** 2 * y ** 3,
                             x ** 3 * y ** 3]).T

    def _estimate_noise_level(self):
        """ estimate white image noise level """

        # print status
        self.sta.status_msg('Estimate white image noise level', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        M = np.mean(self.cfg.calibs[self.cfg.ptc_mean])
        lp_kernel = misc.create_gauss_kernel(length=M)
        if len(self._wht_img.shape) == 3:
            bw_img = rgb2gry(self._wht_img)[..., 0] if self._wht_img.shape[2] == 3 else self._wht_img[..., 0]
        else:
            bw_img = self._wht_img
        flt_img = convolve2d(bw_img, lp_kernel, 'same')

        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return np.std(bw_img-flt_img)

    @property
    def lfp_img(self):
        return self._lfp_img

    @property
    def wht_img(self):
        return self._wht_img
