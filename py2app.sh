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

# rename tifflib as version 5 causes an error
#mv ./dist/plenopticam.app/Contents/Frameworks/libtiff.5.dylib ./dist/plenopticam.app/Contents/Frameworks/libtiff.4.dylib

# remove compiled color management file in PIL as it causes an error
#sudo cp ../site-packages/PIL/liblcms2.2.dylib ~/
#sudo rm -rf liblcms2.2.dylib

# move dylibs (prevents error in codesign)
sudo python3 ./plenopticam/scripts/move_dylibs.py ./dist/plenopticam.app ||
sudo python ./plenopticam/scripts/move_dylibs.py ./dist/plenopticam.app

# certificate signature
sudo codesign --deep --signature-size 9400 -f -s "hahnec" ./dist/plenopticam.app

# command -v nvm >/dev/null 2>&1
#sudo brew install npm
#sudo npm install -g create-dmg
#sudo npm install -g create-dmg --unsafe-perm=true --allow-root

# create dmg (requires npm and create-dmg)
sudo xcode-select -switch "/Applications/Xcode.app/Contents/Developer/"
sudo create-dmg ./dist/plenopticam.app ./dist