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

import numpy as np
import sys, errno
from os import makedirs, remove, chmod, listdir
from os.path import isdir, isfile, expanduser, join

from plenopticam.gui.constants import GENERIC_EXTS
from plenopticam.misc.file_rw import load_img_file
from plenopticam.misc.normalizer import Normalizer


def mkdir_p(path, print_opt=False):

    try:
        makedirs(path, mode=0o777)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and isdir(path):
            if print_opt:
                print('\n Potential data loss as directory already exists.')
        #else:
        #    raise OSError('\n Could not create directory.')

    return True


def rmdir_p(path, print_opt=False):

    try:
        import shutil
        shutil.rmtree(path, onerror=remove_readonly)
    except:
        if print_opt:
            print('\n Directory {0} could not be removed'.format(path))

    return True


def remove_readonly(func, path, _):
    """ clear the readonly bit and reattempt the removal """

    import stat
    chmod(path, stat.S_IWRITE)

    func(path)


def rm_file(path, print_opt=False):

    try:
        if isfile(path):
            remove(path)
    except OSError as e:
        if print_opt:
            print("\n Error: %s - %s." % (e.filename, e.strerror))


def select_file(init_dir=None, title=''):
    """ get file path from tkinter dialog """

    # consider initial directory if provided
    init_dir = expanduser('~/') if not init_dir else init_dir

    # import tkinter while considering Python version
    try:
        if sys.version_info > (3, 0):
            from tkinter import Tk
            from tkinter.filedialog import askopenfilename
        else:
            from Tkinter import Tk
            from tkFileDialog import askopenfilename
    except ImportError:
        raise ImportError('Please install tkinter package.')

    # open window using tkinter
    root = Tk()
    root.withdraw()
    root.update()
    file_path = askopenfilename(initialdir=[init_dir], title=title)
    root.update()

    return file_path if file_path else None


def get_img_list(img_dir, vp=1):
    """ obtain list of images from provided directory path """

    dir_list = listdir(img_dir)
    dir_list.sort()
    img_list = []
    for i in dir_list:
        img_path = join(img_dir, i)
        ext = img_path.split('.')[::-1][0].lower()
        if ext in GENERIC_EXTS:

            # load image
            img = load_img_file(img_path)

            # convert to uint8 if necessary
            img = Normalizer(img).uint8_norm() if str(img.dtype) != 'uint8' else img

            # append to image list
            img_list.append((i, img))

    # sort image list by indices in file names
    img_tuples = sorted(img_list, key=lambda k: idx_str_sort(k[0], 1 if vp else 0))
    _, img_list = zip(*img_tuples)

    if vp:
        vp_dim = int(np.sqrt(len(img_list)))
        img_list = np.reshape(img_list, newshape=(vp_dim, vp_dim) + img_list[0].shape, order='C')

    return img_list


def idx_str_sort(s, mode=0):
    """ criteria for sort in lambda function calls """

    if mode:
        # viewpoint mode
        return [int(s.split('.')[0].split('_')[0]),
                int(s.split('.')[0].split('_')[1])]
    else:
        # refocus mode
        return int(s.split('.')[0])
