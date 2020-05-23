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
from plenopticam.lfp_extractor import LfpViewpoints
from color_space_converter import hsv_conv, yuv_conv, rgb2gry


class LfpContrast(LfpViewpoints):

    def __init__(self, p_lo=None, p_hi=None, *args, **kwargs):
        super(LfpContrast, self).__init__(*args, **kwargs)

        self.p_lo = p_lo if p_lo is not None else 0.0
        self.p_hi = p_hi if p_hi is not None else 1.0

        self.ref_img = kwargs['ref_img'] if 'ref_img' in kwargs else self.central_view

        # internal variables
        self._contrast, self._brightness = (1., 1.)

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # auto contrast balance
        if self.cfg.params[self.cfg.opt_cont] and not self.sta.interrupt:
            self.p_hi, self.p_lo = (1, 0)
            self.con_bal()
        # auto white balance
        if self.cfg.params[self.cfg.opt_awb_] and not self.sta.interrupt:
            self.p_hi, self.p_lo = (1, 0)
            self.wht_bal()
        # auto saturation
        if self.cfg.params[self.cfg.opt_sat_] and not self.sta.interrupt:
            self.p_hi, self.p_lo = (1, 0)
            self.sat_bal()

        # automatic histogram alignment
        self._vp_img_arr = self.auto_hist_align(img=self._vp_img_arr, ref_img=self.central_view, opt=True)

        # gamma correction
        self._vp_img_arr = misc.GammaConverter().srgb_conv(img=self._vp_img_arr)

        return True

    def con_bal(self):

        # find extrema from reference image
        self.ref_img = yuv_conv(self.central_view)[..., 0]
        max = self.ref_img.max()
        min = self.ref_img.min()

        # convert to yuv space
        self.proc_vp_arr(yuv_conv, msg='Convert to YUV')

        # boost luminance channel
        self.sta.status_msg(msg='Contrast balance', opt=self.cfg.params[self.cfg.opt_prnt])
        self._vp_img_arr[..., 0] = misc.Normalizer(self._vp_img_arr[..., 0]).type_norm(max=max, min=min)
        self.sta.progress(100, opt=self.cfg.params[self.cfg.opt_prnt])

        # convert to rgb space
        self.proc_vp_arr(yuv_conv, inverse=True, msg='Convert to RGB')

        return True

    def sat_bal(self):

        # convert to hsv space
        self.proc_vp_arr(hsv_conv, msg='Convert to HSV')

        # boost saturation channel
        self.sta.status_msg(msg='Saturation balance', opt=self.cfg.params[self.cfg.opt_prnt])
        self.vp_img_arr[..., 1] *= 1.1
        self.sta.progress(100, opt=self.cfg.params[self.cfg.opt_prnt])

        # convert to rgb space
        self.proc_vp_arr(hsv_conv, inverse=True, msg='Convert to RGB')

        return True

    def wht_bal(self, method=None, msg_opt=True):

        # status update
        if msg_opt:
            msg = 'Auto white balance' if self.p_hi != 1 else 'Color adjustment'
            self.sta.status_msg(msg=msg, opt=self.cfg.params[self.cfg.opt_prnt])
            self.sta.progress(0, opt=self.cfg.params[self.cfg.opt_prnt])

        ch_num = self.vp_img_arr.shape[-1] if len(self.vp_img_arr.shape) > 4 else 3
        for i in range(ch_num):
            if method is None:

                # channel selection
                ref_ch = self.ref_img[..., i]
                img_ch = self.vp_img_arr[..., i]

                # define level limits
                min = np.percentile(ref_ch, self.p_lo*100)
                max = np.percentile(ref_ch, self.p_hi*100)

                # normalization of color channel
                self.vp_img_arr[..., i] = misc.Normalizer(img_ch, min=min, max=max).uint16_norm()

            else:
                # brightness and contrast method
                self.set_stretch(ref_ch=self.ref_img[..., i])
                self.apply_stretch(ch=i)

            # status update
            if msg_opt:
                self.sta.progress((i+1)/ch_num*100, opt=self.cfg.params[self.cfg.opt_prnt])

        return True

    def channel_bal(self):

        # status update
        self.sta.status_msg(msg='Contrast balance', opt=self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, opt=self.cfg.params[self.cfg.opt_prnt])

        ch_num = self.vp_img_arr.shape[-1] if len(self.vp_img_arr.shape) > 4 else 3

        min = float('Inf')
        max = 0.
        for i in range(ch_num):
            min = np.min([min, np.percentile(self.ref_img[..., i], self.p_lo * 100)])
            max = np.max([max, np.percentile(self.ref_img[..., i], self.p_hi * 100)])

        # normalization of color channel
        self.vp_img_arr = misc.Normalizer(self.vp_img_arr, min=min, max=max).uint16_norm()

        # status update
        self.sta.progress(100, opt=self.cfg.params[self.cfg.opt_prnt])

        return True

    def stretch_contrast(self):

        # estimate contrast and brightness via least-squares method
        self.set_stretch(ref_ch=yuv_conv(self.central_view)[..., 0])

        self.proc_vp_arr(yuv_conv, msg='Convert to YUV')
        self.proc_vp_arr(self.apply_stretch, ch=0, msg='Contrast balance')
        self.proc_vp_arr(yuv_conv, inverse=True, msg='Convert to RGB')

        # status update
        self.sta.progress(100, opt=self.cfg.params[self.cfg.opt_prnt])

        return True

    def set_stretch(self, ref_ch, val_lim=None):
        """ according to https://stackoverflow.com/questions/9744255/instagram-lux-effect/9761841#9761841 """

        # estimate contrast und brightness parameters (by default: first channel only)
        val_lim = 2**16-1 if not val_lim else val_lim
        h = np.histogram(ref_ch, bins=val_lim)[0]
        H = np.cumsum(h)/float(np.sum(h))
        try:
            px_lo = self.find_x_given_y(self.p_lo, np.arange(val_lim), H)
            px_hi = self.find_x_given_y(self.p_hi, np.arange(val_lim), H)
        except:
            px_lo = 0
            px_hi = val_lim
        A = np.array([[px_lo, 1], [px_hi, 1]])
        b = np.array([0, val_lim])
        self._contrast, self._brightness = np.dot(np.linalg.inv(A), b)

        return self._contrast, self._brightness

    @staticmethod
    def find_x_given_y(value, x, y, tolerance=1e-4):

        i = 0
        iter_max = 10
        arr = np.array([])
        while arr.size == 0 and i != iter_max:
            arr = np.array([(xi, yi) for (xi, yi) in zip(x, y) if abs(yi - value) <= tolerance])
            i += 1
            tolerance = 10**(-4+i)

        found_y = np.mean(arr.T[0]) if i != iter_max else round(value)

        return found_y

    def apply_stretch(self, img=None, ch=None):
        """ contrast and brightness rectification for provided RGB image """

        img = img if img is not None else self.vp_img_arr
        ch = ch if ch is not None else 0

        # convert to float
        f = img.astype(np.float64)

        # perform auto contrast (by default: "lum" channel only)
        img[..., ch] = self._contrast * f[..., ch] + self._brightness

        # clip to input extrema to remove contrast outliers
        #img[img < f.min()] = f.min()
        #img[img > f.max()] = f.max()

        return img

    def set_stretch_hsv(self):

        # use luminance channel for parameter analysis
        ref_img = hsv_conv(self.ref_img)
        self.set_stretch(ref_ch=ref_img[..., 1]*(2**16-1))

    def apply_stretch_hsv(self, img):
        ''' saturation '''

        # color model conversion
        hsv = hsv_conv(img)

        # apply histogram stretching to saturation channel only
        hsv[..., 1] *= (2**16-1)
        self.apply_stretch(hsv, ch=1)
        hsv[..., 1] /= (2**16-1)

        # color model conversion
        rgb = hsv_conv(hsv, inverse=True)

        return rgb

    @staticmethod
    def auto_hist_align(img, ref_img, opt=None):

        if opt:
            p_lo, p_hi = (0.005, 99.9)#(0.001, 99.999)
            min_perc = np.percentile(rgb2gry(ref_img), p_lo)
            max_perc = np.percentile(ref_img, p_hi)
        else:
            p_lo, p_hi = (0.5, 99.9)
            min_perc = np.percentile(ref_img, p_lo)
            max_perc = np.percentile(ref_img, p_hi)

        img = misc.Normalizer(img, min=min_perc, max=max_perc).type_norm()

        return img

    def thresh_hist_stretch(self, th=2e-10, bins=2**16-1):

        h = np.histogram(self.central_view, bins=bins)
        hn = h[0] / h[0].sum()
        x_vals = np.where(hn / len(hn) > th)[0] / bins

        hs = np.diff(h[0][::128] / h[0][::128].sum())
        s_vals = np.where(hs > 1.5e-4)[0] / (bins / 128)

        #img = misc.Normalizer(self.central_view.copy(), min=x_vals[1], max=self.central_view.max()).type_norm()
        self.proc_vp_arr(misc.Normalizer().type_norm, msg='Histogram crop', min=x_vals[1], max=1)

        return True

    def post_lum(self, ch=None):

        self.vp_img_arr = misc.Normalizer(self.vp_img_arr).uint16_norm()

        # channel selection
        ch = ch if ch is not None else 0
        ref_ch = yuv_conv(self.central_view)[..., ch]

        # define level limits
        self._min = np.percentile(ref_ch, self.p_lo*100)
        self._max = np.percentile(ref_ch, self.p_hi*100)

        self.proc_vp_arr(self.lum_norm, msg='Luminance normalization')

    def lum_norm(self, img, ch=None):

        # set default channel
        ch = ch if ch is not None else 0

        # RGB to YUV conversion
        img = yuv_conv(img)

        # normalization of Y (luminance channel)
        img = misc.Normalizer(img[..., ch], min=self._min, max=self._max).uint16_norm()

        # YUV to RGB conversion
        img = yuv_conv(img, inverse=True)

        return img
