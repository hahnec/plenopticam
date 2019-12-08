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
from plenopticam.lfp_extractor import LfpViewpoints

import os
from scipy.ndimage import median_filter
from scipy.signal import medfilt
import numpy as np

class LfpHotPixels(LfpViewpoints):

    def __init__(self, *args, **kwargs):
        super(LfpHotPixels, self).__init__(*args, **kwargs)

    def main(self):

        self.proc_vp_arr(self.correct_outliers, msg='Pixel outlier removal')
        #self.vp_hotpixel_removal()

    def correct_outliers(self, img, n=2, perc=.2):

        for j in range(n, img.shape[0]-n):
            for i in range(n, img.shape[1]-n):

                win = img[j-n:j+n+1, i-n:i+n+1]

                # hot pixel detection
                num_hi = len(win[win > img[j, i]*(1-perc)])

                # dead pixel detection
                num_lo = len(win[win < img[j, i]*perc])

                if num_hi < win.size/(2*n+1) or num_lo > win.size/(2*n+1):
                    # replace outlier by average of all directly adjacent pixels
                    img[j, i] = (sum(sum(img[j-1:j+2, i-1:i+2]))-img[j, i])/8.

                # check interrupt status
                if self.sta.interrupt:
                    return False

        return img

    def correct_luma_outliers(self, img, n=2, perc=.2):

        # luma channel conversion
        luma = misc.clr_spc_conv.yuv_conv(img.copy())[..., 0]

        for j in range(n, luma.shape[0]-n):
            for i in range(n, luma.shape[1]-n):
                win = luma[j-n:j+n+1, i-n:i+n+1]

                # hot pixel detection
                num_hi = len(win[win > luma[j, i]*(1-perc)])

                # dead pixel detection
                num_lo = len(win[win < luma[j, i]*perc])

                if num_hi < win.size/(2*n+1) or num_lo < win.size/(2*n+1):
                    # replace outlier by average of all directly adjacent pixels
                    img[j, i, :] = (sum(sum(img[j-1:j+2, i-1:i+2, :]))-img[j, i, :])/8.

                # check interrupt status
                if self.sta.interrupt:
                    return False

        return img

    @staticmethod
    def channel_outliers_filter(channel, perc=.999):

        # create copy of channel for filtering
        arr = channel.copy()

        # perform filter convolution
        filt_img = medfilt(arr, kernel_size=(3, 3))
        #filt_img = median_filter(arr, size=2)

        # compute absolute differences per pixel
        diff_img = abs(arr-filt_img)
        del arr

        # obtain intensity threshold for pixels that have to be replaced
        diff_img /= diff_img.max()
        threshold = np.percentile(diff_img, perc*100)

        # replace pixels above threshold by median filtered pixels while ignoring image borders (due to 3x3 kernel)
        channel[1:-1, 1:-1][diff_img[1:-1, 1:-1] > threshold] = filt_img[1:-1, 1:-1][diff_img[1:-1, 1:-1] > threshold]

        return channel

    def img_outliers_filter(self, img, perc=.999):

        if len(img.shape) == 3:
            for i in range(img.shape[2]):
                img[..., i] = self.channel_outliers_filter(img[..., i], perc=perc)
        elif len(img.shape) == 2:
            img = self.channel_outliers_filter(img)

        return img

    def hotpixel_candidates_bayer(self, bay_img, n=2, sig_lev=4):

        # status message
        self.sta.status_msg('Hot pixel removal', self.cfg.params[self.cfg.opt_prnt])

        #gray_img = np.zeros(bay_img[::2, ::2].shape)
        #for i in range(2):
        #    for j in range(2):
        #        ch = bay_img[i::2, j::2].copy()/bay_img[i::2, j::2].max()
        #        gray_img += ch/4

        #misc.save_img_file(gray_img, file_path=os.path.join(self.cfg.exp_path, 'gray_img.png'))

        for i in range(2):
            for j in range(2):

                # progress update
                percent = (j+i*2) / 4
                self.sta.progress(percent*100, self.cfg.params[self.cfg.opt_prnt])

                misc.save_img_file(bay_img[i::2, j::2], file_path=os.path.join(self.cfg.exp_path, str(i)+str(j)+'.png'))

                # deduct gray image
                gray_img = medfilt(bay_img[i::2, j::2].copy(), kernel_size=(3, 3))
                m_img = bay_img[i::2, j::2].copy()/bay_img[i::2, j::2].max() - gray_img.copy()/gray_img.max()

                misc.save_img_file(m_img, file_path=os.path.join(self.cfg.exp_path, str(i) + str(j) + 'm_img.png'))

                new_img = self.hotpixel_candidates(channel=bay_img[i::2, j::2].copy(), ref_img=m_img, n=n, sig_lev=sig_lev+2)

                # misc.save_img_file(new_img, file_path=os.path.join(self.cfg.exp_path, str(i) + str(j) + '_post.png'))
                diff_img = bay_img[i::2, j::2].copy() - new_img
                diff_img[diff_img != 0] = 1
                hot_pix_num = len(diff_img[diff_img != 0])
                misc.save_img_file(diff_img, file_path=os.path.join(self.cfg.exp_path, str(i) + str(j) + '_' + str(
                    hot_pix_num) + '_diff.png'))

                bay_img[i::2, j::2] = new_img

        # progress update
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return bay_img

    def hotpixel_candidates(self, channel, ref_img=None, n=2, sig_lev=4):

        ref_img = channel if ref_img is None else ref_img

        # pre-select outlier candidates to narrow-down search area and speed-up the process
        m_val = np.mean(ref_img)
        s_val = np.std(ref_img)
        candidate_idxs = np.where((ref_img < m_val - s_val * sig_lev) | (ref_img > m_val + s_val * sig_lev))
        candidates = list(zip(candidate_idxs[0], candidate_idxs[1]))

        k = np.zeros(ref_img.shape)
        k[(ref_img < m_val - s_val * sig_lev) | (ref_img > m_val + s_val * sig_lev)] = 1
        misc.save_img_file(k, file_path=os.path.join(self.cfg.exp_path+'candidates.png'))

        for num, idx in enumerate(candidates):

            j, i = idx
            win = channel[j-n:j+n+1, i-n:i+n+1]

            if win.size > 0:
                m_val = np.mean(win)
                s_val = np.std(win)
                if channel[j, i] < m_val - s_val * sig_lev or channel[j, i] > m_val + s_val * sig_lev:

                    #num_hi = len(win[win > m_val + s_val * (sig_lev-2)])
                    #num_lo = len(win[win < m_val - s_val * (sig_lev-2)])
                    #if num_hi < n//2 or num_lo < n//2:

                    # replace outlier by average of all directly adjacent pixels
                    channel[j, i] = (sum(sum(channel[j-1:j+2, i-1:i+2])) - channel[j, i]) / 8.

        return channel
