:: remove build directories
@RD /S /Q build
@RD /S /Q dist

:: run pyinstaller with provided options
pyinstaller plenopticam\gui\top_level.py^
    --onefile^
	--noconsole^
	--add-data C:\Python\Python36\lib\site-packages\libtiff;.\libtiff^
	--name=plenopticam^
	--icon=plenopticam\gui\icns\1055104.ico^
	--add-data=.\docs\build\html\;.\docs\build\html\^
	--add-data=plenopticam\gui\icns\1055104.ico;.\icns\