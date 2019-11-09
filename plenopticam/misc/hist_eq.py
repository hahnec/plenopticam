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


import numpy as np

from plenopticam import misc


class HistogramEqualizer(object):

    def __init__(self, img=None, bin_num=None, ch=None, **kwargs):

        self._ref_img = None if img is None else img
        self._bin_num = self.set_bin_num() if bin_num is None else bin_num
        self._ch = 0 if ch is None else ch

        self._vp_img_arr = kwargs['vp_img_arr'] if 'vp_img_arr' in kwargs else None

    def set_bin_num(self):

        dtype = self._ref_img.dtype.__str__()
        if dtype.startswith('float'):
            lim_max = np.finfo(np.dtype(dtype)).max
        elif dtype.startswith(('int', 'uint')):
            lim_max = np.iinfo(np.dtype(dtype)).max
        else:
            lim_max = 1.0

        return lim_max if lim_max is not None and lim_max < 2**16-1 else 2**16-1

    def cdf_from_img(self, ch=None):

        # channel selection
        self._ch = self._ch if ch is None else ch
        img_ch = self._ref_img[..., self._ch]

        # get image histogram
        imhist, self._bins = np.histogram(img_ch.flatten(), np.arange(self._bin_num))
        self._cdf = imhist.cumsum()  # cumulative distribution
        self._cdf = self._bin_num * self._cdf / self._cdf[-1]  # normalize

        return True

    def cdf_spec(self, type='linear', param=1., flip=False):

        # set linear function as default
        des_hist = np.linspace(0, 1, self._bin_num)

        # modify function shape according to provided parameters
        if type == 'linear':
            des_hist *= param
            des_hist -= (param-1)/2 if param != 1 and param != 0 else 0
            # clip to input extrema to remove contrast outliers
            des_hist[des_hist < 0] = 0
            des_hist[des_hist > 1] = 1
        elif type == 'exp' or type == 's-curve':
            des_hist **= param
            if flip:
                des_hist = 1-des_hist[::-1]
            if type == 's-curve':
                lower_pt = (des_hist[::2]/2)[:-1]
                des_hist = np.concatenate((lower_pt, 1-lower_pt[::-1]))
                des_hist = np.append(des_hist, 1) if len(des_hist)+1 == len(self._bins) else des_hist
        elif type == 'gaussian':
            mu = des_hist.max() / 2
            sig = 1/param
            des_hist = 1. / (np.sqrt(2. * np.pi) * sig) * np.exp(-np.power((des_hist - mu) / sig, 2.) / 2)
            des_hist /= des_hist.sum()
            des_hist = des_hist.cumsum()

        # normalize to maximum value of data type
        des_hist *= self._bin_num

        # convert to integer if required
        if self._ref_img.dtype.__str__().startswith(('int', 'uint')):
            des_hist = np.round(des_hist).astype(self._ref_img.dtype)

        return des_hist

    def correct_histeq(self, ch=None):

        # channel selection
        self._ch = self._ch if ch is None else ch
        img_ch = self._ref_img[..., self._ch]

        # use specified histogram and cdf to generate desired histogram
        des_cdf = self.cdf_spec(type='gaussian', param=3, flip=False)
        new_img = np.interp(img_ch.flatten(), des_cdf[:-1], self._cdf)

        # reconstruct new image
        new_img = new_img.reshape(self._ref_img[..., self._ch].shape)
        #interp_vals[src_idxs].reshape(src[..., ch].shape)
        self._ref_img[..., self._ch] = new_img

        return True

    def lum_eq(self):

        # RGB/YUV color conversion
        self._ref_img = misc.yuv_conv(self._ref_img)

        # create cumulative distribution function of reference image
        self.cdf_from_img()

        # histogram mapping using cumulative distribution function
        self.correct_histeq()

        # YUV/RGB color conversion
        return misc.yuv_conv(self._ref_img, inverse=True)

    def uv_eq(self):

        # RGB/YUV color conversion
        self._ref_img = misc.yuv_conv(self._ref_img)

        for i in range(1, self._ref_img.shape[-1]):

            # create cumulative distribution function of reference image
            self.cdf_from_img(ch=i)

            # histogram mapping using cumulative distribution function
            self.correct_histeq(ch=i)

        # YUV/RGB color conversion
        return misc.yuv_conv(self._ref_img, inverse=True)

    def awb_eq(self):

        # iterate through all colour channels
        for i in range(self._ref_img.shape[-1]):

            # create cumulative distribution function of reference image
            self.cdf_from_img(ch=i)

            # histogram mapping using cumulative distribution function
            self.correct_histeq(ch=i)

        return self._ref_img
