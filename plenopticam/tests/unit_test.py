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

import requests
import zipfile
import io
import os

from plenopticam.lfp_calibrator import LfpCalibrator
from plenopticam.lfp_aligner import LfpAligner
from plenopticam.lfp_extractor import LfpExtractor
from plenopticam.cfg.cfg import Config
from plenopticam import misc

class PlenoptiCamTester(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTester, self).__init__()

    def setUp(self):

        self.fp = os.path.join(os.getcwd(), 'data')
        self.fnames_wht = ['f197with4m11pxf16Final.bmp', 'f197Inf9pxFinalShift12.7cmf22.bmp']
        self.fnames_lfp = ['f197with4m11pxFinal.bmp', 'f197Inf9pxFinalShift12.7cm.bmp']

        # url path to dataset from Hahne et al. @ OpEx Figshare
        url = 'https://ndownloader.figshare.com/files/5201452'

        for fn in self.fnames_wht:
            if not os.path.exists(os.path.join(self.fp, fn)):
                self.download_data(url)

        self.runTest()

    def runTest(self):

        self.test_cal()
        self.test_lfp()

    def download_data(self, url):
        ''' download plenoptic image data '''

        print('Downloading data ...')

        # establish internet connection for test data download
        try:
            request = requests.get(url)
        except requests.exceptions.ConnectionError:
            raise(Exception('Check your internet connection, which is required for downloading test data.'))

        # extract content from downloaded data
        file = zipfile.ZipFile(io.BytesIO(request.content))
        for fn in file.namelist():
            file.extract(fn, self.fp)

        print('Progress: Finished')

        return True

    def test_cal(self):

        # set config for unit test purposes
        cfg = Config()
        cfg.params[cfg.opt_dbug] = True

        for fn_lfp, fn_wht in zip(self.fnames_lfp, self.fnames_wht):

            # update file paths and calibration data in config
            cfg.params[cfg.lfp_path] = os.path.join(self.fp, fn_lfp)
            cfg.params[cfg.cal_path] = os.path.join(self.fp, fn_wht)

            # create folder (if it doesn't already exist)
            misc.mkdir_p(os.path.splitext(cfg.params[cfg.lfp_path])[0])

            # test light field calibration
            wht_img = misc.load_img_file(cfg.params[cfg.cal_path])
            cal_obj = LfpCalibrator(wht_img=wht_img, cfg=cfg, sta=None)
            ret_val = cal_obj.main()
            del cal_obj

            # assertion
            self.assertEqual(True, ret_val)

    def test_lfp(self):

        # set config for unit test purposes
        cfg = Config()
        cfg.params[cfg.opt_dbug] = True

        for fn_lfp, fn_wht in zip(self.fnames_lfp, self.fnames_wht):

            # update file paths and calibration data in config
            cfg.params[cfg.lfp_path] = os.path.join(self.fp, fn_lfp)
            cfg.params[cfg.cal_path] = os.path.join(self.fp, fn_wht)
            cfg.params[cfg.cal_meta] = os.path.splitext(cfg.params[cfg.cal_path])[0]+'.json'
            cfg.load_cal_data()

            # create folder (if it doesn't already exist)
            misc.mkdir_p(os.path.splitext(cfg.params[cfg.lfp_path])[0])

            # test light field alignment
            lfp_img = misc.load_img_file(cfg.params[cfg.lfp_path])
            lfp_obj = LfpAligner(lfp_img=lfp_img, cfg=cfg, sta=None)
            ret_val = lfp_obj.main()
            lfp_img = lfp_obj.lfp_img
            del lfp_obj

            # assertion
            self.assertEqual(True, ret_val)

            # test light field extraction
            lfp_obj = LfpExtractor(lfp_img_align=lfp_img, cfg=cfg, sta=None)
            ret_val = lfp_obj.main()
            del lfp_obj

            # assertion
            self.assertEqual(True, ret_val)


if __name__ == '__main__':
    unittest.main()
