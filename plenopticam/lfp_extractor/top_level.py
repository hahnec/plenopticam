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
from plenopticam.lfp_extractor.lfp_refocuser import LfpRefocuser
from plenopticam.lfp_extractor.lfp_scheimpflug import LfpScheimpflug
from plenopticam import misc


class LfpExtractor(object):

    def __init__(self, lfp_img_align, cfg=None, sta=None):

        self._lfp_img_align = lfp_img_align
        self.cfg = cfg
        self.sta = sta if sta is not None else misc.PlenopticamStatus()

        # internal variables
        self._vp_img_arr = []
        self._refo_stack = []

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
            self._vp_img_arr = lfp_obj.vp_img_arr
            del lfp_obj

        # refocused image stack
        if self.cfg.params[self.cfg.opt_refo] and not self.sta.interrupt:
            lfp_obj = LfpRefocuser(vp_img_arr=self._vp_img_arr, cfg=self.cfg, sta=self.sta)
            lfp_obj.main()
            self._refo_stack = lfp_obj.refo_stack
            del lfp_obj

        # scheimpflug focus
        if self.cfg.params[self.cfg.opt_pflu] != 'off' and not self.sta.interrupt:
            lfp_obj = LfpScheimpflug(refo_stack=self._refo_stack, cfg=self.cfg, sta=self.sta)
            lfp_obj.main()
            del lfp_obj

        # print status
        self.sta.status_msg('Export finished', opt=True)
        self.sta.progress(100, opt=True)

        return True

    @property
    def vp_img_arr(self):
        return self._vp_img_arr.copy()

    @property
    def refo_stack(self):
        return self._refo_stack.copy()
