#!/usr/bin/env python

from setuptools import setup, find_packages
from plenopticam import __version__
from sys import platform    # cross-platform


APP = ['plenopticam/gui/top_level.py']
DATA_FILES = [
        # ('subdir' , ['file_path'])
        ('cfg', ['plenopticam/cfg/cfg.json'])
]

OPTIONS = {
    "argv_emulation": True,
    "compressed": True,
    "optimize": 2,
    "iconfile":'plenopticam/gui/icns/1055104.icns',
    "excludes": ['matplotlib'],
    "plist": dict(NSHumanReadableCopyright='2019 Christopher Hahne'),
    "packages": ['libtiff', 'colour_demosaicing', 'colour'],
}

if platform == 'darwin':
 extra_options = dict(
     setup_requires=['py2app'],
     app=APP,
     data_files=DATA_FILES,
     # Cross-platform applications generally expect sys.argv to be used for opening files.
     options=dict(py2app=OPTIONS),
 )
elif platform == 'win32':
 extra_options = dict(
     setup_requires=[],
     app=APP,
     data_files=DATA_FILES,
 )
else:
 extra_options = dict(
     # Normally unix-like platforms will use "setup.py install"
     # and install the main script as such
     setup_requires=[],
     scripts=APP,
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
      entry_points={'console_scripts': ['plenopticam=plenopticam.bin.cli_script:main'],},
      packages=find_packages(),
      install_requires=['numpy', 'scipy', 'libtiff', 'colour_demosaicing', 'colour'],
      include_package_data=True,
      zip_safe=False,
      **extra_options
      )