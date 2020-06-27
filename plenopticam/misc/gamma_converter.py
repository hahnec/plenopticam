import numpy as np
from color_space_converter import rgb2gry


class GammaConverter(object):

    def __init__(self, img=None, gamma=None, profile=None):

        self._img = np.asarray(img, dtype='float64')
        self._gam = 1. if gamma is None else gamma
        self._prf = profile

    def correct_gamma(self, img=None, gamma=None, profile=None):
        """ perform gamma correction on image array """

        img = self._img if img is None else np.asarray(img, dtype='float64')
        gam = self._gam if gamma is None else gamma
        prf = self._prf if profile is None else profile

        # normalize image
        img /= img.max()

        # perform gamma correction (if gamma != 1)
        img **= gam

        # convert to provided profile
        if prf == 'sRGB':
            img = self.srgb_conv(img)

        return img

    @staticmethod
    def srgb_conv(img, inverse=None):
        """ perform gamma correction according to sRGB standard """

        new = np.zeros_like(img)
        if inverse:
            new[img <= 0.04045] = img[img <= 0.04045] / 12.92
            new[img > 0.04045] = ((img[img > 0.04045] + 0.055) / 1.055) ** (12 / 5)
        else:
            new[img >= 0.0031308] = 1.055 * img[img >= 0.0031308] ** (5 / 12) - 0.055
            new[img < 0.0031308] = img[img < 0.0031308] * 12.92

        return new

    def estimate_gamma(self, img: np.ndarray = None) -> float:
        """ set gamma value"""

        img = self._img if img is None else np.asarray(img, dtype='float64')

        # extract luminance
        lum = rgb2gry(img)

        # normalize
        lum /= lum.max()

        self._gam = 1/np.log(np.mean(lum/lum.max()))/np.log(.5)

        return self._gam

    @property
    def img(self):
        return self._img
