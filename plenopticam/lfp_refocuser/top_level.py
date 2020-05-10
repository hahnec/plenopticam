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
from plenopticam.lfp_extractor.lfp_viewpoints import LfpViewpoints
from plenopticam.lfp_refocuser.lfp_shiftandsum import LfpShiftAndSum
from plenopticam.lfp_refocuser.lfp_scheimpflug import LfpScheimpflug
from plenopticam.lfp_extractor.lfp_exporter import LfpExporter
from plenopticam.lfp_extractor.lfp_contrast import LfpContrast
from plenopticam.misc import GammaConverter


class LfpRefocuser(LfpViewpoints):

    def __init__(self, vp_img_arr=None, *args, **kwargs):
        super(LfpRefocuser, self).__init__(*args, **kwargs)

        # input variables
        self.vp_img_arr = vp_img_arr

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # refocused image stack
        if self.cfg.params[self.cfg.opt_refo]:
            self.shift_and_sum()
        # scheimpflug focus
        if self.cfg.params[self.cfg.opt_pflu]:
            self.scheimpflug()

        return True

    def shift_and_sum(self):

        # refocusing
        obj = LfpShiftAndSum(vp_img_arr=self.vp_img_arr, cfg=self.cfg, sta=self.sta)
        obj.main()
        self.refo_stack = obj.refo_stack
        del obj

        # color management automation
        if not self.sta.interrupt and self.refo_stack is not None:
            self.refo_stack = LfpContrast().auto_hist_align(self.refo_stack, ref_img=self.refo_stack[0], opt=True)
            self.refo_stack = GammaConverter().srgb_conv(img=self.refo_stack)

        # write refocused images to hard drive
        if not self.sta.interrupt:
            obj = LfpExporter(refo_stack=self.refo_stack, cfg=self.cfg, sta=self.sta)
            obj.export_refo_stack(file_type='png')
            obj.gif_refo()
            del obj

    def scheimpflug(self):

        obj = LfpScheimpflug(refo_stack=self.refo_stack, cfg=self.cfg, sta=self.sta)
        obj.main()
        del obj
