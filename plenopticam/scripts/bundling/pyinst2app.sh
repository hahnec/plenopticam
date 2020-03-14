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
	--add-data=plenopticam/gui/icns/1055104.gif:./icns/ \
    --add-binary='/System/Library/Frameworks/Tk.framework/Tk':'tk' \
    --add-binary='/System/Library/Frameworks/Tcl.framework/Tcl':'tcl'

# create dmg (requires npm and create-dmg)
sudo xcode-select -switch "/Applications/Xcode.app/Contents/Developer/"
sudo create-dmg ./dist/plenopticam.app ./dist

# replace space by underscore
for file in ./dist/*.dmg
do
  mv -- "$file" "${file// /_}"
done
