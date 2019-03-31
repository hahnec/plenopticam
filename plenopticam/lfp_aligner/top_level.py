#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2017 Christopher Hahne <info@christopherhahne.de>

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

# local imports
from plenopticam import misc
from plenopticam.lfp_aligner.lfp_resampler import LfpResampler
from plenopticam.lfp_aligner.pitch_eval import pitch_eval
from plenopticam.lfp_aligner.lfp_rotator import LfpRotator

class LfpAligner(object):

    def __init__(self, lfp_img, cfg=None, sta=None, wht_img=None):

        # input variables
        self.cfg = cfg
        self.sta = sta if sta is not None else misc.PlenopticamStatus()
        self._lfp_img = lfp_img
        self._wht_img = wht_img

    def main(self):

        if self.cfg.params[self.cfg.opt_rota] and self._lfp_img is not None:
            # de-rotate centroids
            obj = LfpRotator(self._lfp_img, self.cfg.calibs[self.cfg.mic_list], rad=None, cfg=self.cfg, sta=self.sta)
            obj.main()
            self._lfp_img, self.cfg.calibs[self.cfg.mic_list] = obj.lfp_img, obj.centroids
            del obj

        # evaluate valid patch size
        self.cfg.params[self.cfg.ptc_leng] = pitch_eval(self.cfg.calibs[self.cfg.mic_list], self.cfg.params[self.cfg.ptc_leng])

        # interpolate each micro image with its MIC as the center with consistent micro image size
        obj = LfpResampler(self._lfp_img, self.cfg, self.sta)
        obj.main()
        self._lfp_img = obj.lfp_out
        del obj

        # print status
        self.sta.status_msg('Alignment finished', opt=True)
        self.sta.progress(100, opt=True)

        return True

    @property
    def lfp_img(self):
        return self._lfp_img.copy()