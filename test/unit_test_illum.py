#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "inbox@christopherhahne.de"
__license__ = """
    Copyright (c) 2020 Christopher Hahne <inbox@christopherhahne.de>

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

from zipfile import ZipFile
import pickle
import os

from plenopticam.lfp_reader import LfpReader
from plenopticam.lfp_calibrator import LfpCalibrator, CaliFinder, CentroidDrawer
from plenopticam.lfp_aligner import LfpAligner
from plenopticam.lfp_extractor import LfpExtractor
from plenopticam.lfp_refocuser import LfpRefocuser
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus, mkdir_p
from test.unit_test_baseclass import PlenoptiCamTester


class PlenoptiCamTesterIllum(PlenoptiCamTester):

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTesterIllum, self).__init__(*args, **kwargs)

    def setUp(self):

        # retrieve Lytro Illum data
        url = 'http://wp12283669.server-he.de/Xchange/illum_test_data.zip'
        archive_fn = os.path.join(self.fp, os.path.basename(url))
        self.download_data(url) if not os.path.exists(archive_fn) else None
        fnames_illum = [file for file in ZipFile(archive_fn).namelist() if file.startswith('caldata') or file.endswith('lfr')]
        self.extract_archive(os.path.join(self.fp, os.path.basename(url)), fnames_illum)

    def test_illum(self):

        # instantiate config and status objects
        cfg = PlenopticamConfig()
        cfg.default_values()
        sta = PlenopticamStatus()

        # enable options in config to test more algorithms
        cfg.params[cfg.cal_meth] = 'grid-fit'
        cfg.params[cfg.opt_vign] = True
        cfg.params[cfg.opt_rota] = True
        cfg.params[cfg.opt_refi] = True
        cfg.params[cfg.opt_pflu] = True
        cfg.params[cfg.opt_arti] = True
        cfg.params[cfg.opt_lier] = True
        cfg.params[cfg.opt_cont] = True
        cfg.params[cfg.opt_awb_] = True
        cfg.params[cfg.opt_sat_] = True
        cfg.params[cfg.ran_refo] = [0, 1]

        # compute 3x3 viewpoints only (to reduce computation time)
        cfg.params[cfg.ptc_leng] = 3

        # skip progress prints (prevent Travis from terminating due to reaching 4MB logfile size)
        sta.prog_opt = False

        # print current process message (to prevent Travis from stopping after 10 mins)
        cfg.params[cfg.opt_prnt] = True

        # use pre-loaded calibration dataset
        wht_list = [file for file in os.listdir(self.fp) if file.startswith('caldata')]
        lfp_list = [file for file in os.listdir(self.fp) if file.endswith(('lfr', 'lfp'))]

        cfg.params[cfg.cal_path] = os.path.join(self.fp, wht_list[0])

        for lfp_file in lfp_list:

            cfg.params[cfg.lfp_path] = os.path.join(self.fp, lfp_file)
            print('\nCompute image %s' % os.path.basename(cfg.params[cfg.lfp_path]))

            # decode light field image
            obj = LfpReader(cfg, sta)
            ret = obj.main()

            # use third of original image size (to prevent Travis from stopping due to memory error)
            crop_h, crop_w = obj.lfp_img.shape[0] // 3, obj.lfp_img.shape[1] // 3
            crop_h, crop_w = crop_h + crop_h % 2, crop_w + crop_w % 2   # use even number for correct Bayer arrangement
            lfp_img = obj.lfp_img[crop_h:-crop_h, crop_w:-crop_w]
            del obj

            self.assertEqual(True, ret)

            # create output data folder
            mkdir_p(cfg.exp_path, cfg.params[cfg.opt_prnt])

            if not cfg.cond_meta_file():
                # automatic calibration data selection
                obj = CaliFinder(cfg, sta)
                ret = obj.main()
                wht_img = obj.wht_bay[crop_h:-crop_h, crop_w:-crop_w] if obj.wht_bay is not None else obj.wht_bay
                del obj

                self.assertEqual(True, ret)

            meta_cond = not (os.path.exists(cfg.params[cfg.cal_meta]) and cfg.params[cfg.cal_meta].lower().endswith('json'))
            if meta_cond or cfg.params[cfg.opt_cali]:
                # perform centroid calibration
                obj = LfpCalibrator(wht_img, cfg, sta)
                ret = obj.main()
                cfg = obj.cfg
                del obj

                self.assertEqual(True, ret)

            # load calibration data
            cfg.load_cal_data()

            # write centroids as png file
            if wht_img is not None:
                obj = CentroidDrawer(wht_img, cfg.calibs[cfg.mic_list], cfg)
                ret = obj.write_centroids_img(fn=os.path.join(cfg.exp_path, 'wht_img+mics.png'))
                del obj

                self.assertEqual(True, ret)

            #  check if light field alignment has been done before
            if cfg.cond_lfp_align():
                # align light field
                obj = LfpAligner(lfp_img, cfg, sta, wht_img)
                ret = obj.main()
                del obj

                self.assertEqual(True, ret)

            # load previously computed light field alignment
            with open(os.path.join(cfg.exp_path, 'lfp_img_align.pkl'), 'rb') as f:
                lfp_img_align = pickle.load(f)

            # extract viewpoint data
            CaliFinder(cfg).main()
            obj = LfpExtractor(lfp_img_align, cfg=cfg, sta=sta)
            ret = obj.main()
            vp_img_arr = obj.vp_img_arr
            del obj

            self.assertEqual(True, ret)

            # do refocusing
            if cfg.params[cfg.opt_refo]:
                obj = LfpRefocuser(vp_img_arr, cfg=cfg, sta=sta)
                ret = obj.main()
                del obj

            self.assertEqual(True, ret)

        return True


if __name__ == '__main__':
    unittest.main()
