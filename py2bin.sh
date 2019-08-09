#!/bin/bash

# install additional tkinter package in ubuntu
sudo apt install python3-tk
sudo pip3 install numpy==1.16.2 # solves issue in bundling with pyinstaller

# rmeove build directories
sudo rm -rf build/
sudo rm -rf dist/

# run pyinstaller with provided options
pyinstaller3.cp plenopticam/gui/top_level.py \
    	--onefile \
	--noconsole \
	--add-data=/home/chris/.local/lib/python3.6/site-packages/libtiff/:./libtiff \
	--name=plenopticam \
	--icon=plenopticam/gui/icns/1055104.ico \
	--add-data=./docs/build/html/:./docs/build/html/ \
	--add-data=plenopticam/gui/icns/1055104.ico:./icns/
