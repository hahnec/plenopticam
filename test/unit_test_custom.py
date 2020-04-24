#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "inbox@christopherhahne.de"
__license__ = """
    Copyright (c) 2019 Christopher Hahne <inbox@christopherhahne.de>

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

import unittest
import os

from plenopticam.lfp_calibrator import LfpCalibrator
from plenopticam.lfp_aligner import LfpAligner
from plenopticam.lfp_extractor import LfpExtractor
from plenopticam.lfp_refocuser import LfpRefocuser
from plenopticam.cfg.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus, mkdir_p, load_img_file
from test.unit_test_baseclass import PlenoptiCamTester


class PlenoptiCamTesterCustom(PlenoptiCamTester):

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTesterCustom, self).__init__(*args, **kwargs)

    def setUp(self):

        # retrieve OpEx data from Hahne et al.
        url = 'https://ndownloader.figshare.com/files/5201452'
        archive_fn = os.path.join(self.fp, os.path.basename(url))
        self.download_data(url) if not os.path.exists(archive_fn) else None
        self.fnames_wht_opex = ['f197with4m11pxf16Final.bmp', 'f197Inf9pxFinalShift12.7cmf22.bmp']
        self.fnames_lfp_opex = ['f197with4m11pxFinal.bmp', 'f197Inf9pxFinalShift12.7cm.bmp']
        self.extract_archive(os.path.join(self.fp, os.path.basename(url)), self.fnames_wht_opex+self.fnames_lfp_opex)

    def runTest(self):

        self.test_custom_cal()
        self.test_custom_lfp()

    def test_custom_cal(self):

        # set config for unit test purposes
        sta = PlenopticamStatus()
        cfg = PlenopticamConfig()
        cfg.reset_values()
        cfg.params[cfg.opt_dbug] = False
        cfg.params[cfg.opt_prnt] = False    # prevent Travis CI from terminating due to reaching 4MB logfile size
        cfg.params[cfg.opt_vign] = False
        cfg.params[cfg.opt_sat_] = True

        for fn_lfp, fn_wht in zip(self.fnames_lfp_opex, self.fnames_wht_opex):

            # generate console output to prevent abort in Travis CI
            print(fn_wht)

            # update file paths and calibration data in config
            cfg.params[cfg.lfp_path] = os.path.join(self.fp, fn_lfp)
            cfg.params[cfg.cal_path] = os.path.join(self.fp, fn_wht)

            # create folder (if it doesn't already exist)
            mkdir_p(os.path.splitext(cfg.params[cfg.lfp_path])[0])

            # test light field calibration
            wht_img = load_img_file(cfg.params[cfg.cal_path])
            cal_obj = LfpCalibrator(wht_img=wht_img, cfg=cfg, sta=sta)
            ret_val = cal_obj.main()
            del cal_obj

            # assertion
            self.assertEqual(True, ret_val)

    def test_custom_lfp(self):

        # set config for unit test purposes
        sta = PlenopticamStatus()
        cfg = PlenopticamConfig()
        cfg.reset_values()
        cfg.params[cfg.opt_dbug] = False
        cfg.params[cfg.opt_prnt] = False    # prevent Travis CI to terminate after reaching 4MB logfile size

        for fn_lfp, fn_wht in zip(self.fnames_lfp_opex, self.fnames_wht_opex):

            # generate console output to prevent abort in Travis CI
            print(fn_lfp)

            # update file paths and calibration data in config
            cfg.params[cfg.lfp_path] = os.path.join(self.fp, fn_lfp)
            cfg.params[cfg.cal_path] = os.path.join(self.fp, fn_wht)
            cfg.params[cfg.cal_meta] = os.path.splitext(cfg.params[cfg.cal_path])[0]+'.json'
            cfg.load_cal_data()

            # create folder (if it doesn't already exist)
            mkdir_p(os.path.splitext(cfg.params[cfg.lfp_path])[0])

            # test light field alignment
            lfp_img = load_img_file(cfg.params[cfg.lfp_path])
            lfp_obj = LfpAligner(lfp_img=lfp_img, cfg=cfg, sta=sta)
            ret_val = lfp_obj.main()
            lfp_img = lfp_obj.lfp_img
            del lfp_obj

            # assertion
            self.assertEqual(True, ret_val)

            # test light field extraction
            lfp_obj = LfpExtractor(lfp_img_align=lfp_img, cfg=cfg, sta=sta)
            ret_val = lfp_obj.main()
            vp_img_arr = lfp_obj.vp_img_arr
            del lfp_obj

            # assertion
            self.assertEqual(True, ret_val)

            lfp_obj = LfpRefocuser(vp_img_arr=vp_img_arr, cfg=cfg, sta=sta)
            ret_val = lfp_obj.main()
            del lfp_obj

            # assertion
            self.assertEqual(True, ret_val)


if __name__ == '__main__':
    unittest.main()
