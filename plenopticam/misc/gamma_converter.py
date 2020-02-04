import numpy as np


class GammaConverter(object):

    def __init__(self, img=None, gamma=None, profile=None):

        self._img = np.asarray(img, dtype='float64')
        self._gam = 1. if gamma is None else gamma
        self._prf = profile

    def correct_gamma(self, img=None, gamma=None, profile=None):
        ''' perform gamma correction on image array '''

        img = self._img if img is None else np.asarray(img, dtype='float64')
        gam = self._gam if gamma is None else gamma
        prf = self._prf if profile is None else profile

        # normalize image
        img /= img.max()

        # perform gamma correction (if gamma != 1)
        img **= gam

        # convert to provided profile
        if prf == 'sRGB':
            new = np.zeros_like(img)
            new[img >= 0.0031308] = 1.055 * img[img >= 0.0031308] ** (5 / 12) - 0.055
            new[img < 0.0031308] = img[img < 0.0031308] * 12.92
            img = new

        return img

    def estimate_gamma(self, img: np.ndarray = None) -> float:

        img = self._img if img is None else img

        #self._gam = 1/np.log(img.mean())/np.log((img.max()-img.min())/2)
        #self._gam = -.3/np.log10(np.mean(img/img.max()))
        self._gam = 1/np.log(np.mean(img/img.max()))/np.log(.5)

        return self._gam

    @property
    def img(self):
        return self._img
