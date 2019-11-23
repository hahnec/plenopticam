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


class LfpContrast(LfpViewpoints):

    def __init__(self, p_lo=None, p_hi=None, *args, **kwargs):
        super(LfpContrast, self).__init__(*args, **kwargs)

        self.p_lo = p_lo if p_lo is not None else 0.0
        self.p_hi = p_hi if p_hi is not None else 1.0

        # internal variables
        self._contrast, self._brightness = (1., 1.)

    def contrast_bal(self):

        # status update
        self.sta.status_msg(msg='Contrast balance', opt=self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, opt=self.cfg.params[self.cfg.opt_prnt])

        # estimate contrast and brightness via least-squares method
        self.set_stretch_lum(img=self.vp_img_arr)

        # apply estimated brightness and contrast levels to viewpoint array
        self.vp_img_arr = self.apply_stretch_lum(img=self.vp_img_arr)

        # status update
        self.sta.progress(100, opt=self.cfg.params[self.cfg.opt_prnt])

    def post_lum(self):

        self.proc_vp_arr(self.stretch_lum_vp, ch=0, msg='contrast eq')

    def stretch_lum_vp(self, img, ch=None):

        ch = ch if ch is not None else 0

        img = misc.clr_spc_conv.yuv_conv(img)
        #img = misc.hsv_conv(img)
        obj = misc.HistogramEqualizer(img=img, ch=ch)
        obj.cdf_from_img()
        obj.correct_histeq()
        img = obj._ref_img
        del obj
        img = misc.clr_spc_conv.yuv_conv(img, inverse=True)

        return img

    def auto_wht_bal(self, method=None):

        # status update
        self.sta.status_msg(msg='Auto white balance', opt=self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, opt=self.cfg.params[self.cfg.opt_prnt])

        ch_num = self.vp_img_arr.shape[-1] if len(self.vp_img_arr.shape) > 4 else 1
        for i in range(ch_num):
            if method is None:
                ref_ch = self.central_view[..., i]
                img_ch = self.vp_img_arr[..., i]
                self.vp_img_arr[..., i] = misc.Normalizer(img=img_ch,
                                                          min=np.percentile(ref_ch, self.p_lo*100),
                                                          max=np.percentile(ref_ch, self.p_hi*100)).uint16_norm()
            else:
                self.set_stretch(ref_ch=self.central_view[..., i])
                self.apply_stretch(ch=i)

            # status update
            self.sta.progress((i+1)/ch_num*100, opt=self.cfg.params[self.cfg.opt_prnt])

        return True

    def sat_bal(self):

        self.set_stretch_hsv()
        self.proc_vp_arr(self.apply_stretch_hsv, msg='Color saturation')

        return True

    def set_stretch(self, ref_ch, val_lim=None):
        ''' according to https://stackoverflow.com/questions/9744255/instagram-lux-effect/9761841#9761841 '''

        # estimate contrast und brightness parameters (by default: first channel only)
        val_lim = 2**16-1 if not val_lim else val_lim
        h = np.histogram(ref_ch, bins=np.arange(val_lim))[0]
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
        ''' contrast and brightness rectification For provided RGB image '''

        img = img if img is not None else self.vp_img_arr
        ch = ch if ch is not None else 0

        # convert to float
        f = img[..., ch].astype(np.float32)

        # perform auto contrast (by default: "value" channel only)
        img[..., ch] = self._contrast * f + self._brightness

        # clip to input extrema to remove contrast outliers
        img[..., ch][img[..., ch] < f.min()] = f.min()
        img[..., ch][img[..., ch] > f.max()] = f.max()

        return img

    def set_stretch_lum(self, img=None):

        img = img if img is not None else self.central_view

        # use luminance channel for parameter analysis
        ref_img = misc.clr_spc_conv.yuv_conv(img)
        self.set_stretch(ref_ch=ref_img[..., 0])

    def apply_stretch_lum(self, img=None):
        ''' contrast and brightness rectification to luminance channel of provided RGB image '''

        img = img if img is not None else self.vp_img_arr

        # color model conversion
        img = misc.clr_spc_conv.yuv_conv(img) if img is not None else misc.clr_spc_conv.yuv_conv(self.vp_img_arr)

        # apply histogram stretching to luminance channel only
        img = self.apply_stretch(img=img, ch=0)

        # color model conversion
        img = misc.clr_spc_conv.yuv_conv(img, inverse=True)

        return img

    def set_stretch_hsv(self):

        # use luminance channel for parameter analysis
        ref_img = misc.clr_spc_conv.hsv_conv(self.central_view)
        self.set_stretch(ref_ch=ref_img[..., 1]*(2**16-1))

    def apply_stretch_hsv(self, img):
        ''' contrast and brightness rectification to luminance channel of provided RGB image '''

        # color model conversion
        hsv = misc.clr_spc_conv.hsv_conv(img)

        # apply histogram stretching to saturation channel only
        hsv[..., 1] *= (2**16-1)
        self.apply_stretch(hsv, ch=1)
        hsv[..., 1] /= (2**16-1)

        # color model conversion
        rgb = misc.clr_spc_conv.hsv_conv(hsv, inverse=True)

        return rgb
