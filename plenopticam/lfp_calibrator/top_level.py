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

# external
from color_space_converter import rgb2gry


# local imports
from plenopticam.lfp_calibrator.pitch_estimator import PitchEstimator
from plenopticam.lfp_calibrator.centroid_extractor import CentroidExtractor
from plenopticam.lfp_calibrator.centroid_refiner import CentroidRefiner
from plenopticam.lfp_calibrator.centroid_sorter import CentroidSorter
from plenopticam.lfp_calibrator.centroid_drawer import CentroidDrawer
from plenopticam.lfp_calibrator.grid_fitter import GridFitter
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc.status import PlenopticamStatus
from plenopticam.lfp_aligner.cfa_processor import CfaProcessor
from plenopticam.cfg import constants as c


class LfpCalibrator(object):

    def __init__(self, wht_img, cfg=None, sta=None):

        # input variables
        self._wht_img = wht_img
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else PlenopticamStatus()

        # private
        self._M = None

    def main(self):

        if self._wht_img is None:
            self.sta.status_msg(msg='White image file not present', opt=self.cfg.params[self.cfg.opt_prnt])
            self.sta.error = True

        # convert Bayer to RGB representation
        if len(self._wht_img.shape) == 2 and 'bay' in self.cfg.lfpimg:
            # perform color filter array management and obtain rgb image
            cfa_obj = CfaProcessor(bay_img=self._wht_img, cfg=self.cfg, sta=self.sta)
            cfa_obj.bay2rgb()
            self._wht_img = cfa_obj.rgb_img
            del cfa_obj

        # ensure white image is monochromatic
        if len(self._wht_img.shape) == 3:
            self._wht_img = rgb2gry(self._wht_img)[..., 0] if self._wht_img.shape[-1] == 3 else self._wht_img

        # estimate micro image diameter
        obj = PitchEstimator(self._wht_img, self.cfg, self.sta)
        obj.main()
        self._M = obj.M if self._M is None else self._M
        del obj

        # compute all centroids of micro images
        obj = CentroidExtractor(self._wht_img, self.cfg, self.sta, self._M)
        obj.main()
        centroids = obj.centroids
        peak_img = obj.peak_img
        del obj

        # refine centroids with sub-pixel precision using provided method
        obj = CentroidRefiner(peak_img, centroids, self.cfg, self.sta, self._M, self.cfg.params[self.cfg.cal_meth])
        obj.main()
        centroids = obj.centroids_refined
        del obj

        # reorder MICs and assign indices based on the detected MLA pattern
        obj = CentroidSorter(centroids, self.cfg, self.sta)
        obj.main()
        mic_list, pattern, pitch = obj.mic_list, obj.pattern, obj.pitch
        del obj

        # fit grid of MICs using least-squares method to obtain accurate MICs from line intersections
        if self.cfg.params[self.cfg.cal_meth] == c.CALI_METH[2] and not self.sta.interrupt:
            self.cfg.calibs[self.cfg.pat_type] = pattern
            obj = GridFitter(coords_list=mic_list, cfg=self.cfg, sta=self.sta)
            obj.main()
            mic_list = obj.grid_fit
            del obj

        # save calibration metadata
        self.sta.status_msg('Save calibration data', opt=self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, opt=self.cfg.params[self.cfg.opt_prnt])
        try:
            self.cfg.save_cal_data(mic_list=mic_list, pat_type=pattern, ptc_mean=pitch)
            self.sta.progress(100, opt=self.cfg.params[self.cfg.opt_prnt])
        except PermissionError:
            self.sta.status_msg('Could not save calibration data', opt=self.cfg.params[self.cfg.opt_prnt])

        # write image to hard drive (only if debug option is set)
        if self.cfg.params[self.cfg.opt_dbug]:
            draw_obj = CentroidDrawer(self._wht_img, mic_list, self.cfg, self.sta)
            draw_obj.write_centroids_img(fn='wht_img+mics_sorted.png')
            del draw_obj

        return True
