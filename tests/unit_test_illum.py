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

import pickle
from os.path import join, exists, basename
from os import listdir

from plenopticam.lfp_reader import LfpReader
from plenopticam.lfp_calibrator import LfpCalibrator, CaliFinder, CentroidDrawer
from plenopticam.lfp_aligner import LfpAligner
from plenopticam.lfp_extractor import LfpExtractor
from plenopticam.lfp_refocuser import LfpRefocuser
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus, mkdir_p
from plenopticam.misc.data_downloader import DataDownloader


class PlenoptiCamTesterIllum(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTesterIllum, self).__init__(*args, **kwargs)

    def setUp(self):

        # instantiate config and status objects
        self.cfg = PlenopticamConfig()
        self.cfg.default_values()
        self.sta = PlenopticamStatus()

        # enable options in config to cover more algorithms in tests
        self.cfg.params[self.cfg.cal_meth] = 'grid-fit'
        self.cfg.params[self.cfg.opt_vign] = True
        self.cfg.params[self.cfg.opt_rota] = True
        self.cfg.params[self.cfg.opt_refi] = True
        self.cfg.params[self.cfg.opt_pflu] = True
        self.cfg.params[self.cfg.opt_arti] = True
        self.cfg.params[self.cfg.opt_lier] = True
        self.cfg.params[self.cfg.opt_cont] = True
        self.cfg.params[self.cfg.opt_awb_] = True
        self.cfg.params[self.cfg.opt_sat_] = True
        self.cfg.params[self.cfg.opt_dbug] = True
        self.cfg.params[self.cfg.opt_dpth] = True
        self.cfg.params[self.cfg.ran_refo] = [0, 1]

        # compute 3x3 viewpoints only (to reduce computation time)
        self.cfg.params[self.cfg.ptc_leng] = 7

        # skip progress prints (prevent Travis from terminating due to reaching 4MB logfile size)
        self.sta.prog_opt = False

        # print current process message (to prevent Travis from stopping after 10 mins)
        self.cfg.params[self.cfg.opt_prnt] = True

        # retrieve Lytro Illum data
        self.loader = DataDownloader(cfg=self.cfg, sta=self.sta)
        self.fp = join(self.loader.root_path, 'examples', 'data')
        archive_fn = join(self.fp, basename(self.loader.host_eu_url))
        self.loader.download_data(self.loader.host_eu_url, fp=self.fp) if not exists(archive_fn) else None
        self.loader.extract_archive(archive_fn, fname_list='lfr')

    def test_illum(self):

        # use pre-loaded calibration dataset
        wht_list = [file for file in listdir(self.fp) if file.startswith('caldata')]
        lfp_list = [file for file in listdir(self.fp) if file.endswith(('lfr', 'lfp'))]

        self.cfg.params[self.cfg.cal_path] = join(self.fp, wht_list[0])

        for lfp_file in lfp_list:

            self.cfg.params[self.cfg.lfp_path] = join(self.fp, lfp_file)
            print('\nCompute image %s' % basename(self.cfg.params[self.cfg.lfp_path]))

            # decode light field image
            obj = LfpReader(self.cfg, self.sta)
            ret = obj.main()

            # use third of original image size (to prevent Travis from stopping due to memory error)
            crop_h, crop_w = obj.lfp_img.shape[0] // 3, obj.lfp_img.shape[1] // 3
            crop_h, crop_w = crop_h + crop_h % 2, crop_w + crop_w % 2   # use even number for correct Bayer arrangement
            lfp_img = obj.lfp_img[crop_h:-crop_h, crop_w:-crop_w]
            del obj

            self.assertEqual(True, ret)

            # create output data folder
            mkdir_p(self.cfg.exp_path, self.cfg.params[self.cfg.opt_prnt])

            if not self.cfg.cond_meta_file():
                # automatic calibration data selection
                obj = CaliFinder(self.cfg, self.sta)
                ret = obj.main()
                wht_img = obj.wht_bay[crop_h:-crop_h, crop_w:-crop_w] if obj.wht_bay is not None else obj.wht_bay
                del obj

                self.assertEqual(True, ret)

            meta_cond = not (exists(self.cfg.params[self.cfg.cal_meta]) and self.cfg.params[self.cfg.cal_meta].lower().endswith('json'))
            if meta_cond or self.cfg.params[self.cfg.opt_cali]:
                # perform centroid calibration
                obj = LfpCalibrator(wht_img, self.cfg, self.sta)
                ret = obj.main()
                self.cfg = obj.cfg
                del obj

                self.assertEqual(True, ret)

            # load calibration data
            self.cfg.load_cal_data()

            # write centroids as png file
            if wht_img is not None:
                obj = CentroidDrawer(wht_img, self.cfg.calibs[self.cfg.mic_list], self.cfg)
                ret = obj.write_centroids_img(fn='testcase_wht_img+mics.png')
                del obj

                self.assertEqual(True, ret)

            #  check if light field alignment has been done before
            if self.cfg.cond_lfp_align():
                # align light field
                obj = LfpAligner(lfp_img, self.cfg, self.sta, wht_img)
                ret = obj.main()
                del obj

                self.assertEqual(True, ret)

            # load previously computed light field alignment
            with open(join(self.cfg.exp_path, 'lfp_img_align.pkl'), 'rb') as f:
                lfp_img_align = pickle.load(f)

            # extract viewpoint data
            CaliFinder(self.cfg).main()
            obj = LfpExtractor(lfp_img_align, cfg=self.cfg, sta=self.sta)
            ret = obj.main()
            vp_img_arr = obj.vp_img_linear
            del obj

            self.assertEqual(True, ret)

            # do refocusing
            if self.cfg.params[self.cfg.opt_refo]:
                obj = LfpRefocuser(vp_img_arr, cfg=self.cfg, sta=self.sta)
                ret = obj.main()
                del obj

            self.assertEqual(True, ret)

        return True

    def test_all(self):

        self.test_illum()


if __name__ == '__main__':
    unittest.main()
