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


class CfaHotPixels(object):

    def __init__(self, *args, **kwargs):

        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()

    def rectify_candidates_bayer(self, bay_img, n=2, sig_lev=4):

        # status message
        self.sta.status_msg('Hot pixel removal', self.cfg.params[self.cfg.opt_prnt])

        cum_img = np.zeros(bay_img[0::2, 0::2].shape)

        for i in range(2):
            for j in range(2):

                # progress update
                percent = (j+i*2) / 4
                self.sta.progress(percent*100, self.cfg.params[self.cfg.opt_prnt])

                # deduct median filtered image
                med_img = medfilt(bay_img[i::2, j::2].copy(), kernel_size=(3, 3))
                m_img = bay_img[i::2, j::2].copy()/bay_img[i::2, j::2].max() - med_img.copy()/med_img.max()

                new_img = self.rectify_candidates_channel(channel=bay_img[i::2, j::2].copy(), ref_img=m_img, med_img=med_img, n=n, sig_lev=sig_lev + 2)
                #misc.save_img_file(new_img, file_path=os.path.join(self.cfg.exp_path, 'outlier'+str(i+2*j)+'.tiff'))

                diff_img = bay_img[i::2, j::2].copy() - new_img
                cum_img[diff_img != 0] = 1

                bay_img[i::2, j::2] = new_img

                # check interrupt status
                if self.sta.interrupt:
                    return False

        hotp_num = len(cum_img[cum_img != 0])
        misc.save_img_file(cum_img, file_path=os.path.join(self.cfg.exp_path, str(hotp_num)+'_cum.png'))

        # progress update
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return bay_img

    def rectify_candidates_channel(self, channel, ref_img=None, med_img=None, n=2, sig_lev=4):

        ref_img = channel if ref_img is None else ref_img
        med_img = channel if med_img is None else med_img

        # pre-select outlier candidates to narrow-down search area and speed-up the process
        m_val = np.mean(ref_img)
        s_val = np.std(ref_img)
        candidate_idxs = np.where((ref_img < m_val - s_val * sig_lev) | (ref_img > m_val + s_val * sig_lev))
        candidates = list(zip(candidate_idxs[0], candidate_idxs[1]))

        #k = np.zeros(ref_img.shape)
        #k[(ref_img < m_val - s_val * sig_lev) | (ref_img > m_val + s_val * sig_lev)] = 1
        #misc.save_img_file(k, file_path=os.path.join(self.cfg.exp_path+'candidates.png'))

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
                    channel[j, i] = med_img[j, i]#(sum(sum(channel[j-1:j+2, i-1:i+2])) - channel[j, i]) / 8.#

            # check interrupt status
            if self.sta.interrupt:
                return False

        return channel
