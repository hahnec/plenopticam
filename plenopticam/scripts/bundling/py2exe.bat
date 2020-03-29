:: remove build directories
@RD /S /Q build
@RD /S /Q dist

:: run pyinstaller with provided options
pyinstaller ..\..\gui\top_level.py^
    	--onefile^
	--noconsole^
	--name=plenopticam^
	--icon=..\..\gui\icns\1055104.ico^
	--add-data C:\Python\Python38\lib\site-packages\imageio;.\imageio^
	--add-data=..\..\..\docs\build\html\;.\docs\build\html\^
	--add-data=..\..\gui\icns\1055104.ico;.\icns\