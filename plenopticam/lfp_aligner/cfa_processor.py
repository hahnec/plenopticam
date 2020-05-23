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


from plenopticam import misc
from plenopticam.cfg import PlenopticamConfig

# external libs
import numpy as np

try:
    from scipy.signal import medfilt
    from scipy.ndimage import median_filter
except ImportError:
    raise ImportError('Please install scipy package.')

try:
    from colour_demosaicing import demosaicing_CFA_Bayer_bilinear, demosaicing_CFA_Bayer_Malvar2004, demosaicing_CFA_Bayer_Menon2007
except ImportError:
    raise ImportError('Please install colour_demosaicing package')


class CfaProcessor(object):

    def __init__(self, bay_img=None, wht_img=None, cfg=None, sta=None):

        # input variables
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else misc.PlenopticamStatus()
        self._bay_img = bay_img.astype('float32') if isinstance(bay_img, np.ndarray) else None
        self._wht_img = wht_img.astype('float32') if isinstance(wht_img, np.ndarray) else None

        self._bit_pac = self.cfg.lfpimg['bit'] if 'bit' in self.cfg.lfpimg else 10
        self._gains = self.cfg.lfpimg['awb'] if 'awb' in self.cfg.lfpimg else [1, 1, 1, 1]
        self._bay_pat = self.cfg.lfpimg['bay'] if 'bay' in self.cfg.lfpimg else None

        # output variables
        self._rgb_img = np.array([])

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # apply auto white balance gains while considering image highlights
        self.safe_bayer_awb()

        # debayer to rgb image
        if 'bay' in self.cfg.lfpimg.keys() and len(self._bay_img.shape) == 2:
            self.bay2rgb(2)

        # convert to uint16
        self._rgb_img = misc.Normalizer(self._rgb_img).uint16_norm()

        return True

    def bay2rgb(self, method=2):

        # print status
        self.sta.status_msg('Debayering', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # Bayer to RGB conversion
        if method == 0:
            self._rgb_img = demosaicing_CFA_Bayer_bilinear(self._bay_img, self.cfg.lfpimg['bay'])
        elif method == 1:
            self._rgb_img = demosaicing_CFA_Bayer_Malvar2004(self._bay_img, self.cfg.lfpimg['bay'])
        else:
            self._rgb_img = demosaicing_CFA_Bayer_Menon2007(self._bay_img, self.cfg.lfpimg['bay'])

        # normalize image
        min = np.percentile(self._rgb_img, 0.05)
        max = np.max(self.rgb_img)
        self._rgb_img = misc.Normalizer(self._rgb_img, min=min, max=max).type_norm()

        # update status message
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def _reshape_bayer(self):

        if len(self._bay_img.shape) == 2:
            # reshape bayer image to 4 channels in third dimension (G, R, B, G)
            self._bay_img = np.dstack((self._bay_img[0::2, 0::2], self._bay_img[0::2, 1::2],
                                       self._bay_img[1::2, 0::2], self._bay_img[1::2, 1::2]))

        elif len(self._bay_img.shape) == 3:
            if self._bay_img.shape[2] == 4:
                # reshape 4 channel bayer image to 2D bayer image
                arr, self._bay_img = self._bay_img, np.zeros(np.array(self._bay_img.shape[:2])*2)
                self._bay_img[0::2, 0::2] = arr[..., 0]
                self._bay_img[0::2, 1::2] = arr[..., 1]
                self._bay_img[1::2, 0::2] = arr[..., 2]
                self._bay_img[1::2, 1::2] = arr[..., 3]

        return True

    def _reshape_white(self):

        if self._wht_img is not None:
            if len(self._wht_img.shape) == 2:
                # reshape bayer image to 4 channels in third dimension
                self._wht_img = np.dstack((self._wht_img[0::2, 0::2], self._wht_img[0::2, 1::2],
                                           self._wht_img[1::2, 0::2], self._wht_img[1::2, 1::2]))

            elif len(self._wht_img.shape) == 3:
                if self._wht_img.shape[2] == 4:
                    # reshape 4 channel bayer image to 2D bayer image
                    arr, self._wht_img = self._wht_img, np.zeros(np.array(self._wht_img.shape[:2])*2)
                    self._wht_img[0::2, 0::2] = arr[..., 0]
                    self._wht_img[0::2, 1::2] = arr[..., 1]
                    self._wht_img[1::2, 0::2] = arr[..., 2]
                    self._wht_img[1::2, 1::2] = arr[..., 3]

        return True

    @property
    def rgb_img(self):
        return self._rgb_img.copy()

    def apply_awb(self, img_arr=None, bay_pat=None, gains=None):
        """ white balance from gains """

        img_arr = self._bay_img if img_arr is None else img_arr
        bay_pat = self._bay_pat if bay_pat is None else bay_pat
        gains = self._gains if gains is None else gains

        if len(img_arr.shape) == 3:

            img_arr[..., 0] *= gains[0]             # red channel
            img_arr[..., 1] *= gains[1]             # green channel
            img_arr[..., 2] *= gains[2]             # blue channel

        elif len(img_arr.shape) == 2 and bay_pat == "GRBG":

            img_arr[0::2, 0::2] *= gains[0]         # green-red channel
            img_arr[0::2, 1::2] *= gains[1]         # red channel
            img_arr[1::2, 0::2] *= gains[2]         # blue channel
            img_arr[1::2, 1::2] *= gains[3]         # green-blue channel

        elif len(img_arr.shape) == 2 and bay_pat == "BGGR":

            img_arr[0::2, 0::2] *= gains[0]         # blue channel
            img_arr[0::2, 1::2] *= gains[1]         # green-blue channel
            img_arr[1::2, 0::2] *= gains[2]         # green-red channel
            img_arr[1::2, 1::2] *= gains[3]         # red channel

        return img_arr

    def _correct_bayer_highlights(self, gains=None):
        """ inspired by CLIM_VSENSE highlight correction """

        self._gains = self._gains if gains is None else gains

        bay_img = self._bay_img.copy()
        wht_img = np.ones(self._bay_img.shape) if self._wht_img is None else self._wht_img

        fact = self._gains.max()
        ThSatCol = .99

        # Determine the component with lowest value (the last one to saturate).
        min_sat, min_idx = bay_img.min(2), bay_img.argmin(2)
        min_sat_bal = min_sat * self._gains[min_idx]

        # weights
        min_sat = min_sat * wht_img.mean(2)
        min_sat[min_sat > 1] = 1
        min_sat **= 2

        for i in range(4):
            ref_img = np.divide(ThSatCol, wht_img[..., i], out=np.ones_like(wht_img[..., i])*float('Inf'), where=wht_img[..., i]!=0)
            ref_img[~np.isfinite(ref_img)] = 0
            ch_idxs = np.nonzero(bay_img[..., i] > ref_img)
            inm_img = (min_sat_bal*(1-min_sat) + bay_img[..., i]*fact * min_sat) / self._gains[i]
            bay_img[..., i][ch_idxs] = np.maximum.reduce([bay_img[..., i][ch_idxs], inm_img[ch_idxs]])

        self._bay_img = bay_img

        return True

    @staticmethod
    def desaturate_clipped(img_arr, gains=None):

        # skip process if gains not set
        if gains is None:
            return img_arr

        # original channel intensities
        orig = img_arr / gains

        # identify clipped pixels
        beta = orig / np.amax(orig, axis=2)[..., np.newaxis]
        weights = beta * gains
        weights[weights < 1] = 1
        mask = np.zeros(orig.shape[:2])
        mask[np.amax(orig, axis=2) >= orig.max()] = 1

        # de-saturate clipped values
        img_arr[mask > 0] /= weights[mask > 0]

        return img_arr

    @staticmethod
    def correct_color(img, ccm_mat=np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])):
        """ color correction according to http://www.imatest.com/docs/colormatrix/ using Case 1 """

        # perform color correction
        img_ccm = np.dot(np.vstack(img), ccm_mat).reshape(img.shape)

        return img_ccm

    def safe_bayer_awb(self):

        self._reshape_bayer()
        self._reshape_white()

        self.set_gains(self.cfg.lfpimg['awb'])
        self._correct_bayer_highlights()

        self._reshape_bayer()
        self._reshape_white()

        self.apply_awb()
        self._bay_img[self._bay_img < 0] = 0

        if 'exp' in self.cfg.lfpimg:
            exp_bias = self.cfg.lfpimg['exp']
            max_lum = 2**(-exp_bias)
            self._bay_img = self.soft_clipping(self._bay_img/max_lum, 7)*max_lum

    def soft_clipping(self, img, max):

        b = np.exp(max)
        return np.log((1+b)/(1+b*np.exp(-max*img)))/np.log(1+b)

    def set_gains(self, gains=None):

        # skip process if gains not set
        if gains is not None:
            if len(self._bay_img.shape) == 2 or len(self._bay_img.shape) == 3 and self._bay_img.shape[-1] == 4:
                if self._bay_pat == "GRBG":
                    self._gains = np.array([gains[2], gains[1], gains[0], gains[3]])
                elif self._bay_pat == "BGGR":
                    self._gains = np.array([gains[0], gains[2], gains[3], gains[1]])
                else:
                    return None
            elif len(self._bay_img.shape) == 3 and self._bay_img.shape[-1] == 3:
                self._gains = np.array([gains[1], (gains[2] + gains[3]) / 2, gains[0]])
            else:
                return None
        else:
            return None

        return self._gains
