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
from plenopticam.cfg import PlenopticamConfig
from plenopticam import misc
from plenopticam.lfp_extractor.lfp_cropper import LfpCropper
from plenopticam.lfp_extractor.lfp_rearranger import LfpRearranger
from plenopticam.lfp_extractor.lfp_exporter import LfpExporter
from plenopticam.lfp_extractor.lfp_contrast import LfpContrast
from plenopticam.misc.hist_eq import HistogramEqualizer
from plenopticam.lfp_extractor.lfp_outliers import LfpOutliers
from plenopticam.lfp_extractor.lfp_color_eq import LfpColorEqualizer


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

        # histogram equalization
        if self.cfg.params[self.cfg.opt_cont] and not self.sta.interrupt:
            obj = HistogramEqualizer(img=self.vp_img_arr)
            self.vp_img_arr = obj.lum_eq()
            #self.vp_img_arr = obj.awb_eq()
            del obj

        # remove outliers if option is set
        if self.cfg.params[self.cfg.opt_lier] and not self.sta.interrupt:
            obj = LfpOutliers(vp_img_arr=self.vp_img_arr, cfg=self.cfg, sta=self.sta)
            obj.main()
            self.vp_img_arr = obj.vp_img_arr
            del obj

        # color equalization
        if self.cfg.params[self.cfg.opt_colo] and not self.sta.interrupt:
            obj = LfpColorEqualizer(vp_img_arr=self.vp_img_arr, cfg=self.cfg, sta=self.sta)
            obj.main()
            self.vp_img_arr = obj._vp_img_arr
            del obj

        if not self.sta.interrupt:
            obj = LfpContrast(vp_img_arr=self.vp_img_arr, cfg=self.cfg, sta=self.sta, p_lo=0.01, p_hi=1.0)
            # automatic white balance (otherwise default balance only)
            obj.p_hi, obj.p_lo = (0.995, 0.01) if self.cfg.params[self.cfg.opt_awb_] else (obj.p_hi, obj.p_lo)
            obj.auto_wht_bal()

            # automatic saturation
            if self.cfg.params[self.cfg.opt_sat_]:
                obj.p_hi, obj.p_lo = (1, 0)
                obj.sat_bal()

            self.vp_img_arr = obj.vp_img_arr
            del obj

        # write viewpoint data to hard drive
        if self.cfg.params[self.cfg.opt_view] and not self.sta.interrupt:
            obj = LfpExporter(vp_img_arr=self.vp_img_arr, cfg=self.cfg, sta=self.sta)
            obj.write_viewpoint_data()
            del obj

        return True
