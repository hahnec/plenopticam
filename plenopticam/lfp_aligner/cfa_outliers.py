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

from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus
from plenopticam import misc

import numpy as np
import os
from scipy.signal import medfilt


class CfaOutliers(object):

    def __init__(self, *args, **kwargs):

        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()

        self._bay_img = kwargs['bay_img'] if 'bay_img' in kwargs else np.array([])

    def rectify_candidates_bayer(self, bay_img=None, n=2, sig_lev=4):

        # status message
        self.sta.status_msg('Hot pixel detection', self.cfg.params[self.cfg.opt_prnt])

        bay_img = self._bay_img.copy() if bay_img is None else bay_img
        cum_img = np.zeros(bay_img[0::2, 0::2].shape)

        for c in range(4):

            # check interrupt status
            if self.sta.interrupt:
                return False

            # progress update
            percent = c / 4
            self.sta.progress(percent*100, self.cfg.params[self.cfg.opt_prnt])

            # Bayer channel index
            i, j = c//2, c % 2

            # deduct median filtered image
            med_img = medfilt(bay_img[i::2, j::2].copy(), kernel_size=(3, 3))
            m_img = bay_img[i::2, j::2].copy()/bay_img[i::2, j::2].max() - med_img.copy()/med_img.max()

            new_img = self.rectify_candidates_channel(channel=bay_img[i::2, j::2].copy(),
                                                      ref_img=m_img, med_img=med_img, n=n, sig_lev=sig_lev+2)

            diff_img = bay_img[i::2, j::2].copy() - new_img
            cum_img[diff_img != 0] = 1

            bay_img[i::2, j::2] = new_img

        # export hot-pixel map
        if self.cfg.params[self.cfg.opt_dbug]:
            hotp_num = len(cum_img[cum_img != 0])
            misc.save_img_file(cum_img, file_path=os.path.join(self.cfg.exp_path, 'hot-pixel_map_'+str(hotp_num)+'.png'))

        # progress update
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        self._bay_img = bay_img

        return True

    def rectify_candidates_channel(self, channel, ref_img=None, med_img=None, n=2, sig_lev=4):

        ref_img = channel if ref_img is None else ref_img
        med_img = channel if med_img is None else med_img

        # pre-select outlier candidates (narrow-down search area to speed-up the process)
        m_val = np.mean(ref_img)
        s_val = np.std(ref_img)
        candidate_idxs = np.where(ref_img > m_val + s_val * sig_lev)

        ref_img = np.zeros_like(channel)
        ref_img[candidate_idxs[0], candidate_idxs[1]] = channel[candidate_idxs[0], candidate_idxs[1]]
        ref_img[ref_img < .3] = 0
        candidate_idxs = np.where(ref_img != 0)
        candidates = list(zip(candidate_idxs[0], candidate_idxs[1]))

        if n < 1 or not misc.isint(n):
            self.sta.status_msg('Skip hot-pixel detection due to wrong settings', self.cfg.params[self.cfg.opt_prnt])
            return channel

        for num, idx in enumerate(candidates):

            j, i = idx

            adj_cands = (candidate_idxs[0] > j-n**2) & (candidate_idxs[0] < j+n**2) & \
                        (candidate_idxs[1] > i-n**2) & (candidate_idxs[1] < i+n**2)

            if np.count_nonzero(adj_cands) < n:

                if n < j < ref_img.shape[0]-n and n < i < ref_img.shape[1]-n:
                    win = channel[j-n:j+n+1, i-n:i+n+1]
                else:
                    # treat candidates being too close to image border
                    alt_n = min(j, abs(ref_img.shape[0]-j), i, abs(ref_img.shape[1]-i))
                    win = channel[j-alt_n:j+alt_n+1, i-alt_n:i+alt_n+1]

                m_val = np.mean(win)
                s_val = np.std(win)

                if channel[j, i] < m_val - s_val * sig_lev or channel[j, i] > m_val + s_val * sig_lev:

                    # replace outlier
                    channel[j, i] = med_img[j, i]

            # check interrupt status
            if self.sta.interrupt:
                return False

        return channel

    @property
    def bay_img(self):
        return self._bay_img
