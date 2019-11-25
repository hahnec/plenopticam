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
from plenopticam.lfp_extractor.lfp_cropper import LfpCropper
from plenopticam.lfp_extractor.lfp_rearranger import LfpRearranger
from plenopticam.cfg import PlenopticamConfig
from plenopticam import misc


class LfpExtractor(object):

    def __init__(self, lfp_img_align, cfg=None, sta=None):

        self._lfp_img_align = lfp_img_align
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else misc.PlenopticamStatus()

        # internal variable
        self._vp_img_arr = []

    def main(self):

        self.cfg.load_cal_data()

        # micro image crop
        if not self.sta.interrupt:
            lfp_obj = LfpCropper(lfp_img_align=self._lfp_img_align, cfg=self.cfg, sta=self.sta)
            lfp_obj.main()
            self._lfp_img_align = lfp_obj.lfp_img_align
            del lfp_obj

        # viewpoint images
        if self.cfg.params[self.cfg.opt_view] and not self.sta.interrupt:
            lfp_obj = LfpRearranger(self._lfp_img_align, cfg=self.cfg, sta=self.sta)
            lfp_obj.main()
            self.vp_img_arr = lfp_obj.vp_img_arr
            del lfp_obj

        return True
