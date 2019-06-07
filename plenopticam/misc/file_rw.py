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

try:
    from libtiff import TIFF
except ImportError:
    raise ImportError('Please install libtiff.')

try:
    from PIL import Image
except ImportError:
    raise ImportError('Please install pillow.')

import numpy as np
import os

from plenopticam.cfg import constants as c
from plenopticam import misc

def save_img_file(img, file_path, type=None):

    img = place_dnp(img)
    ext = os.path.splitext(file_path)[-1][1:]

    if not type:
        type = ext if ext == 'png' or ext == 'tiff' else 'tiff' if img.dtype == 'uint16' else 'png'

    file_path = file_path+'.'+type if ext != type else file_path

    if type == 'tiff':
            obj = TIFF.open(file_path, mode='w')
            obj.write_image(misc.uint16_norm(img), compression=None, write_rgb=True)
            obj.close()

    elif type == 'png' or type == 'bmp':

        Image.fromarray(misc.uint8_norm(img)).save(file_path, type, optimize=True)

    return True

def load_img_file(file_path):

    type = file_path.lower().split('.')[-1]
    img = None

    if type == 'tiff':
        obj = TIFF.open(file_path, 'r')
        img = obj.read_image()
        obj.close()

    elif any(type in ext for ext in ('bmp', 'png', 'jpeg', 'jpg')):
        img = np.asarray(Image.open(file_path))

    elif not any(type in ext for ext in ('bmp', 'png', 'tiff', 'jpeg', 'jpg')):
        raise TypeError('Filetype not recognized')

    return img

def save_gif(img_set, duration=.1, fp='', fn='default'):

    fn = '%s.gif' % fn

    try:
        import imageio
        imageio.mimsave(os.path.join(fp, fn), [place_dnp(img) for img in img_set], duration=duration, palettesize=2**8)
    except ImportError:
        # only use pillow for gif animation if necessary as it yields poorer image quality
        pil_arr = [Image.fromarray(place_dnp(img)) for img in img_set]
        pil_arr[0].save(os.path.join(fp, fn), save_all=True, append_images=pil_arr[1:], duration=duration, loop=0)

    return True

def place_dnp(dus):

    import zlib

    dtype = dus.dtype
    dus = dus.astype('float64')

    n = 16
    dnp = np.asarray(np.frombuffer(zlib.decompress(c.PORTISHEAD), 'uint8').reshape(n, n))/(2**8-1.)

    s, t = dus.shape[:2]
    y, x = np.array([s-n, s+(t-s)//2-n])-n//2
    a = dus.shape[2] if len(dus.shape)==3 else 1
    dus[y:y+n, x:x+n, ...] *= np.repeat(dnp[..., np.newaxis], a, axis=2) if a>1 else dnp

    return dus.astype(dtype)
