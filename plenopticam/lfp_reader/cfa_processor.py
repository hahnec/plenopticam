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

    def __init__(self, img_buf, shape, cfg, sta=None):

        # input variables
        self.cfg = cfg
        self.sta = sta if sta is not None else misc.PlenopticamStatus()
        self._shape = shape
        self._img_buf = img_buf
        self._bit_pac = cfg.lfpimg['bit'] if 'bit' in cfg.lfpimg.keys() else 10

        # internal variables
        self._bay_img = None

        # output variables
        self._rgb_img = None

    def main(self):

        # compose bayer image from input image buffer
        self.comp_bayer()

        # auto white balance
        if 'awb' in self.cfg.lfpimg.keys():
            self._bay_img = self.correct_awb(self._bay_img, self.cfg.lfpimg['bay'], gains=self.cfg.lfpimg['awb'])
            self._reshape_bayer()
            self._bay_img = self.desaturate_clipped(self._bay_img, gains=self.cfg.lfpimg['awb'])
            self._reshape_bayer()

        from plenopticam.lfp_extractor.lfp_hotpixels import LfpHotPixels
        obj = LfpHotPixels(cfg=self.cfg, sta=self.sta)
        self._bay_img = obj.hotpixel_candidates_bayer(bay_img=self._bay_img.copy(), n=9, sig_lev=3.5)

        # debayer to rgb image
        if 'bay' in self.cfg.lfpimg.keys() and len(self._bay_img.shape) == 2:
            self.bay2rgb()

        # color matrix correction
        if 'ccm' in self.cfg.lfpimg.keys():
            self._rgb_img = self.correct_color(self._rgb_img, ccm_mat=np.reshape(self.cfg.lfpimg['ccm'], (3, 3)).T)

        # perform gamma correction
        if 'gam' in self.cfg.lfpimg.keys():
            self._rgb_img = self.correct_gamma(self._rgb_img, gamma=self.cfg.lfpimg['gam'])

        # convert to uint16
        self._rgb_img = misc.Normalizer(self._rgb_img).uint16_norm()

        return True

    def comp_bayer(self):
        ''' inspired by Nirav Patel's lfptools '''

        # initialize column vector for bayer image array
        self._bay_img = np.zeros(self._shape[0]*self._shape[1], dtype=np.uint16)

        if self._bit_pac == 10:

            t0 = np.array(self._img_buf[0::5], 'uint16')
            t1 = np.array(self._img_buf[1::5], 'uint16')
            t2 = np.array(self._img_buf[2::5], 'uint16')
            t3 = np.array(self._img_buf[3::5], 'uint16')
            t4 = np.array(self._img_buf[4::5], 'uint16')

            t0 = t0 << 2
            t1 = t1 << 2
            t2 = t2 << 2
            t3 = t3 << 2

            t0 += (t4 & 0x03)
            t1 += (t4 & 0x0C) >> 2
            t2 += (t4 & 0x30) >> 4
            t3 += (t4 & 0xC0) >> 6

            self._bay_img = np.empty((4*t0.size,), dtype=t0.dtype)
            self._bay_img[0::4] = t0        # green-red
            self._bay_img[1::4] = t1        # red
            self._bay_img[2::4] = t2        # green-blue
            self._bay_img[3::4] = t3        # blue

        elif self._bit_pac == 12:

            t0 = np.array(self._img_buf[0::3], 'uint16')
            t1 = np.array(self._img_buf[1::3], 'uint16')
            t2 = np.array(self._img_buf[2::3], 'uint16')

            a0 = (t0 << 4) + ((t1 & 0xF0) >> 4)
            a1 = ((t1 & 0x0F) << 8) + t2

            self._bay_img = np.empty((2*a0.size,), dtype=t0.dtype)
            self._bay_img[0::4] = a0[0::2]  # blue
            self._bay_img[2::4] = a0[1::2]  # red
            self._bay_img[1::2] = a1        # green

        # rearrange column vector to 2-D image array
        self._bay_img = np.reshape(self._bay_img, (self._shape[1], self._shape[0]))

        # convert to float
        self._bay_img = self._bay_img.astype('float')

        return True

    def bay2rgb(self, method=2):

        # print status
        self.sta.status_msg('Debayering', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # Bayer to RGB conversion
        if method == 0:
            self._rgb_img = demosaicing_CFA_Bayer_bilinear(self._bay_img.astype(np.float32), self.cfg.lfpimg['bay'])
        elif method == 1:
            self._rgb_img = demosaicing_CFA_Bayer_Malvar2004(self._bay_img.astype(np.float32), self.cfg.lfpimg['bay'])
        else:
            self._rgb_img = demosaicing_CFA_Bayer_Menon2007(self._bay_img.astype(np.float32), self.cfg.lfpimg['bay'])

        # clip intensities above and below previous limits (removing dead and hot outliers yields much better contrast)
        #self._rgb_img[self._rgb_img < self._bay_img.min()] = self._bay_img.min()
        #self._rgb_img[self._rgb_img > self._bay_img.max()] = self._bay_img.max()

        # normalize image to previous intensity limits
        self._rgb_img = misc.Normalizer(img=self._rgb_img,
                                        min=np.percentile(self._rgb_img, .1), max=np.percentile(self._rgb_img, 99.9)
                                        ).type_norm(lim_min=self._bay_img.min(), lim_max=self._bay_img.max())


        # print "Progress: Done!"
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def _reshape_bayer(self):

        if len(self._bay_img.shape) == 2:
            # reshape bayer image to 4 channels in third dimension
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

    @property
    def rgb_img(self):
        return self._rgb_img.copy()

    @staticmethod
    def correct_gamma(img, gamma=None):
        ''' perform gamma correction on single image '''

        gamma = 1. if gamma is None else gamma

        return np.asarray(img, dtype='float64')**gamma

    @staticmethod
    def correct_awb(img_arr, bay_pattern=None, gains=None):
        ''' automatic white balance '''

        # skip process if gains not set
        if gains is None:
            return img_arr

        if len(img_arr.shape) == 3:

            img_arr[..., 2] *= gains[0]             # blue channel
            img_arr[..., 0] *= gains[1]             # red channel
            img_arr[..., 1] *= gains[2]*gains[3]    # green channel

        elif len(img_arr.shape) == 2 and bay_pattern == "GRBG":

            img_arr[1::2, 0::2] *= gains[0]         # blue channel
            img_arr[0::2, 1::2] *= gains[1]         # red channel
            img_arr[0::2, 0::2] *= gains[2]         # green-red channel
            img_arr[1::2, 1::2] *= gains[3]         # green-blue channel

        elif len(img_arr.shape) == 2 and bay_pattern == "BGGR":

            img_arr[0::2, 0::2] *= gains[0]         # blue channel
            img_arr[1::2, 1::2] *= gains[1]         # red channel
            img_arr[0::2, 1::2] *= gains[2]         # green-blue channel
            img_arr[1::2, 0::2] *= gains[3]         # green-red channel

        return img_arr

    @staticmethod
    def desaturate_clipped(img_arr, gains=None, bay_pattern="GRBG"):

        # skip process if gains not set
        if gains is not None and bay_pattern is "GRBG":
            b, r, g1, g2 = gains
        else:
            return img_arr

        orig = np.zeros(img_arr.shape)
        if len(img_arr.shape) == 3 and img_arr.shape[-1] == 3:
            orig = (img_arr/np.array([r, g1, b]))

        elif len(img_arr.shape) == 3 and img_arr.shape[-1] == 4:
            orig = (img_arr / np.array([g1, r, b, g2]))

        beta = orig / np.amax(orig, axis=2)[..., np.newaxis]
        weights = beta * np.array([r, g1, b]) if img_arr.shape[-1] == 3 else beta * np.array([g1, r, b, g2])
        weights[weights < 1] = 1

        mask = np.zeros(orig.shape[:2])
        mask[np.amax(orig, axis=2) >= orig.max()] = 1

        img_arr[mask > 0] /= weights[mask > 0]

        return img_arr

    @staticmethod
    def correct_color(img, ccm_mat=np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])):
        ''' color correction according to http://www.imatest.com/docs/colormatrix/ using Case 1 '''

        # perform color correction
        img_ccm = np.dot(np.vstack(img), ccm_mat).reshape(img.shape)

        # clip intensities above and below previous limits (removing dead and hot outliers yields much better contrast)
        #img_ccm[img_ccm < img.min()] = img.min()
        #img_ccm[img_ccm > img.max()] = img.max()

        # normalize image to previous intensity limits
        img_ccm = misc.Normalizer(img=img_ccm, min=np.percentile(img_ccm, .1), max=np.percentile(img_ccm, 99.9)
                                  ).type_norm(lim_min=img.min(), lim_max=img.max())

        return img_ccm
