import numpy as np

from plenopticam import misc
from plenopticam.lfp_extractor import LfpViewpoints


class LfpContrast(LfpViewpoints):

    def __init__(self, p_lo=None, p_hi=None, *args, **kwargs):
        super(LfpContrast, self).__init__(*args, **kwargs)

        self.p_lo = p_lo if p_lo is not None else 0.01
        self.p_hi = p_hi if p_hi is not None else 0.99

        # internal variables
        self._contrast, self._brightness = (1., 1.)

    def contrast_bal(self):

        # estimate contrast and brightness via least-squares method
        self.set_params_lum()

        # apply estimated brightness and contrast levels to viewpoint array
        #self.proc_vp_arr(self.correct_contrast, msg='Contrast automation')
        self.correct_contrast_lum()

    def set_params(self, ref_ch):
        ''' according to https://stackoverflow.com/questions/9744255/instagram-lux-effect/9761841#9761841 '''

        # estimate contrast und brightness parameters (by default: first channel only)
        val_lim = 2**16-1
        h = np.histogram(ref_ch, bins=np.arange(val_lim))[0]
        H = np.cumsum(h)/float(np.sum(h))
        try:
            px_lo = self.find_x_given_y(self.p_lo, np.arange(val_lim), H)
            px_hi = self.find_x_given_y(self.p_hi, np.arange(val_lim), H)
        except:
            px_lo = 0
            px_hi = 1
        A = np.array([[px_lo, 1], [px_hi, 1]])
        b = np.array([0, val_lim])
        self._contrast, self._brightness = np.dot(np.linalg.inv(A), b)

        return self._contrast, self._brightness

    @staticmethod
    def find_x_given_y(value, x, y, tolerance=1e-3):
        return np.mean(np.array([(xi, yi) for (xi, yi) in zip(x, y) if abs(yi - value) <= tolerance]).T[0])

    def correct_contrast(self, ch=0):
        ''' contrast and brightness rectification to provided RGB image '''

        # convert to float
        f = self.vp_img_arr[..., ch].astype(np.float32)

        # perform auto contrast (by default: "value" channel only)
        self.vp_img_arr[..., ch] = self._contrast * f + self._brightness

        # clip to input extrema to remove contrast outliers
        self.vp_img_arr[..., ch][self.vp_img_arr[..., ch] < f.min()] = f.min()
        self.vp_img_arr[..., ch][self.vp_img_arr[..., ch] > f.max()] = f.max()

        return True

    def correct_contrast_lum(self):
        ''' contrast and brightness rectification to luminance channel of provided RGB image '''

        # color model conversion
        self.vp_img_arr = misc.yuv_conv(self.vp_img_arr) if len(self.vp_img_arr.shape) > 4 else self.vp_img_arr

        # apply histogram stretching to luminance channel only
        self.correct_contrast(ch=0)

        # color model conversion
        self.vp_img_arr = misc.yuv_conv(self.vp_img_arr, inverse=True)

        return True

    def set_params_lum(self):

        # use luminance channel for parameter analysis
        ref_img = misc.yuv_conv(self.central_view)
        self.set_params(ref_ch=ref_img[..., 0])

    def auto_wht_bal(self):

        ch_num = self.vp_img_arr.shape[-1] if len(self.vp_img_arr.shape) > 4 else 1
        for i in range(ch_num):
            self.set_params(ref_ch=self.central_view[..., i])
            self.correct_contrast(ch=i)

        return True

    @staticmethod
    def contrast_per_channel(img_arr, sat_perc=0.1):
        ''' sat_perc is the saturation percentile which is cut-off at the lower and higher end in each color channel '''

        q = [sat_perc/100, 1-sat_perc/100]

        for ch in range(img_arr.shape[2]):

            # compute histogram quantiles
            tiles = np.quantile(img_arr[..., ch], q)

            # clip histogram quantiles
            img_arr[..., ch][img_arr[..., ch] < tiles[0]] = tiles[0]
            img_arr[..., ch][img_arr[..., ch] > tiles[1]] = tiles[1]

        return img_arr
