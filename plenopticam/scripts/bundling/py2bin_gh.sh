#!/bin/bash

# rmeove build directories
sudo rm -rf build/
sudo rm -rf dist/

# find python's site-packages path
sp_path=$(python3 -c "import sysconfig; print(sysconfig.get_path('purelib'))")
echo "$sp_path"/imageio/

# run pyinstaller with provided options
pyinstaller plenopticam/gui/top_level.py \
  --onefile \
	--noconsole \
	--noconfirm \
  --add-data="$sp_path"/imageio/:./imageio \
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
sudo apt-get install tar
tar -czvf ./dist/plenopticam_${version}.tar.gz dist/plenopticam
rm -rf ./dist/plenopticam