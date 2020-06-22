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
from os.path import exists, join, basename, splitext

from plenopticam.lfp_calibrator import LfpCalibrator
from plenopticam.lfp_aligner import LfpAligner
from plenopticam.lfp_extractor import LfpExtractor
from plenopticam.lfp_refocuser import LfpRefocuser
from plenopticam.cfg.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus, mkdir_p, load_img_file
from test.unit_test_baseclass import PlenoptiCamTester


class PlenoptiCamTesterCustom(PlenoptiCamTester):

    CEA_PATH = r'../plenopticam/scripts/metrics/calibration/centroid_error_analysis/'

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTesterCustom, self).__init__(*args, **kwargs)

    def setUp(self):

        # retrieve OpEx data from Hahne et al.
        url = 'https://ndownloader.figshare.com/files/5201452'
        archive_fn = join(self.fp, basename(url))
        self.download_data(url) if not exists(archive_fn) else None
        self.fnames_wht_opex = ['f197with4m11pxf16Final.bmp', 'f197Inf9pxFinalShift12.7cmf22.bmp']
        self.fnames_lfp_opex = ['f197with4m11pxFinal.bmp', 'f197Inf9pxFinalShift12.7cm.bmp']
        self.extract_archive(join(self.fp, basename(url)), self.fnames_wht_opex+self.fnames_lfp_opex)

        # set config for unit test purposes
        self.sta = PlenopticamStatus()
        self.cfg = PlenopticamConfig()
        self.cfg.reset_values()
        self.cfg.params[self.cfg.opt_dbug] = False
        self.cfg.params[self.cfg.opt_prnt] = False    # prevent Travis CI to terminate after reaching 4MB logfile size
        self.cfg.params[self.cfg.opt_vign] = True
        self.cfg.params[self.cfg.opt_sat_] = True

    def test_custom_cal(self):

        for fn_lfp, fn_wht in zip(self.fnames_lfp_opex, self.fnames_wht_opex):

            # generate console output to prevent abort in Travis CI
            print(fn_wht)

            # update file paths and calibration data in config
            self.cfg.params[self.cfg.lfp_path] = join(self.fp, fn_lfp)
            self.cfg.params[self.cfg.cal_path] = join(self.fp, fn_wht)

            # create folder (if it doesn't already exist)
            mkdir_p(splitext(self.cfg.params[self.cfg.lfp_path])[0])

            # test light field calibration
            wht_img = load_img_file(self.cfg.params[self.cfg.cal_path])
            cal_obj = LfpCalibrator(wht_img=wht_img, cfg=self.cfg, sta=self.sta)
            ret_val = cal_obj.main()
            del cal_obj

            # assertion
            self.assertEqual(True, ret_val)

    def test_custom_lfp(self):

        for fn_lfp, fn_wht in zip(self.fnames_lfp_opex, self.fnames_wht_opex):

            # generate console output to prevent abort in Travis CI
            print(fn_lfp)

            # update file paths and calibration data in config
            self.cfg.params[self.cfg.lfp_path] = join(self.fp, fn_lfp)
            self.cfg.params[self.cfg.cal_path] = join(self.fp, fn_wht)
            self.cfg.params[self.cfg.cal_meta] = splitext(self.cfg.params[self.cfg.cal_path])[0]+'.json'
            self.cfg.load_cal_data()

            # create folder (if it doesn't already exist)
            mkdir_p(splitext(self.cfg.params[self.cfg.lfp_path])[0])

            # test light field alignment
            lfp_img = load_img_file(self.cfg.params[self.cfg.lfp_path])
            lfp_obj = LfpAligner(lfp_img=lfp_img, cfg=self.cfg, sta=self.sta)
            ret_val = lfp_obj.main()
            lfp_img = lfp_obj.lfp_img
            del lfp_obj

            # assertion
            self.assertEqual(True, ret_val)

            # test light field extraction
            lfp_obj = LfpExtractor(lfp_img_align=lfp_img, cfg=self.cfg, sta=self.sta)
            ret_val = lfp_obj.main()
            vp_img_arr = lfp_obj.vp_img_arr
            del lfp_obj

            # assertion
            self.assertEqual(True, ret_val)

            lfp_obj = LfpRefocuser(vp_img_arr=vp_img_arr, cfg=self.cfg, sta=self.sta)
            ret_val = lfp_obj.main()
            del lfp_obj

            # assertion
            self.assertEqual(True, ret_val)

    @unittest.skipUnless(condition=exists(join(CEA_PATH, 'a.png')), reason='Test data for PitchEstimator not found')
    def test_pitch_estimator(self):

        from plenopticam.lfp_calibrator import PitchEstimator

        fns = [join(self.CEA_PATH, fn+'.png') for fn in ['a', 'b', 'c', 'd']]
        ref_sizes = [141, 50, 10, 6]

        for fn, ref_size in zip(fns, ref_sizes):
            img = load_img_file(fn)
            obj = PitchEstimator(img=img, cfg=self.cfg)
            obj.main()

            self.assertEqual(ref_size, obj.M)


if __name__ == '__main__':
    unittest.main()
