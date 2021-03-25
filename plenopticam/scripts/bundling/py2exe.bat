:: remove build directories
@RD /S /Q build
@RD /S /Q dist

:: find python's site-packages path
set sp_path = python3 -c "import sysconfig; print(sysconfig.get_path('purelib'))"
%sp_path%

:: run pyinstaller with provided options
pyinstaller plenopticam\gui\top_level.py^
	--name=plenopticam^
    --onefile^
    --noconsole^
	--icon=plenopticam\gui\icns\1055104.ico^
	--add-data=c:\hostedtoolcache\windows\python\3.8.8\x64\lib\site-packages\imageio;.\imageio^
	--add-data=docs\build\html\;.\docs\build\html\^
	--add-data=plenopticam\gui\icns\1055104.ico;.\icns\

::    --noconfirm^
