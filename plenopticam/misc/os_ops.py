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


import sys, errno
from os import makedirs, remove
from os.path import isdir, isfile, expanduser

def mkdir_p(path, print_opt=False):

    try:
        makedirs(path)
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
        shutil.rmtree(path, ignore_errors=True)
    except:
        if print_opt:
            print('\n Directory {0} could not be removed'.format(path))

    return True

def rm_file(path, print_opt=False):

    try:
        if isfile(path):
            remove(path)
    except OSError as e:
        if print_opt:
            print("\n Error: %s - %s." % (e.filename, e.strerror))

def select_file(init_dir=None, title=''):
    ''' get filepath from tkinter dialog '''

    # consider initial directory if provided
    init_dir = expanduser('~/') if not init_dir else init_dir

    # import tkinter while considering Python version
    try:
        if (sys.version_info > (3, 0)):
            from tkinter import Tk
            from tkinter.filedialog import askopenfilename
        elif (sys.version_info > (2, 0)):
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
