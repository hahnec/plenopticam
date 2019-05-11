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

# external libs
import os

def export_viewpoints(vp_img_arr, cfg, type='tiff'):

    ptc_leng = cfg.params[cfg.ptc_leng]

    # create folder
    folderpath = os.path.join(cfg.params[cfg.lfp_path].split('.')[0], 'viewpoints_' + str(ptc_leng) + 'px')
    misc.mkdir_p(folderpath)

    # normalize image array to 16-bit unsigned integer
    vp_img_arr = misc.uint16_norm(vp_img_arr)

    # export viewpoint images as image files
    for j in range(ptc_leng):
        for i in range(ptc_leng):

            misc.save_img_file(vp_img_arr[j, i], os.path.join(folderpath, str(j) + '_' + str(i)), type=type)

    return True

def export_refo_stack(refo_stack, cfg, type='tiff'):

    refo_stack = misc.uint16_norm(refo_stack)

    patch_len = cfg.params[cfg.ptc_leng]

    # create folder
    string = ''
    if cfg.params[cfg.opt_refo] == 2 or cfg.params[cfg.opt_refi]:
        string = 'subpixel_'
    elif cfg.params[cfg.opt_refo] == 1 or cfg.params[cfg.opt_view]:
        string = ''

    folder_path = os.path.join(cfg.params[cfg.lfp_path].split('.')[0], 'refo_' + string + str(patch_len) + 'px')
    misc.mkdir_p(folder_path)

    for i, refo_img in enumerate(refo_stack):

        # write image file
        misc.save_img_file(refo_img, str(range(*cfg.params[cfg.ran_refo])[i]), type=type)

    return True

def gif_vp_img(vp_img_arr, duration, fp='', fn='', pattern='circle'):

    dims = vp_img_arr.shape[:2]
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

    misc.save_gif(img_set, duration, fp, fn)

    return True