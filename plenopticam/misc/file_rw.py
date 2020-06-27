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

import numpy as np
import os

try:
    from PIL import Image
except ImportError:
    raise ImportError('Please install pillow.')

from plenopticam.misc.normalizer import Normalizer
from plenopticam.misc import suppress_user_warning

PORTISHEAD = b"x\x9cm\x8f\xe1\n\xc0 \x08\x84\xdf\xffEu\x8c\x84`kBM\x9d\x95\xc4`\xbb?\xde\xa7R\x9e\x99K\xa55Q\x0b)" + \
             b"\x13\x02 \xf1\xecH\x86P\x96>]\xe8\r\xdf\xe0nRJ[\xaflJ^P\xb8\xdc\xc9\r\xa9\xe0\xe0\x1d\xcek\x98\x06" + \
             b"\xc1|t\xd7\x82E\n\x0e^\xfb0\x07\xf1^0i\xfc\x87\x93\xf9{\xcf\xfb^\xfd\xcb3\xf2\xd6\x1ay\x1f\xc8\x93\xf0u"


def try_tiff_import(type):

    try:
        import imageio
    except:
        imageio, type = None, 'png'

    return imageio, type


def save_img_file(img, file_path=None, file_type=None, gamma=None, tag=None):

    # do gamma correction
    img = img**gamma if gamma is not None else img

    file_path = os.getcwd() if file_path is None else file_path

    try:
        img = place_dnp(img) if not tag else img
    except ValueError:
        pass

    # amend write privileges of (potentially existing) config file
    if os.path.exists(file_path):
        st = os.stat(file_path)
        os.chmod(file_path, st.st_mode | 0o111)

    ext = os.path.splitext(file_path)[-1][1:]
    if not file_type:
        file_type = ext if ext == 'png' or ext == 'tiff' else 'tiff' if img.dtype == 'uint16' else 'png'

    # try imageio import or use png instead if import fails
    imageio, file_type = try_tiff_import(file_type)

    # compose new file path string if extension type changed
    file_path = os.path.splitext(file_path)[-2] if file_path.endswith(('.tiff', '.png', '.bmp')) else file_path
    file_type = 'png' if file_type is None else file_type
    file_path += '.' + file_type

    if file_type.__contains__('tif'):
        suppress_user_warning(True, category=UserWarning)
        imageio.imwrite(uri=file_path, im=Normalizer(img).uint16_norm())
        suppress_user_warning(False, category=UserWarning)

    elif file_type == 'png' or file_type == 'bmp':
        try:
            #Image.fromarray(Normalizer(img).uint8_norm()).save(file_path, file_type, optimize=True)
            imageio.imwrite(uri=file_path, im=Normalizer(img).uint8_norm())
        except PermissionError as e:
            raise Exception(e)

    return True


def load_img_file(file_path):

    file_type = file_path.split('.')[-1]
    img = None

    # try libtiff import or use png instead if import fails
    imageio, file_type = try_tiff_import(file_type)

    if file_type.__contains__('tif'):
        suppress_user_warning(True, category=UserWarning)
        img = imageio.imread(uri=file_path)
        suppress_user_warning(False, category=UserWarning)

    elif any(file_type in ext for ext in ('bmp', 'png', 'jpeg', 'jpg')):
        try:
            img = Image.open(file_path)
            #imageio.imread(uri=file_path, format=file_type)
        except OSError:
            # support load of truncated images
            from PIL import ImageFile
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            img = Image.open(file_path)
        except AttributeError:
            raise TypeError()

    elif not any(file_type in ext for ext in ('bmp', 'png', 'tiff', 'jpeg', 'jpg')):
        raise TypeError('Filetype %s not recognized' % file_type)

    # normalize (convert to numpy array)
    img = Normalizer(np.asarray(img)).type_norm()

    return img


def save_gif(img_set, duration=.1, fp='', fn='default'):

    fn = '%s.gif' % fn

    try:
        import imageio
        imageio.mimwrite(os.path.join(fp, fn), [place_dnp(img) for img in img_set], duration=duration, palettesize=2**8)
    except ImportError:
        # only use pillow for gif animation if necessary as it yields poorer image quality
        pil_arr = [Image.fromarray(place_dnp(img)) for img in img_set]
        pil_arr[0].save(os.path.join(fp, fn), save_all=True, append_images=pil_arr[1:], duration=duration, loop=0)
    except PermissionError:
        pass#raise PlenopticamError(e)

    return True


def place_dnp(dus):

    import zlib

    dtype = dus.dtype
    dus = dus.astype('float64')

    n = 16
    dnp = np.asarray(np.frombuffer(zlib.decompress(PORTISHEAD), 'uint8').reshape(n, n))/(2**8-1.)

    s, t = dus.shape[:2]
    y, x = np.array([s-n, s+(t-s)//2-n])-n//2
    a = dus.shape[2] if len(dus.shape) == 3 else 1
    dus[y:y+n, x:x+n, ...] *= np.repeat(dnp[..., np.newaxis], a, axis=2) if a > 1 else dnp

    return dus.astype(dtype)
