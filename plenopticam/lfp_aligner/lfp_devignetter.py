from plenopticam.lfp_aligner.lfp_lensiter import LfpLensIter
from plenopticam import misc
from plenopticam.misc.type_checks import rint

import numpy as np

class LfpDevignetter(LfpLensIter):

    def __init__(self, *args, **kwargs):
        super(LfpDevignetter, self).__init__(*args, **kwargs)

        # threshold from white image intensity distribution (key to find balance between edges turning black or white)
        default_thresh = np.mean(self._wht_img/self._wht_img.max()) - np.std(self._wht_img/self._wht_img.max())
        self._th = kwargs['th'] if 'th' in kwargs else default_thresh

        # noise level for decision making whether division by raw image or fit values
        self._noise_lev = kwargs['noise_lev'] if 'noise_lev' in kwargs else 0

        self._lfp_div = np.zeros(self._lfp_img.shape)

    def main(self):

        # print status
        self.sta.status_msg('De-vignetting', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # based on provided noise level in white image
        if self._noise_lev < .5:
            # perform raw white image division (low noise)
            self.wht_img_divide()
        else:
            # perform fitted white micro image division (high noise)
            self.proc_lfp_img(self.patch_devignetting, msg='De-vignetting fit')

        # identify pixels requiring treatment from significantly large intensity variations
        self._lfp_div[self._lfp_div > self._lfp_img.max()] = self._lfp_img.max()
        lfp_vgn = self._lfp_div - self._lfp_img
        lfp_vgn[lfp_vgn < 0] = 0

        #import os
        #misc.save_img_file(self._lfp_img, file_path=os.path.join(os.getcwd(), 'lfp_img.bmp'))
        #misc.save_img_file(lfp_vgn, file_path=os.path.join(os.getcwd(), 'lfp_vgn.bmp'))

        thresh = np.mean(lfp_vgn) - np.std(lfp_vgn)
        lfp_vgn[lfp_vgn < thresh] = 0

        # add selected pixels to light-field image
        self._lfp_img += lfp_vgn*.3

        #misc.save_img_file(lfp_vgn, file_path=os.path.join(os.getcwd(), 'lfp_vgn_thresh.bmp'))
        #misc.save_img_file(self._lfp_img, file_path=os.path.join(os.getcwd(), 'lfp_out.bmp'))

        # print status
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

    def wht_img_divide(self, th=None):

        self._th = th if th is not None else self._th

        # equalize channel balance for white image channels
        self._wht_img = misc.eq_channels(self._wht_img)

        # normalize white image
        self._wht_img /= self._wht_img.max()

        # threshold dark areas to prevent large number after division
        self._wht_img[self._wht_img < self._th] = self._th

        # divide light-field image
        self._lfp_div = self._lfp_img / self._wht_img

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
        b = misc.yuv_conv(patch)[..., 0].flatten()

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

    def patch_devignetting(self, mic):

        # slice images
        margin = 1
        wht_win = self._extract_win(self._wht_img, mic, margin)
        lfp_win = self._extract_win(self._lfp_img, mic)
        div_win = self._extract_win(self._lfp_div, mic)

        # fit micro image
        if self._noise_lev > .5:
            _, weight_win = self.fit_patch(wht_win)
        else:
            weight_win = wht_win/wht_win.max()

        # thresholding (to prevent too large numbers in corrected image)
        th = .2
        weight_win[weight_win < th] = th

        # apply vignetting correction
        div_win += lfp_win / weight_win[margin:-margin, margin:-margin, ...]

        return True

    def _extract_win(self, img, mic, margin=0):
        win = img[rint(mic[0]) - self._C-margin:rint(mic[0]) + self._C+margin+1,
                  rint(mic[1]) - self._C-margin:rint(mic[1]) + self._C+margin+1]
        return win
