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
from plenopticam.misc.data_proc import rgb2gray
from plenopticam.lfp_calibrator.pitch_estimator import PitchEstimator
from plenopticam.lfp_calibrator.centroid_extractor import CentroidExtractor
from plenopticam.lfp_calibrator.centroid_sorter import CentroidSorter
from plenopticam.lfp_calibrator.centroid_drawer import CentroidDrawer
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc.status import PlenopticamStatus


class LfpCalibrator(object):

    def __init__(self, wht_img, cfg=None, sta=None, M=None):

        # input variables
        self._wht_img = wht_img
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else PlenopticamStatus()
        self._M = M

    def main(self):

        # ensure white image is monochromatic
        self._wht_img = rgb2gray(self._wht_img) if len(self._wht_img.shape) is 3 else self._wht_img

        # estimate micro image diameter
        obj = PitchEstimator(self._wht_img, self.cfg, self.sta)
        obj.main()
        self._M = obj.M if not self._M else self._M
        del obj

        # compute all centroids of micro images
        obj = CentroidExtractor(self._wht_img, self.cfg, self.sta, self._M)
        obj.main()
        centroids = obj.centroids
        del obj

        # write micro image center image to hard drive if debug option is set
        if not self.sta.interrupt:
            CentroidDrawer(self._wht_img, centroids, self.cfg).write_centroids_img(fn='wht_img+mics_unsorted.png')

        # reorder MICs and assign indices based on the detected MLA pattern
        obj = CentroidSorter(centroids, self.cfg, self.sta)
        obj.main()
        mic_list, pattern, pitch = obj.mic_list, obj.pattern, obj.pitch
        del obj

        # save calibration metadata
        self.sta.status_msg('Save calibration data', opt=self.cfg.params[self.cfg.opt_dbug])
        self.sta.progress(None, opt=self.cfg.params[self.cfg.opt_dbug])
        try:
            self.cfg.save_cal_data(mic_list=mic_list, pat_type=pattern, ptc_mean=pitch)
        except:
            self.sta.status_msg('Could not save calibration data', opt=self.cfg.params[self.cfg.opt_dbug])

        # write image to hard drive if debug option is set
        if not self.sta.interrupt:
            CentroidDrawer(self._wht_img, mic_list, self.cfg).write_centroids_img(fn='wht_img+mics_sorted.png')

        # print status
        self.sta.status_msg('Finished calibration', opt=True)
        self.sta.progress(100, opt=True)

        return True
