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

    def main(self):

        # estimate contrast and brightness via least-squares method
        self.auto_contrast()

        # apply estimated brightness and contrast levels to viewpoint array
        self.proc_vp_arr(self.correct_contrast, msg='Contrast automation')

    def auto_contrast(self, ch=0):
        ''' according to https://stackoverflow.com/questions/9744255/instagram-lux-effect/9761841#9761841 '''

        # estimate contrast und brightness parameters (by default: achromatic "luma" channel only)
        val_lim = 2**16-1
        img_yuv = misc.yuv_conv(self.central_view)
        h = np.histogram(img_yuv[..., ch], bins=np.arange(val_lim))[0]
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

        return True

    @staticmethod
    def find_x_given_y(value, x, y, tolerance=1e-3):
        return np.mean(np.array([(xi, yi) for (xi, yi) in zip(x, y) if abs(yi - value) <= tolerance]).T[0])

    def correct_contrast(self, img_arr, ch=0):
        ''' Application of contrast and brightness values to luminance channel of provided RGB image '''

        # color model conversion
        img_yuv = misc.yuv_conv(img_arr)

        # convert to float
        f = img_yuv[..., ch].astype(np.float32)

        # perform auto contrast (by default: "value" channel only)
        img_yuv[..., ch] = self._contrast * f + self._brightness

        # clip to input extrema to remove contrast outliers
        img_yuv[..., ch][img_yuv[..., ch] < img_arr.min()] = img_arr.min()
        img_yuv[..., ch][img_yuv[..., ch] > img_arr.max()] = img_arr.max()

        # color model conversion
        img = misc.yuv_conv(img_yuv, inverse=True)

        return img

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