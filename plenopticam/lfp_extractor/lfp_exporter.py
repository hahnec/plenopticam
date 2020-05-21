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
from plenopticam.lfp_extractor.lfp_viewpoints import LfpViewpoints


# external libs
import os
import numpy as np
from color_space_converter import rgb2gry


class LfpExporter(LfpViewpoints):

    def __init__(self, refo_stack=None, *args, **kwargs):
        super(LfpExporter, self).__init__(*args, **kwargs)

        self.refo_stack = np.asarray(refo_stack) if refo_stack is not None else None

    def write_viewpoint_data(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # write central view as thumbnail image
        self.export_thumbnail(type='png')

        # write viewpoint image files to hard drive
        self.export_viewpoints(type='png')

        # write viewpoints as single image
        if self.cfg.params[self.cfg.opt_dbug]:
            self.export_vp_stack(type='png')

        # write viewpoint gif animation
        self.gif_vp_img(duration=.1)

        return True

    def export_thumbnail(self, type='tiff'):

        thumb = misc.Normalizer(self.central_view.copy()).type_norm()

        # export central viewpoint as thumbnail image
        fp = os.path.join(self.cfg.exp_path, 'thumbnail')
        misc.save_img_file(thumb, file_path=fp, file_type=type, tag=self.cfg.params[self.cfg.opt_dbug])

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

                misc.save_img_file(vp_img_arr[j, i], os.path.join(folderpath, str(j) + '_' + str(i)),
                                   file_type=type, tag=self.cfg.params[self.cfg.opt_dbug])

                # print status
                percentage = (((j*self._M+i+1)/self._M**2)*100)
                self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

                if self.sta.interrupt:
                    return False

        return True

    def export_vp_stack(self, type='png', downscale=None):
        """ write viewpoint images stitched to together in a single image """

        # print status
        self.sta.status_msg('Write viewpoint image stack', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # downscale image
        downscale = True if downscale is None else downscale
        views_stacked_img = misc.img_resize(self.views_stacked_img.copy(), 1 / self._M) \
            if downscale else self.views_stacked_img.copy()

        # normalization
        p_lo = np.percentile(rgb2gry(self.central_view), 0.05)
        p_hi = np.percentile(rgb2gry(self.central_view), 99.995)
        views_stacked_img = misc.Normalizer(views_stacked_img, min=p_lo, max=p_hi).uint8_norm()

        # export all viewpoints in single image
        views_stacked_path = os.path.join(self.cfg.exp_path, 'views_stacked_img_' + str(self._M) + 'px')
        misc.save_img_file(views_stacked_img, file_path=views_stacked_path, file_type=type)

        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def export_refo_stack(self, file_type=None):

        # print status
        self.sta.status_msg('Write refocused images', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        refo_stack = misc.Normalizer(self.refo_stack).uint16_norm()
        if self.cfg.params[self.cfg.opt_refi]:
            a_list = np.arange(*np.array(self.cfg.params[self.cfg.ran_refo]) * self.cfg.params[self.cfg.ptc_leng])
            a_list = np.round(a_list / self.cfg.params[self.cfg.ptc_leng], 2)
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

        # write image file
        misc.save_img_file(refo_img, os.path.join(folder_path, str(a)), file_type=file_type)

        return True

    def gif_vp_img(self, duration, pattern='circle'):

        # micro image size estimate
        M = max(self.cfg.calibs[self.cfg.ptc_mean]) if self.cfg.calibs else self.cfg.params[self.cfg.ptc_leng]

        # filter images forming a pattern
        lf_radius = min(int((M+1)//4), self._C)
        img_set = self.reorder_vp_arr(pattern=pattern, lf_radius=lf_radius)

        # image normalization
        img_set = misc.Normalizer(img_set).uint8_norm()

        # export gif animation
        fn = 'view_animation_' + str(lf_radius * 2 + 1) + 'px'
        misc.save_gif(img_set, duration=duration, fp=self.cfg.exp_path, fn=fn)

        return True

    def gif_refo(self):

        # image normalization
        refo_stack = misc.Normalizer(self.refo_stack).uint8_norm()

        # append reversed array copy to play forward and backwards
        refo_stack = np.concatenate((refo_stack, refo_stack[::-1]), axis=0)

        # export gif animation
        fn = 'refocus_animation_' + str(self.cfg.params[self.cfg.ptc_leng]) + 'px'
        misc.save_gif(refo_stack, duration=.5, fp=self.cfg.exp_path, fn=fn)

        return True
