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
from plenopticam.lfp_extractor.lfp_outliers import LfpOutliers
from plenopticam.lfp_extractor.lfp_color_eq import LfpColorEqualizer
from plenopticam.lfp_extractor.hex_corrector import HexCorrector

import pickle
import os


class LfpExtractor(object):

    def __init__(self, lfp_img_align=None, cfg=None, sta=None):

        # input variables
        self._lfp_img_align = lfp_img_align
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else misc.PlenopticamStatus()

        # variables for viewpoint arrays
        self.vp_img_arr = []        # gamma corrected
        self.vp_img_linear = []     # linear gamma (for further processing)

    def main(self):

        # load previously calculated calibration and aligned data
        self.cfg.load_cal_data()
        if self._lfp_img_align is None:
            self.load_pickle_file()
            self.load_lfp_metadata()

        # micro image crop
        lfp_obj = LfpCropper(lfp_img_align=self._lfp_img_align, cfg=self.cfg, sta=self.sta)
        lfp_obj.main()
        self._lfp_img_align = lfp_obj.lfp_img_align
        del lfp_obj

        # rearrange light-field to sub-aperture images
        if self.cfg.params[self.cfg.opt_view]:
            lfp_obj = LfpRearranger(self._lfp_img_align, cfg=self.cfg, sta=self.sta)
            lfp_obj.main()
            self.vp_img_linear = lfp_obj.vp_img_arr
            del lfp_obj

        # remove outliers if option is set
        if self.cfg.params[self.cfg.opt_lier]:
            obj = LfpOutliers(vp_img_arr=self.vp_img_linear, cfg=self.cfg, sta=self.sta)
            obj.main()
            self.vp_img_linear = obj.vp_img_arr
            del obj

        # color equalization
        if self.cfg.params[self.cfg.opt_colo]:
            obj = LfpColorEqualizer(vp_img_arr=self.vp_img_linear, cfg=self.cfg, sta=self.sta)
            obj.main()
            self.vp_img_linear = obj.vp_img_arr
            del obj

        # copy light-field for refocusing process prior to contrast alignment and export
        self.vp_img_arr = self.vp_img_linear.copy() if self.vp_img_linear is not None else None

        # color management automation
        obj = LfpContrast(vp_img_arr=self.vp_img_arr, cfg=self.cfg, sta=self.sta)
        obj.main()
        self.vp_img_arr = obj.vp_img_arr
        del obj

        # reduction of hexagonal sampling artifacts
        if self.cfg.params[self.cfg.opt_arti]:
            obj = HexCorrector(vp_img_arr=self.vp_img_arr, cfg=self.cfg, sta=self.sta)
            obj.main()
            self.vp_img_arr = obj.vp_img_arr
            del obj

        # write viewpoint data to hard drive
        if self.cfg.params[self.cfg.opt_view]:
            obj = LfpExporter(vp_img_arr=self.vp_img_arr, cfg=self.cfg, sta=self.sta)
            obj.write_viewpoint_data()
            del obj

        return True

    def load_pickle_file(self):
        """ load previously computed light field alignment """

        # file path
        fp = os.path.join(self.cfg.exp_path, 'lfp_img_align.pkl')

        try:
            self._lfp_img_align = pickle.load(open(fp, 'rb'))
        except EOFError:
            os.remove(fp)
        except FileNotFoundError:
            return False

        return True

    def load_lfp_metadata(self):
        """ load LFP metadata settings (for Lytro files only) """

        fname = os.path.splitext(os.path.basename(self.cfg.params[self.cfg.lfp_path]))[0]+'.json'
        fp = os.path.join(self.cfg.exp_path, fname)
        if os.path.isfile(fp):
            json_dict = self.cfg.load_json(fp=fp, sta=None)
            from plenopticam.lfp_reader.lfp_decoder import LfpDecoder
            self.cfg.lfpimg = LfpDecoder().filter_lfp_json(json_dict, settings=self.cfg.lfpimg)

        return True
