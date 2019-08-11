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
