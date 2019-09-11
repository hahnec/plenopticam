#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "inbox@christopherhahne.de"
__license__ = """
    Copyright (c) 2019 Christopher Hahne <inbox@christopherhahne.de>

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

from setuptools import setup, find_packages
from plenopticam import __version__
from sys import platform


APP = ['plenopticam/gui/top_level.py']

MAC_FILES = [
        # ('subdir' , ['file_path'])
        ('cfg', ['plenopticam/cfg/cfg.json']),
        ('gui/icns', ['plenopticam/gui/icns/1055104.ico'])
]

WIN_FILES = [
        # ('subdir' , ['file_path'])
        ('gui/icns', ['plenopticam/gui/icns/1055104.ico'])
]
UNIX_FILES = [
        # ('subdir' , ['file_path'])
        ('gui/icns', ['plenopticam/gui/icns/1055104.gif'])
]

OPTIONS = {
    "argv_emulation": True,
    "compressed": True,
    "optimize": 2,
    "iconfile": 'plenopticam/gui/icns/1055104.icns',
    "excludes": ['matplotlib'],
    "plist": dict(NSHumanReadableCopyright='2019 Christopher Hahne'),
    "packages": ['numpy', 'scipy', 'libtiff', 'colour_demosaicing', 'colour', 'pillow'],
}

if platform == 'darwin':
 extra_options = dict(
     setup_requires=['py2app'],
     app=APP,
     data_files=MAC_FILES,
     options=dict(py2app=OPTIONS),
 )
elif platform == 'win32':
 extra_options = dict(
     setup_requires=[],
     app=APP,
     data_files=WIN_FILES,
 )
else:
 extra_options = dict(
     setup_requires=[],
     data_files=UNIX_FILES,
 )

setup(
      name='plenopticam',
      version=__version__,
      description='Software for scientific light field computation',
      url='http://github.com/hahnec/plenopticam',
      author='Christopher Hahne',
      author_email='inbox@christopherhahne.de',
      license='GNU GPL V3.0',
      scripts=['plenopticam/bin/cli_script.py'],
      entry_points={'console_scripts': ['plenopticam=plenopticam.bin.cli_script:main'], },
      packages=find_packages(),
      install_requires=['numpy', 'scipy', 'colour_demosaicing', 'colour', 'pillow', 'libtiff', 'imageio'],
      include_package_data=True,
      zip_safe=False,
      **extra_options
      )
