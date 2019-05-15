#!/bin/bash

# remove build and dist folder
sudo rm -rf build dist

# generate MacOSX app
sudo python3 ./setup.py py2app || sudo python ./setup.py py2app

# grant write privileges to config file
sudo chmod -R 666 ./dist/plenopticam.app/Contents/Resources/cfg/cfg.json

# modify redundant file cam16_ucs.py in colour package as it causes an import error
sudo sed -i -e '71,85 s/^/#/' ./dist/plenopticam.app/Contents/Resources/lib/python3.6/colour/models/cam16_ucs.py

# copy docs folder to app bundle
sudo cp -r ./docs ./dist/plenopticam.app/Contents/Resources/