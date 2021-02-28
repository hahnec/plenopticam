:: remove build directories
@RD /S /Q build
@RD /S /Q dist

:: run pyinstaller with provided options
pyinstaller plenopticam\gui\top_level.py^
	--name=plenopticam^
    --onefile^
    --noconsole^
	--icon=plenopticam\gui\icns\1055104.ico^
	--add-data=c:\hostedtoolcache\windows\python\3.8.7\x64\lib\site-packages\imageio;.\imageio^
	--add-data=docs\build\html\;.\docs\build\html\^
	--add-data=plenopticam\gui\icns\1055104.ico;.\icns\

::    --noconfirm^
