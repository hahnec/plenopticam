# external libs
import numpy as np

from plenopticam import misc
from plenopticam.misc import Normalizer
from plenopticam.lfp_extractor import LfpViewpoints

try:
    from scipy.signal import medfilt
    from scipy.ndimage import median_filter
except ImportError:
    raise ImportError('Please install scipy package.')

class LfpColors(LfpViewpoints):

    def __init__(self, *args, **kwargs):
        super(LfpColors, self).__init__(*args, **kwargs)

        self._gains = [1., 1., 1.]

    def main(self):

        # print status
        self.sta.status_msg('Automatic white balance', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # estimate RGB gains based on central view using Huo's method
        self.robust_awb()

        # apply estimated gains to viewpoint array
        self.proc_vp_arr(self.correct_awb, g=self._gains)

        # simplest color balancing (similar to auto contrast in photoshop)
        # self.proc_vp_arr(contrast_per_channel)

        # color balance
        # sat_contrast, sat_brightness = auto_contrast(central_view, ch=1)
        # self.proc_vp_arr(correct_contrast, sat_contrast, sat_brightness, self.central_view.min(), self.central_view.max(), 1)

        # print status
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

    def robust_awb(self, t=0.3, max_iter=1000):
        ''' inspired by Jun-yan Huo et al. and http://web.stanford.edu/~sujason/ColorBalancing/Code/robustAWB.m '''

        img = Normalizer(self.central_view).type_norm(dtype='float16', lim_min=0, lim_max=1.0)
        ref_pixel = img[0, 0, :].copy()

        u = .01  # gain step size
        a = .8  # double step threshold
        b = .001  # convergence threshold

        gains_adj = np.array([1., 1., 1.])

        for i in range(max_iter):
            img_yuv = misc.yuv_conv(img)
            f = (abs(img_yuv[..., 1]) + abs(img_yuv[..., 2])) / img_yuv[..., 0]
            grays = np.zeros(img_yuv.shape)
            grays[f < t] = img_yuv[f < t]
            if np.sum(f < t) == 0:
                self.sta.status_msg('No valid gray pixels found.', self.cfg.params[self.cfg.opt_prnt])
                break

            u_bar = np.mean(grays[..., 1])  # estimate
            v_bar = np.mean(grays[..., 2])  # estimate

            # rgb_est = misc.yuv_conv(np.array([100, u_bar, v_bar]), inverse=True)    # convert average gray from YUV to RGB

            # U > V: blue needs adjustment otherwise red is treated
            err, ch = (u_bar, 2) if abs(u_bar) > abs(v_bar) else (v_bar, 0)

            if abs(err) >= a:
                delta = 2 * np.sign(err) * u  # accelerate gain adjustment if far off
            elif abs(err) < b:  # converged when u_bar and v_bar < b
                # delta = 0
                self.sta.status_msg('AWB convergence reached', self.cfg.params[self.cfg.opt_prnt])
                break
            else:
                delta = err * u

            # negative feedback loop
            gains_adj[ch] -= delta

            img = np.dot(img, np.diag(gains_adj))

        # take gains only if result is obtained by convergence
        if i != max_iter - 1:
            self._gains = img[0, 0, :] / ref_pixel

        return True

    def correct_awb(self, img, gains):

        return np.dot(img, np.diag(gains))

class ContrastHandler(LfpViewpoints):

    def __init__(self, p_lo=None, p_hi=None, *args, **kwargs):
        super(ContrastHandler, self).__init__(*args, **kwargs)

        self.p_lo = p_lo if p_lo is not None else 0.01
        self.p_hi = p_hi if p_hi is not None else 0.99

        # internal variables
        self._contrast, self._brightness = (1., 1.)

    def main(self):

        # estimate contrast and brightness via least-squares method
        self.auto_contrast()

        if len(self.vp_img_arr.shape) == 5:
            self.proc_vp_arr(self.correct_contrast, msg='Contrast correction')
        else:
            raise NotImplementedError

    def auto_contrast(self, ch=0):
        ''' according to Adi Shavit on https://stackoverflow.com/questions/9744255/instagram-lux-effect/9761841#9761841 '''

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
        # sat_perc is the saturation percentile which will be cut-off at the lower and higher end in each color channel

        q = [sat_perc/100, 1-sat_perc/100]

        for ch in range(img_arr.shape[2]):

            # compute histogram quantiles
            tiles = np.quantile(img_arr[..., ch], q)

            # clip histogram quantiles
            img_arr[..., ch][img_arr[..., ch] < tiles[0]] = tiles[0]
            img_arr[..., ch][img_arr[..., ch] > tiles[1]] = tiles[1]

        return img_arr

# def correct_hotpixels(img):
#
#     if len(img.shape) == 3:
#         for i, channel in enumerate(img.swapaxes(0, 2)):
#             img[:, :, i] = correct_outliers(channel).swapaxes(0, 1)
#     elif len(img.shape) == 2:
#         img = correct_outliers(img)
#
#     return img
#
# def correct_outliers(channel):
#
#     # create copy of channel for filtering
#     arr = channel.copy()
#
#     # perform median filter convolution
#     #med_img = medfilt(arr, kernel_size=(3, 3))
#     med_img = median_filter(arr, size=2)
#
#     # compute absolute differences per pixel
#     diff_img = abs(arr-med_img)
#     del arr
#
#     # obtain intensity threshold for pixels that have to be replaced
#     threshold = np.std(diff_img)*10#np.max(diff_img-np.mean(diff_img)) * .4
#
#     # replace pixels above threshold by median filtered pixels while ignoring image borders (due to 3x3 kernel)
#     channel[1:-1, 1:-1][diff_img[1:-1, 1:-1] > threshold] = med_img[1:-1, 1:-1][diff_img[1:-1, 1:-1] > threshold]
#
#     return channel


def correct_outliers(img, n=2, perc=.2, sta=None):

    # status init
    sta = sta if sta is not None else misc.PlenopticamStatus()
    sta.status_msg('Hot pixel removal', True)

    for i in range(n, img.shape[0]-n):
        for j in range(n, img.shape[1]-n):
            win = img[i-n:i+n+1, j-n:j+n+1]

            # hot pixel detection
            num_hi = len(win[win > img[i, j]*(1-perc)])

            # dead pixel detection
            num_lo = len(win[win < img[i, j]*(1+perc)])

            if num_hi < win.size/5 or num_lo < win.size/5:
                # replace outlier by average of all directly adjacent pixels
                img[i, j] = (sum(sum(img[i-1:i+2, j-1:j+2]))-img[i, j])/8.

            # progress update
            sta.progress((i*img.shape[1]+(j+1))/img.size*100, True)

    return img

def correct_luma_outliers(img, n=2, perc=.2, sta=None):

    # status init
    sta = sta if sta is not None else misc.PlenopticamStatus()
    sta.status_msg('Hot pixel removal', True)

    # luma channel conversion
    luma = misc.yuv_conv(img.copy())[..., 0]

    for i in range(n, luma.shape[0]-n):
        for j in range(n, luma.shape[1]-n):
            win = luma[i-n:i+n+1, j-n:j+n+1]

            # hot pixel detection
            num_hi = len(win[win > luma[i, j]*(1-perc)])

            # dead pixel detection
            num_lo = len(win[win < luma[i, j]*(1+perc)])

            if num_hi < win.size/5 or num_lo < win.size/5:
                # replace outlier by average of all directly adjacent pixels
                img[i, j, :] = (sum(sum(img[i-1:i+2, j-1:j+2, :]))-img[i, j, :])/8.

            # progress update
            sta.progress((i*luma.shape[1]+(j+1))/luma.size*100, True)

    return img
