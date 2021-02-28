#!/bin/bash

# install additional tkinter package in ubuntu
#sudo apt-get install python3-tk
#sudo pip3 install numpy==1.16.2 # solves issue in bundling with pyinstaller

# rmeove build directories
sudo rm -rf build/
sudo rm -rf dist/

# run pyinstaller with provided options
pyinstaller plenopticam/gui/top_level.py \
  --onefile \
	--noconsole \
	--noconfirm \
	--add-data=/opt/hostedtoolcache/Python/3.8.7/x64/lib/python3.8/site-packages/imageio/:./imageio \
	--name=plenopticam \
	--icon=plenopticam/gui/icns/1055104.gif \
	--add-data=docs/build/html/:./docs/build/html/ \
	--add-data=plenopticam/gui/icns/1055104.gif:./icns/ \
	--hidden-import='PIL._tkinter_finder'

# change distribution folder ownership to user
#sudo chown -R chris: ./dist

# set absolute path to icon file
#gio set -t string ./dist/plenopticam 'metadata::custom-icon' 'file:./plenopticam/gui/icns/1055104.gif'

# extract version number from python file (first get substring in quotation marks, then remove the quotation marks)
version=$(sed -ne 's@__version__ = \([^]]*\)@\1@gp' plenopticam/__init__.py | sed 's/'\''//g')
echo "detected version number $version"

# compress to archive (c-create archive; z-compress archive with gzip; v-display progress in the terminal; f-filename)
tar -czvf ./dist/plenopticam_${version}.tar.gz dist/plenopticam