#!/usr/bin/env python
from math import sqrt, atan2

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
from plenopticam.misc import Normalizer
from plenopticam.lfp_extractor.lfp_viewpoints import LfpViewpoints

# external libs
import os
import numpy as np

class LfpExporter(LfpViewpoints):

    def __init__(self, refo_stack=None, *args, **kwargs):
        super(LfpExporter, self).__init__(*args, **kwargs)

        self._refo_stack = refo_stack

    def write_viewpoint_data(self):

        # write central view as thumbnail image
        self.export_thumbnail(type='png')

        # write viewpoint image files to hard drive
        self.export_viewpoints(type='png')

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
        vp_img_arr = Normalizer(self.vp_img_arr).uint16_norm()

        # export viewpoint images as image files
        for j in range(ptc_leng):
            for i in range(ptc_leng):

                misc.save_img_file(vp_img_arr[j, i], os.path.join(folderpath, str(j) + '_' + str(i)), file_type=type)

                # print status
                percentage = (((j*self._M+i+1)/self._M**2)*100)
                self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

        return True

    def gif_vp_img(self, duration, pattern='circle'):

        fn = 'view_animation_' + str(self.cfg.params[self.cfg.ptc_leng]) + 'px'

        vp_img_arr = Normalizer(self._vp_img_arr).uint8_norm()
        dims = self._vp_img_arr.shape[:2]
        r = int(min(dims)/2)
        mask = [[0] * dims[1] for _ in range(dims[0])]

        if pattern == 'square':
            mask[0, :] = 1
            mask[:, 0] = 1
            mask[-1, :] = 1
            mask[:, -1] = 1
        if pattern == 'circle':
            for x in range(-r, r+1):
                for y in range(-r, r+1):
                    if int(sqrt(x**2 + y**2)) == r:
                        mask[y+r][x+r] = 1

        # extract coordinates from mask
        coords_table = [(y, x) for y in range(len(mask)) for x in range(len(mask)) if mask[y][x]]

        # sort coordinates in angular order
        coords_table.sort(key=lambda coords: atan2(coords[0]-r, coords[1]-r))

        img_set = []
        for coords in coords_table:
                img_set.append(vp_img_arr[coords[0], coords[1], :, :, :])

        misc.save_gif(img_set, duration=duration, fp=self.cfg.exp_path, fn=fn)

        return True

    def export_refo_stack(self, type=None):

        # print status
        self.sta.status_msg('Write refocused images', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        refo_stack = Normalizer(np.asarray(self._refo_stack)).uint16_norm()

        # create folder
        string = ''
        if self.cfg.params[self.cfg.opt_refo] == 2 or self.cfg.params[self.cfg.opt_refi]:
            string = 'subpixel_'
        elif self.cfg.params[self.cfg.opt_refo] == 1 or self.cfg.params[self.cfg.opt_view]:
            string = ''

        folder_path = os.path.join(self.cfg.exp_path, 'refo_' + string + str(self._M) + 'px')
        misc.mkdir_p(folder_path)

        for i, refo_img in enumerate(refo_stack):

            # get depth plane number for filename
            a = range(*self.cfg.params[self.cfg.ran_refo])[i]
            # account for sub-pixel precise depth value
            a = round(float(a)/self._M, 2) if self.cfg.params[self.cfg.opt_refi] else a

            # write image file
            misc.save_img_file(refo_img, os.path.join(folder_path, str(a)), file_type=type)

            # print status
            percentage = (i / len(refo_stack)) * 100
            self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

        return True

    def gif_refo(self):

        # export gif animation
        fn = 'refocus_animation_' + str(self.cfg.params[self.cfg.ptc_leng]) + 'px'
        refo_stack = misc.Normalizer(np.asarray(self._refo_stack)).uint8_norm()
        refo_stack = np.concatenate((refo_stack, refo_stack[::-1]), axis=0)      # play forward and backwards
        misc.save_gif(refo_stack, duration=.5, fp=self.cfg.exp_path, fn=fn)

        return True
