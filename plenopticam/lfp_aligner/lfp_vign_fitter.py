from plenopticam.lfp_aligner.lfp_lensiter import LfpLensIter
from plenopticam import misc
from plenopticam.misc.type_checks import rint

import numpy as np

class LfpVignFitter(LfpLensIter):

    def __init__(self, *args, **kwargs):
        super(LfpVignFitter, self).__init__(*args, **kwargs)

    def main(self):

        self.proc_lfp_img(self.patch_devignetting, msg='Devignetting process')

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

        # thresholding (to prevent too large numbers in corrected image)
        th = .4 if th is None else th
        weight_win[weight_win < th] = th

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

        # yuv_img = misc.yuv_conv(patch)
        # yuv_img[..., 0] = yuv_img[..., 0] / surf_z
        patch /= f  # normalize f?

        return patch  # misc.yuv_conv(yuv_img, inverse=True)

    def patch_devignetting(self, mic):

        # slice images
        wht_win = self._wht_img[rint(mic[0]) - self._C - 1:rint(mic[0]) + self._C + 2,
                 rint(mic[1]) - self._C - 1: rint(mic[1]) + self._C + 2]

        lfp_win = self._lfp_img[rint(mic[0]) - self._C - 1:rint(mic[0]) + self._C + 2,
                 rint(mic[1]) - self._C - 1: rint(mic[1]) + self._C + 2]


        _, weight_win = self.fit_patch(wht_win)

        # apply vignetting correction
        lfp_win /= weight_win

        return lfp_win
