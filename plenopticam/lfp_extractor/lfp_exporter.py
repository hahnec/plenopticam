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
from plenopticam import misc
from plenopticam.lfp_reader.cfa_processor import CfaProcessor
from plenopticam.lfp_extractor.lfp_viewpoints import LfpViewpoints
from plenopticam.lfp_extractor.lfp_contrast import LfpContrast


# external libs
import os
import numpy as np


class LfpExporter(LfpViewpoints):

    def __init__(self, refo_stack=None, *args, **kwargs):
        super(LfpExporter, self).__init__(*args, **kwargs)

        self.refo_stack = np.asarray(refo_stack) if refo_stack else None

        # gamma correction
        if hasattr(self, 'cfg'):
            self.cfg.lfpimg['gam'] = 1./2.2
            gamma = self.cfg.lfpimg['gam'] if self.cfg.lfpimg and 'gam' in self.cfg.lfpimg.keys() else 1/2.2
            self.vp_img_arr = CfaProcessor().correct_gamma(img=self.vp_img_arr, gamma=gamma)
            self.refo_stack = CfaProcessor().correct_gamma(img=self.refo_stack, gamma=gamma)

    def write_viewpoint_data(self):

        # write central view as thumbnail image
        self.export_thumbnail(type='png')

        # write viewpoint image files to hard drive
        self.export_viewpoints(type='png')

        # write viewpoints as single image
        self.export_vp_stack(type='png')

        # write viewpoint gif animation
        self.gif_vp_img(duration=.1)

        return True

    def export_thumbnail(self, type='tiff'):

        # export central viewpoint as thumbnail image
        fp = os.path.join(self.cfg.exp_path, 'thumbnail')
        misc.save_img_file(self.central_view, file_path=fp, file_type=type)

        return True

    def export_viewpoints(self, type='tiff'):

        # print status
        self.sta.status_msg('Write viewpoint images', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        ptc_leng = self.cfg.params[self.cfg.ptc_leng]

        # create folder
        folderpath = os.path.join(self.cfg.exp_path, 'viewpoints_'+str(ptc_leng)+'px')
        misc.mkdir_p(folderpath)

        # normalize image array to 16-bit unsigned integer
        vp_img_arr = misc.Normalizer(self.vp_img_arr).uint16_norm()

        # export viewpoint images as image files
        for j in range(ptc_leng):
            for i in range(ptc_leng):

                misc.save_img_file(vp_img_arr[j, i], os.path.join(folderpath, str(j) + '_' + str(i)), file_type=type)

                # print status
                percentage = (((j*self._M+i+1)/self._M**2)*100)
                self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

        return True

    def export_vp_stack(self, type='tiff'):

        # print status
        self.sta.status_msg('Write viewpoint image stack', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # export all viewpoints in single image
        views_stacked_path = os.path.join(self.cfg.exp_path, 'views_stacked_img_'+str(self._M)+'px')
        misc.save_img_file(misc.img_resize(self.views_stacked_img, 1/self._M),
                           file_path=views_stacked_path, file_type=type)

        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def export_refo_stack(self, file_type=None):

        # print status
        self.sta.status_msg('Write refocused images', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        refo_stack = misc.Normalizer(np.asarray(self.refo_stack)).uint16_norm()
        if self.cfg.params[self.cfg.opt_refi]:
            a_list = np.arange(*np.array(self.cfg.params[self.cfg.ran_refo]) * self.cfg.params[self.cfg.ptc_leng])
            a_list = a_list / self.cfg.params[self.cfg.ptc_leng]
        else:
            a_list = range(*self.cfg.params[self.cfg.ran_refo])

        # create folder
        string = 'subpixel_' if self.cfg.params[self.cfg.opt_refi] else ''
        folder_path = os.path.join(self.cfg.exp_path, 'refo_' + string + str(self._M) + 'px')
        misc.mkdir_p(folder_path)

        for i, refo_img in enumerate(refo_stack):

            # get depth plane number for filename
            a = a_list[i]

            self.save_refo_slice(a, refo_img, folder_path, file_type=file_type)

            # print status
            percentage = ((i+1) / len(refo_stack)) * 100
            self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

        return True

    def save_refo_slice(self, a, refo_img, folder_path=None, file_type=None, string=None):

        string = 'subpixel_' if self.cfg.params[self.cfg.opt_refi] and string is None else string

        if folder_path is None:
            folder_path = os.path.join(self.cfg.exp_path, 'refo_' + string + str(self._M) + 'px')
            misc.mkdir_p(folder_path)

        # account for sub-pixel precise depth value
        a = round(float(a) / self._M, 2) if self.cfg.params[self.cfg.opt_refi] else a

        # gamma correction
        gamma = self.cfg.lfpimg['gam'] if self.cfg.lfpimg and 'gam' in self.cfg.lfpimg.keys() else 1.
        refo_img **= gamma

        # write image file
        misc.save_img_file(refo_img, os.path.join(folder_path, str(a)), file_type=file_type)

        return True

    def gif_vp_img(self, duration, pattern='circle'):

        lf_radius = min(int((max(self.cfg.calibs[self.cfg.ptc_mean])+1)//4), self._C)
        fn = 'view_animation_' + str(lf_radius*2+1) + 'px'
        img_set = self.reorder_vp_arr(pattern=pattern, lf_radius=lf_radius)
        img_set = misc.Normalizer(img_set, dtype=self.vp_img_arr.dtype).uint8_norm()
        misc.save_gif(img_set, duration=duration, fp=self.cfg.exp_path, fn=fn)

        return True

    def gif_refo(self):

        # export gif animation
        fn = 'refocus_animation_' + str(self.cfg.params[self.cfg.ptc_leng]) + 'px'
        refo_stack = misc.Normalizer(np.asarray(self.refo_stack)).uint8_norm()
        refo_stack = np.concatenate((refo_stack, refo_stack[::-1]), axis=0)      # play forward and backwards
        misc.save_gif(refo_stack, duration=.5, fp=self.cfg.exp_path, fn=fn)

        return True
