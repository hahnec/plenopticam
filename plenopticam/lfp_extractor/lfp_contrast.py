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
from plenopticam.misc.hist_eq import HistogramEqualizer
from plenopticam.lfp_aligner.cfa_processor import CfaProcessor


class LfpContrast(LfpViewpoints):

    def __init__(self, p_lo=None, p_hi=None, *args, **kwargs):
        super(LfpContrast, self).__init__(*args, **kwargs)

        self.p_lo = p_lo if p_lo is not None else 0.0
        self.p_hi = p_hi if p_hi is not None else 1.0

        self.ref_img = kwargs['ref_img'] if 'ref_img' in kwargs else self.central_view

        # internal variables
        self._contrast, self._brightness = (1., 1.)

    def main(self):

        # histogram equalization
        if self.cfg.params[self.cfg.opt_cont] and not self.sta.interrupt:
            obj = HistogramEqualizer(img=self._vp_img_arr)
            self._vp_img_arr = obj.lum_eq()
            #self.vp_img_arr = obj.awb_eq()
            del obj

        if self.cfg.params[self.cfg.opt_awb_] and not self.sta.interrupt:
            self.contrast_bal()

        # automatic saturation
        if self.cfg.params[self.cfg.opt_sat_] and not self.sta.interrupt:
            self.p_hi, self.p_lo = (1, 0)
            self.sat_bal()

        if self.vp_img_arr is not None:
            self.apply_ccm()
        #self._vp_img_arr = misc.data_proc.thresh_hist_stretch(self._vp_img_arr)
        #self._vp_img_arr = misc.Normalizer(self._vp_img_arr).type_norm()

        # clip to gray limits
        gray_opt = False
        if gray_opt:
            ref_img = misc.rgb2gray(self.central_view)
            p_lo, p_hi = (0.001, 99.999)
        else:
            ref_img = self.central_view
            p_lo, p_hi = (0.5, 99.9)

        min_perc = np.percentile(self.central_view, p_lo)
        max_perc = np.percentile(self.central_view, p_hi)
        self.vp_img_arr = misc.Normalizer(self.vp_img_arr, min=min_perc, max=max_perc).type_norm()

        # gamma correction
        gamma = 1#self.cfg.lfpimg['gam'] if self.cfg.lfpimg and 'gam' in self.cfg.lfpimg.keys() else 1 / 2.2
        gam_obj = misc.GammaConverter(img=self._vp_img_arr, gamma=gamma, profile='sRGB')
        #gam_obj.estimate_gamma(self.central_view)   # automatic gamma proved to yield better results
        self._vp_img_arr = gam_obj.correct_gamma()

        # cut-off lower end
        #self.thresh_hist_stretch(th=5e-11)    #2e-10

        # boost gamma
        #self.vp_img_arr /= self.vp_img_arr.max()
        #self.vp_img_arr **= .9

        #min_perc = np.percentile(self.central_view, 0.035)
        #max_perc = np.percentile(self.central_view, 99.95)
        #self.vp_img_arr = misc.Normalizer(self.vp_img_arr, min=min_perc, max=max_perc).type_norm()

        # boost gamma
        #self.vp_img_arr /= self.vp_img_arr.max()
        #self.vp_img_arr **= .7

    def thresh_hist_stretch(self, th=2e-10, bins=2**16-1):

        h = np.histogram(self.central_view, bins=bins)
        hn = h[0] / h[0].sum()
        x_vals = np.where(hn / len(hn) > th)[0] / bins

        hs = np.diff(h[0][::128] / h[0][::128].sum())
        s_vals = np.where(hs > 1.5e-4)[0] / (bins / 128)

        #img = misc.Normalizer(self.central_view.copy(), min=x_vals[1], max=self.central_view.max()).type_norm()
        self.proc_vp_arr(misc.Normalizer().type_norm, msg='Histogram crop', min=x_vals[1], max=1)

        return True

    def apply_ccm(self):

        # color matrix correction
        if 'ccm' in self.cfg.lfpimg.keys():

            # ccm mat selection
            if 'ccm_wht' in self.cfg.lfpimg:
                ccm_arr = self.cfg.lfpimg['ccm_wht']
            else:
                ccm_arr = np.array([2.4827811717987061, -1.1018080711364746, -0.38097298145294189,
                                    -0.36761483550071716, 1.6667767763137817, -0.29916191101074219,
                                    -0.18722048401832581, -0.73317205905914307, 1.9203925132751465])
                #ccm_arr = self.cfg.lfpimg['ccm']

            # normalize
            self.vp_img_arr /= self.vp_img_arr.max()

            sat_lev = 2 ** (-self.cfg.lfpimg['exp'])
            self.vp_img_arr *= sat_lev

            # transpose and flip ccm_mat for RGB order
            ccm_mat = np.reshape(ccm_arr, (3, 3)).T
            self._vp_img_arr = CfaProcessor().correct_color(self._vp_img_arr.copy(), ccm_mat=ccm_mat)

            # remove potential NaNs
            self._vp_img_arr[self._vp_img_arr < 0] = 0
            #self._vp_img_arr[self._vp_img_arr > sat_lev] = sat_lev
            #self._vp_img_arr /= sat_lev
            self._vp_img_arr /= self._vp_img_arr.max()

        return True

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

    def post_lum(self, ch=None):

        self.vp_img_arr = misc.Normalizer(self.vp_img_arr).uint16_norm()

        # channel selection
        ch = ch if ch is not None else 0
        ref_ch = misc.clr_spc_conv.yuv_conv(self.central_view)[..., ch]

        # define level limits
        self._min = np.percentile(ref_ch, self.p_lo*100)
        self._max = np.percentile(ref_ch, self.p_hi*100)

        self.proc_vp_arr(self.lum_norm, msg='Luminance normalization')

    def lum_norm(self, img, ch=None):

        # set default channel
        ch = ch if ch is not None else 0

        # RGB to YUV conversion
        img = misc.clr_spc_conv.yuv_conv(img)

        # normalization of Y (luminance channel)
        img = misc.Normalizer(img, min=self._min, max=self._max).uint16_norm()

        # YUV to RGB conversion
        img = misc.clr_spc_conv.yuv_conv(img, inverse=True)

        return img

    def auto_wht_bal(self, method=None, msg_opt=True):

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

    def sat_bal(self):

        self.set_stretch_hsv()
        self.proc_vp_arr(self.apply_stretch_hsv, msg='Color saturation')

        return True

    def set_stretch(self, ref_ch, val_lim=None):
        ''' according to https://stackoverflow.com/questions/9744255/instagram-lux-effect/9761841#9761841 '''

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
        ''' contrast and brightness rectification For provided RGB image '''

        img = img if img is not None else self.vp_img_arr
        #ch = ch if ch is not None else 0

        # convert to float
        f = img.astype(np.float32)

        # perform auto contrast (by default: "lum" channel only)
        img = self._contrast * f + self._brightness

        # clip to input extrema to remove contrast outliers
        img[img < f.min()] = f.min()
        img[img > f.max()] = f.max()

        return img

    def set_stretch_lum(self, img=None):

        img = img if img is not None else self.ref_img

        # use luminance channel for parameter analysis
        ref_img = misc.clr_spc_conv.yuv_conv(img)
        self.set_stretch(ref_ch=ref_img[..., 0])

    def apply_stretch_lum(self, img=None):
        ''' contrast and brightness rectification to luminance channel of provided RGB image '''

        # color model conversion
        img = misc.clr_spc_conv.yuv_conv(img) if img is not None else misc.clr_spc_conv.yuv_conv(self.vp_img_arr)

        # apply histogram stretching to luminance channel only
        img = self.apply_stretch(img=img, ch=0)

        # color model conversion
        img = misc.clr_spc_conv.yuv_conv(img, inverse=True)

        return img

    def set_stretch_hsv(self):

        # use luminance channel for parameter analysis
        ref_img = misc.clr_spc_conv.hsv_conv(self.ref_img)
        self.set_stretch(ref_ch=ref_img[..., 1]*(2**16-1))

    def apply_stretch_hsv(self, img):
        ''' saturation '''

        # color model conversion
        hsv = misc.clr_spc_conv.hsv_conv(img)

        # apply histogram stretching to saturation channel only
        hsv[..., 1] *= (2**16-1)
        self.apply_stretch(hsv, ch=1)
        hsv[..., 1] /= (2**16-1)

        # color model conversion
        rgb = misc.clr_spc_conv.hsv_conv(hsv, inverse=True)

        return rgb
