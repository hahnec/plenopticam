#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2019 Christopher Hahne <info@christopherhahne.de>

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

# external libs
import numpy as np

from plenopticam.lfp_extractor import LfpViewpoints
from plenopticam.lfp_aligner.cfa_processor import CfaProcessor
from plenopticam import misc

try:
    from scipy.signal import medfilt
    from scipy.ndimage import median_filter
except ImportError:
    raise ImportError('Please install scipy package.')

from color_matcher import ColorMatcher


class LfpColorEqualizer(LfpViewpoints):

    def __init__(self, *args, **kwargs):
        super(LfpColorEqualizer, self).__init__(*args, **kwargs)

        self._ref_img = kwargs['ref_img'] if 'ref_img' in kwargs else self.central_view
        self.prop_type = kwargs['prop_type'] if 'prop_type' in kwargs else 'central'
        self._method = 'mvgd'

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # apply color correction
        if self.vp_img_arr is not None:
            self.apply_ccm()
            self._ref_img = self.central_view

        # equalize light field colors
        if self.prop_type == 'central':
            self.proc_vp_arr(fun=self.color_eq_img, ref=self._ref_img, method=self._method, msg='Color equalization')
        elif self.prop_type == 'axial':
            self.proc_ax_propagate_2d(fun=self.color_eq_img, method=self._method, msg='Color equalization')

        # zero-out marginal sub-apertures (e.g. suffering from cross-talk)
        self._exclude_crosstalk_views()

    @staticmethod
    def color_eq_img(src, ref, method=None):

        # instantiate color matcher
        match = ColorMatcher(src, ref, method=method).main()

        return match

    def apply_ccm(self):

        # color matrix correction
        if 'ccm' in self.cfg.lfpimg.keys():

            # ccm mat selection
            if 'ccm_wht' in self.cfg.lfpimg:
                ccm_arr = self.cfg.lfpimg['ccm_wht']
            elif 'ccm' in self.cfg.lfpimg:
                #ccm_arr = self.cfg.lfpimg['ccm']
                ccm_arr = np.array([2.4827811717987061, -1.1018080711364746, -0.38097298145294189,
                                    -0.36761483550071716, 1.6667767763137817, -0.29916191101074219,
                                    -0.18722048401832581, -0.73317205905914307, 1.9203925132751465])
            else:
                ccm_arr = np.diag(np.ones(3))

            # normalize
            self.vp_img_arr /= self.vp_img_arr.max()

            if 'exp' in self.cfg.lfpimg:
                sat_lev = 2 ** (-self.cfg.lfpimg['exp'])
            else:
                sat_lev = 1
            self.vp_img_arr *= sat_lev

            # transpose and flip ccm_mat for RGB order
            ccm_mat = np.reshape(ccm_arr, (3, 3)).T
            self._vp_img_arr = CfaProcessor().correct_color(self._vp_img_arr.copy(), ccm_mat=ccm_mat)

            # remove potential NaNs
            self._vp_img_arr[self._vp_img_arr < 0] = 0
            self._vp_img_arr[self._vp_img_arr > sat_lev] = sat_lev
            #self._vp_img_arr /= sat_lev
            self._vp_img_arr /= self._vp_img_arr.max()

        return True

    def _exclude_crosstalk_views(self):
        """ function wrapper to exclude Lytro Illum views that suffer from cross-talk """

        self.circular_view_aperture(offset=2, ellipse=True)
