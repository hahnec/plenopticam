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


class LfpRefocuser(LfpViewpoints):

    def __init__(self, vp_img_arr=None, *args, **kwargs):
        super(LfpRefocuser, self).__init__(*args, **kwargs)

        # input variables
        self.vp_img_arr = vp_img_arr

    def main(self):

        # refocused image stack
        if self.cfg.params[self.cfg.opt_refo]:
            self.shift_and_sum()
        # scheimpflug focus
        if self.cfg.params[self.cfg.opt_pflu] != 'off':
            self.scheimplfug()

    def shift_and_sum(self):

        lfp_obj = LfpShiftAndSum(vp_img_arr=self.vp_img_arr, cfg=self.cfg, sta=self.sta)
        lfp_obj.main()
        self.refo_stack = lfp_obj.refo_stack
        del lfp_obj

    def scheimpflug(self):

        lfp_obj = LfpScheimpflug(refo_stack=self.refo_stack, cfg=self.cfg, sta=self.sta)
        lfp_obj.main()
        del lfp_obj
