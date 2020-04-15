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
from zipfile import ZipFile
import pickle
import os

from plenopticam.lfp_reader import LfpReader
from plenopticam.lfp_calibrator import LfpCalibrator, CaliFinder
from plenopticam.lfp_aligner import LfpAligner
from plenopticam.lfp_extractor import LfpExtractor
from plenopticam.lfp_refocuser import LfpRefocuser
from plenopticam.cfg.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus, mkdir_p, load_img_file


class PlenoptiCamTester(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTester, self).__init__(*args, **kwargs)

    def setUp(self):

        # refer to folder containing data
        self.fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        mkdir_p(self.fp) if not os.path.exists(self.fp) else None

        # retrieve Lytro Illum data
        url = 'http://wp12283669.server-he.de/Xchange/illum_test_data.zip'
        archive_fn = os.path.join(self.fp, os.path.basename(url))
        self.download_data(url) if not os.path.exists(archive_fn) else None
        fnames_illum = [file for file in ZipFile(archive_fn).namelist() if file.startswith('caldata') or file.endswith('lfr')]
        self.extract_archive(os.path.join(self.fp, os.path.basename(url)), fnames_illum)

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
        self.test_illum()

    def download_data(self, url):
        ''' download plenoptic image data '''

        print('Downloading data ...')

        # establish internet connection for test data download
        try:
            r = requests.get(url)
        except requests.exceptions.ConnectionError:
            raise(Exception('Check your internet connection, which is required for downloading test data.'))

        with open(os.path.join(self.fp, os.path.basename(url)), 'wb') as f:
            f.write(r.content)

        print('Finished download of %s' % os.path.basename(url))

        return True

    def extract_archive(self, archive_fn, fname_list):
        ''' extract content from downloaded data '''

        with ZipFile(archive_fn) as z:
            for fn in z.namelist():
                if fn in fname_list:
                    z.extract(fn, self.fp)

        return True

    def test_illum(self):

        # instantiate config and status objects
        cfg = PlenopticamConfig()
        cfg.default_values()
        sta = PlenopticamStatus()

        # skip concole output message (prevent Travis from terminating due to reaching 4MB logfile size)
        cfg.params[cfg.opt_prnt] = True

        # use pre-loaded calibration dataset
        wht_list = [file for file in os.listdir(self.fp) if file.startswith('caldata')]
        lfp_list = [file for file in os.listdir(self.fp) if file.endswith(('lfr', 'lfp'))]

        cfg.params[cfg.cal_path] = os.path.join(self.fp, wht_list[0])

        for lfp_file in lfp_list:
            cfg.params[cfg.lfp_path] = os.path.join(self.fp, lfp_file)
            print(cfg.params[cfg.lfp_path])

            # decode light field image
            lfp_obj = LfpReader(cfg, sta)
            ret_val = lfp_obj.main()
            lfp_img = lfp_obj.lfp_img
            del lfp_obj

            self.assertEqual(True, ret_val)

            # create output data folder
            mkdir_p(cfg.exp_path, cfg.params[cfg.opt_prnt])

            if not cfg.cond_meta_file():
                # automatic calibration data selection
                obj = CaliFinder(cfg, sta)
                ret_val = obj.main()
                wht_img = obj.wht_bay
                del obj

                self.assertEqual(True, ret_val)

            meta_cond = not (os.path.exists(cfg.params[cfg.cal_meta]) and cfg.params[cfg.cal_meta].lower().endswith('json'))
            if meta_cond or cfg.params[cfg.opt_cali]:
                # perform centroid calibration
                cal_obj = LfpCalibrator(wht_img, cfg, sta)
                ret_val = cal_obj.main()
                cfg = cal_obj.cfg
                del cal_obj

                self.assertEqual(True, ret_val)

            # load calibration data
            cfg.load_cal_data()

            #  check if light field alignment has been done before
            if cfg.cond_lfp_align():
                # align light field
                lfp_obj = LfpAligner(lfp_img, cfg, sta, wht_img)
                ret_val = lfp_obj.main()
                lfp_obj = lfp_obj.lfp_img
                del lfp_obj

                self.assertEqual(True, ret_val)

            # load previously computed light field alignment
            with open(os.path.join(cfg.exp_path, 'lfp_img_align.pkl'), 'rb') as f:
                lfp_img_align = pickle.load(f)

            # extract viewpoint data
            CaliFinder(cfg).main()
            obj = LfpExtractor(lfp_img_align, cfg=cfg, sta=sta)
            ret_val = obj.main()
            vp_img_arr = obj.vp_img_arr
            del obj

            self.assertEqual(True, ret_val)

            # do refocusing
            if cfg.params[cfg.opt_refo]:
                obj = LfpRefocuser(vp_img_arr, cfg=cfg, sta=sta)
                ret_val = obj.main()
                del obj

            self.assertEqual(True, ret_val)

        return True

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
