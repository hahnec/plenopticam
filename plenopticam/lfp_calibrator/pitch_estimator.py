#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2017 Christopher Hahne <info@christopherhahne.de>

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

# local imports
from plenopticam.misc import create_gauss_kernel
from plenopticam.misc.status import PlenopticamStatus

# external libs
import numpy as np
import scipy


class PitchEstimator(object):

    def __init__(self, img, cfg, sta=None, scale_val=1.625, CR=3):

        # input variables
        self._img = img
        self.cfg = cfg
        self.sta = sta if sta is not None else PlenopticamStatus()
        self._scale_val = scale_val
        self._CR = CR

        # internal variables
        self._scale_space = []
        self._top_img = None

        # output variables
        self._M = None

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # print status
        self.sta.status_msg('Estimate micro image size', self.cfg.params[self.cfg.opt_prnt])

        # take fractional central part of image
        self._crop_img(CR=self._CR)

        # create scale space
        self.create_scale_space()

        # find first maximum in scale space
        self.find_scale_max()

        # print "Progress: Done!"
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def _crop_img(self, CR=1):

        # crop image (for computational speed-up and smaller region of interest)
        S = self._img.shape[0]//2
        self._top_img = self._img[S-S//CR:S+S//CR-1, S-S//CR:S+S//CR-1].copy().astype(np.float64)

        # darken image edges to exclude micro images at border
        self._top_img *= create_gauss_kernel(length=S // CR * 2 - 1, sigma=S // CR // 2)

        return True

    def create_scale_space(self):

        # create Gaussian kernels with sigma=1 and sigma=sqrt(2)
        sig_one_kernel = create_gauss_kernel(length=9, sigma=1.)
        sig_sqrt_kernel = 1 * create_gauss_kernel(length=9, sigma=np.sqrt(2))

        # initialize scale space variables
        self._scale_space = []
        img_scale = scipy.signal.convolve2d(self._top_img, sig_one_kernel, 'same')   # initial scale

        # compute scale space by Gaussian filtering and down-sampling
        while (img_scale.shape[0] or img_scale.shape[1]) >= 3:

            # filter scaled image by Gaussian kernel with sigma=1
            gauss_img_one = (scipy.signal.convolve2d(img_scale, sig_one_kernel, 'same'))

            # append scaled image to pyramid
            self._scale_space.append(-(gauss_img_one-img_scale))  # negative for maximum detection

            # filter scaled image by Gaussian kernel with sigma=sqrt(2)
            gauss_img_two = (scipy.signal.convolve2d(gauss_img_one, sig_sqrt_kernel, 'same'))

            # append scaled image to pyramid
            self._scale_space.append(-(gauss_img_two-gauss_img_one))  # negative for maximum detection

            # down-sample to half the image resolution where Gaussian filters prevent from aliasing
            img_scale = gauss_img_two[::2, ::2]

            # check interrupt status
            if self.sta.interrupt:
                return False

        return True

    def get_maxima(self):
        """ compute list of maxima in scale space """

        return list(map(lambda x: np.max(x), self._scale_space))

    def find_scale_max(self, precision=.1):
        """ determine dominant scale size by analyzing maximum over scale space """

        maxima = np.array(self.get_maxima())

        if len(maxima) > 2:
            # find scale maximum (with sub-scale precision using interpolation)
            x_new = np.arange(0, len(maxima)-1, precision)
            i_fun = scipy.interpolate.interp1d(range(0, len(maxima)), maxima, kind='cubic')
            y_new = i_fun(x_new)
            y_new /= y_new.max()

            # start looking from first positive gradient to exclude early maxima on falling curve (false large scales)
            start = np.argmax(np.sign(np.gradient(y_new, int(1./precision))))

            # compute global and relative maxima in scale space
            val_max, arg_max = np.max(y_new[start:]), x_new[np.argmax(y_new[start:])+start]
            rel_max, arg_rel_max = y_new[min(scipy.signal.argrelmax(y_new[start:])[0])+start], \
                                   x_new[min(scipy.signal.argrelmax(y_new[start:])[0])+start]

            # use global maximum only if its y/x ratio is larger than that of relative to penalize "weak late maxima"
            scale_max = arg_max if val_max/arg_max > rel_max/arg_rel_max else arg_rel_max

        elif len(maxima) > 0:
            scale_max = max(maxima)
        else:
            scale_max = 0

        # compute corresponding DoG and Laplacian sigmas
        dog_sig = 2**(int(scale_max)//2) * np.sqrt(2**np.mod(scale_max, 2))
        lap_sig = dog_sig * 1.18

        # scale to get micro image size
        self._M = int(np.round(lap_sig * 4))

        return True

    @property
    def M(self):
        return self._M
