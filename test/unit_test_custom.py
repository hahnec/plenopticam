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
from plenopticam.gui.widget_view import ViewWidget, PX, PY


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

        # set config for unit test purposes
        self.sta = PlenopticamStatus()
        self.cfg = PlenopticamConfig()
        self.cfg.reset_values()
        self.cfg.params[self.cfg.opt_dbug] = False
        self.cfg.params[self.cfg.opt_prnt] = False    # prevent Travis CI to terminate after reaching 4MB logfile size
        self.cfg.params[self.cfg.opt_vign] = False
        self.cfg.params[self.cfg.opt_sat_] = True

    def runTest(self):

        #self.test_custom_cal()
        #self.test_custom_lfp()
        self.test_viewer()

    def test_custom_cal(self):

        for fn_lfp, fn_wht in zip(self.fnames_lfp_opex, self.fnames_wht_opex):

            # generate console output to prevent abort in Travis CI
            print(fn_wht)

            # update file paths and calibration data in config
            self.cfg.params[self.cfg.lfp_path] = os.path.join(self.fp, fn_lfp)
            self.cfg.params[self.cfg.cal_path] = os.path.join(self.fp, fn_wht)

            # create folder (if it doesn't already exist)
            mkdir_p(os.path.splitext(self.cfg.params[self.cfg.lfp_path])[0])

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
            self.cfg.params[self.cfg.lfp_path] = os.path.join(self.fp, fn_lfp)
            self.cfg.params[self.cfg.cal_path] = os.path.join(self.fp, fn_wht)
            self.cfg.params[self.cfg.cal_meta] = os.path.splitext(self.cfg.params[self.cfg.cal_path])[0]+'.json'
            self.cfg.load_cal_data()

            # create folder (if it doesn't already exist)
            mkdir_p(os.path.splitext(self.cfg.params[self.cfg.lfp_path])[0])

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

    def test_viewer(self):

        import matplotlib as mpl
        if os.environ.get('DISPLAY', '') == '':
            print('Display not found. Using non-interactive Agg backend.')
            mpl.use('Agg')

        try:
            import tkinter as tk
        except ImportError:
            import Tkinter as tk

        # dummy button with state key
        btn = {'state': 'normal'}

        # instantiate viewer
        self.view_frame = tk.Toplevel(padx=PX, pady=PY)  # open window
        self.view_frame.resizable(width=0, height=0)  # make window not resizable
        ViewWidget(self.view_frame, cfg=self.cfg, sta=self.sta, btn=btn).pack(expand="no", fill="both")

        # close frame
        self.view_frame.destroy()

        return True


if __name__ == '__main__':
    unittest.main()
