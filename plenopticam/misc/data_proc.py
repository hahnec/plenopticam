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
from scipy.interpolate import interp2d
from color_space_converter import yuv_conv

from plenopticam.misc.normalizer import Normalizer


def create_gauss_kernel(length: int = 7, sigma: float = 1) -> np.ndarray:
    
    # ensure length is odd
    length = (length - 1)//2 + (length + 1)//2
    
    # compute Gaussian kernel
    xs = np.arange(-length//2 + 1, length//2 + 1)
    xx, yy = np.meshgrid(xs, xs)
    kernel = np.exp(-(xx**2 + yy**2) / (2*sigma**2))
    kernel /= kernel.sum()
    
    return kernel


def safe_get(any_dict, *keys):

    if any_dict:
        for key in keys:
            try:
                any_dict = any_dict[key]
            except KeyError:
                return None

    return any_dict


def img_resize(img, x_scale=1, y_scale=None, method=None, new_shape=None, norm_opt=False):
    """ perform image interpolation based on scipy lib """

    if not y_scale:
        y_scale = x_scale

    if x_scale == 1 and y_scale == 1 and new_shape is None or x_scale <= 0 or y_scale <= 0:
        return img

    method = 'cubic' if method is None else method
    dtype = img.dtype

    if len(img.shape) == 3:
        n, m, p = img.shape
    elif len(img.shape) == 2:
        n, m, p = img.shape + (1,)
        img = img[..., np.newaxis]
    else:
        raise NotImplementedError

    # construct new 2-D shape
    y_len, x_len = (int(round(n*y_scale)), int(round(m*x_scale))) if x_scale != 1 or y_scale != 1 else new_shape

    # interpolate
    new_img = np.zeros([y_len, x_len, p])
    for p in range(p):
        f = interp2d(range(m), range(n), img[:, :, p], kind=method)
        new_img[:, :, p] = f(np.linspace(0, m - 1, x_len), np.linspace(0, n - 1, y_len))

    # normalize to the 0-1 range
    new_img = Normalizer(new_img).type_norm(new_min=0, new_max=1) if norm_opt else new_img

    # remove added third axes in monochromatic image
    new_img = new_img[..., 0] if new_img.shape[-1] == 1 else new_img

    return new_img.astype(dtype)


def eq_channels(img):
    """ equalize channels of RGB image (make channels of even power) """

    chs = np.ones(img.shape[2]) if len(img.shape) == 3 else 1
    ch_max = np.argmax(img.sum(axis=0).sum(axis=0))
    for idx in range(len(chs)):
        chs[idx] = np.mean(img[..., ch_max]) / np.mean(img[..., idx])
        img[..., idx] *= chs[idx]

    return img


def robust_awb(img, t=0.3, max_iter=1000):
    """ inspired by Jun-yan Huo et al. and http://web.stanford.edu/~sujason/ColorBalancing/Code/robustAWB.m """

    img = Normalizer(img).type_norm(new_min=0, new_max=1.0)
    ref_pixel = img[0, 0, :].copy()

    u = .01  # gain step size
    a = .8  # double step threshold
    b = .001  # convergence threshold

    gains_adj = np.array([1., 1., 1.])

    for i in range(max_iter):
        img_yuv = yuv_conv(img)
        f = (abs(img_yuv[..., 1]) + abs(img_yuv[..., 2])) / img_yuv[..., 0]
        grays = np.zeros(img_yuv.shape)
        grays[f < t] = img_yuv[f < t]
        if np.sum(f < t) == 0:
            print('No valid gray pixels found.')
            break

        u_bar = np.mean(grays[..., 1])  # estimate
        v_bar = np.mean(grays[..., 2])  # estimate

        # rgb_est = yuv_conv(np.array([100, u_bar, v_bar]), inverse=True)    # convert average gray from YUV to RGB

        # U > V: blue needs adjustment otherwise red is treated
        err, ch = (u_bar, 2) if abs(u_bar) > abs(v_bar) else (v_bar, 0)

        if abs(err) >= a:
            delta = 2 * np.sign(err) * u  # accelerate gain adjustment if far off
        elif abs(err) < b:  # converged when u_bar and v_bar < b
            # delta = 0
            #self.sta.status_msg('AWB convergence reached', self.cfg.params[self.cfg.opt_prnt])
            break
        else:
            delta = err * u

        # negative feedback loop
        gains_adj[ch] -= delta

        img = np.dot(img, np.diag(gains_adj))

    # take gains only if result is obtained by convergence
    gains = img[0, 0, :] / ref_pixel if i != max_iter - 1 else (1, 1, 1)

    return img, gains


def suppress_user_warning(switch=None, category=None):

    import warnings
    switch = switch if switch is None else True
    if switch:
        warnings.filterwarnings("ignore", category=category)
    else:
        warnings.filterwarnings("default", category=category)
