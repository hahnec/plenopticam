#!/usr/bin/env bash

# remove build directories
sudo rm -rf build dist

# find python's site-packages path
sp_path=$(python3 -c "import sysconfig; print(sysconfig.get_path('purelib'))")
echo "$sp_path"/imageio/
echo $(locate libtk*.dylib)

# run pyinstaller with provided options
pyinstaller plenopticam/gui/top_level.py \
  --onefile \
	--noconsole \
	--noconfirm \
	--name=plenopticam \
	--icon=plenopticam/gui/icns/1055104.icns \
	--paths="$sp_path" \
  --add-data="$sp_path"/imageio/:./imageio \
  --add-data=./docs/build/html/:./docs/build/html/ \
  --exclude-module=matplotlib \
  --osx-bundle-identifier='org.pythonmac.unspecified.plenopticam' \
  --hidden-import pkg_resources.py2_warn \
  --add-data=plenopticam/cfg/cfg.json:cfg
#  --add-binary='/usr/local/opt/tcl-tk/lib/libtk8.6.dylib':'tk' \
#  --add-binary='/usr/local/opt/tcl-tk/lib/libtcl8.6.dylib':'tcl' \

# extract version number from python file
version=$(sed -ne 's@__version__ = \([^]]*\)@\1@gp' plenopticam/__init__.py)

# add config to spec file
#sudo sed -i -e '$ d' ./plenopticam.spec
#echo "             bundle_identifier=None," >> ./plenopticam.spec
#echo "             info_plist={" >> ./plenopticam.spec
#echo "              'NSHighResolutionCapable': 'True'," >> ./plenopticam.spec
#echo "              'PyRuntimeLocations': $version," >> ./plenopticam.spec
#echo "              'CFBundleShortVersionString': $version," >> ./plenopticam.spec
#echo "              'CFBundleVersion': $version" >> ./plenopticam.spec
#echo "             }," >> ./plenopticam.spec
#echo "            )" >> ./plenopticam.spec

# re-run pyinstaller with extended spec file
sudo pyinstaller plenopticam.spec --noconfirm

#pyinstaller ./plenopticam.spec
sudo mkdir ./dist/plenopticam.app/Contents/Resources/cfg
sudo cp ./plenopticam/cfg/cfg.json ./dist/plenopticam.app/Contents/Resources/cfg/cfg.json

# grant write privileges to config file
sudo chmod -R 666 ./dist/plenopticam.app/Contents/Resources/cfg/cfg.json

sudo cp -r ./docs ./dist/plenopticam.app/Contents/Resources/
sudo mkdir -p ./dist/plenopticam.app/Contents/Resources/gui/
sudo cp -r ./plenopticam/gui/icns ./dist/plenopticam.app/Contents/Resources/gui/

# certificate signature
sudo codesign --deep --signature-size 9400 -f -s "hahnec" ./dist/plenopticam.app

# create dmg (requires npm and create-dmg)
#sudo xcode-select -switch "/Applications/Xcode.app/Contents/Developer/"
sudo create-dmg ./dist/plenopticam.app ./dist
sudo rm -rf ./dist/plenopticam.app
sudo rm -rf ./dist/plenopticam

# replace space by underscore
for file in ./dist/*.dmg
do
  mv -- "$file" "${file// /_}"
done
