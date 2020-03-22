#!/usr/bin/env bash

# remove build directories
sudo rm -rf build dist

#line_num=187
#line_text="if 'Library/Frameworks' in path_to_tcl and 'Python' not in path_to_tcl:"
#file_name="/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages/PyInstaller/hooks/hook-_tkinter.py"
#sed -i ${line_num}s/.*/$line_text/ $file_name

#sed -i "187s/.*/if 'Library/Frameworks' in path_to_tcl and 'Python' not in path_to_tcl:/" echo "$file_name"

#sed -i '' 's/toreplace/replacewith/g'

#line_text="if 'Library/Frameworks' in path_to_tcl and 'Python' not in path_to_tcl:"
#sed -i '' -e "s/if 'Library/Frameworks' in path_to_tcl.*/" echo "$line_text" "=187/" echo "$file_name"
#sed -i '' -e 's/text-on-line-to-be-changed.*/text-to-replace-the=whole-line/' file-name

# run pyinstaller with provided options
pyinstaller plenopticam/gui/top_level.py \
    	--onefile \
	--noconsole \
	--name=plenopticam \
	--icon=plenopticam/gui/icns/1055104.icns \
	--add-data=/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages/imageio/:./imageio \
	--add-data=./docs/build/html/:./docs/build/html/ \
    --exclude-module=matplotlib \
    --osx-bundle-identifier='org.pythonmac.unspecified.plenopticam' \
    --add-binary='/Library/Frameworks/Python.framework/Versions/3.6/lib/libtk8.6.dylib':'tk' \
    --add-binary='/Library/Frameworks/Python.framework/Versions/3.6/lib/libtcl8.6.dylib':'tcl' \
    --add-data=plenopticam/cfg/cfg.json:cfg
#    --add-data='./plenopticam/cfg/cfg.json':'Resources/cfg' \
#    --add-binary='/System/Library/Frameworks/Tk.framework/Tk':'tk' \
#    --add-binary='/System/Library/Frameworks/Tcl.framework/Tcl':'tcl' \

# extract version number from python file
version=$(sed -ne 's@__version__ = \([^]]*\)@\1@gp' plenopticam/__init__.py)

# add config to spec file
sudo sed -i -e '$ d' ./plenopticam.spec
echo "             bundle_identifier=None," >> ./plenopticam.spec
echo "             info_plist={" >> ./plenopticam.spec
echo "              'NSHighResolutionCapable': 'True'," >> ./plenopticam.spec
echo "              'PyRuntimeLocations': $version," >> ./plenopticam.spec
echo "              'CFBundleShortVersionString': $version," >> ./plenopticam.spec
echo "              'CFBundleVersion': $version" >> ./plenopticam.spec
echo "             }," >> ./plenopticam.spec
echo "            )" >> ./plenopticam.spec

# re-run pyinstaller with extended spec file
sudo pyinstaller plenopticam.spec

# add plist file to app bundle (as an alternative to modifying the spec file)
#cp -f ./plenopticam/scripts/bundling/Info.plist dist/plenopticam.app/Contents/Info.plist

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
sudo xcode-select -switch "/Applications/Xcode.app/Contents/Developer/"
sudo create-dmg ./dist/plenopticam.app ./dist

# replace space by underscore
for file in ./dist/*.dmg
do
  mv -- "$file" "${file// /_}"
done
