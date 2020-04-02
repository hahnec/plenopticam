:: determine version number from __init__.py file
@ECHO OFF
SETLOCAL ENABLEDELAYEDEXPANSION
for /f "tokens=*" %%a in (plenopticam/__init__.py) do (
    SET b=%%a
    SET prefix=!b:~0,11!
    IF !prefix!==__version__ (
        SET version=!b:~15,5!
        ECHO Packaging v!version!
    )
)

:: path where advanced installer resides
set advinst="C:\Program Files (x86)\Caphyon\Advanced Installer 16.9\bin\x86\advinst.exe"
set prjpath=".\plenopticam\scripts\bundling\msi_auto-gen.aip"
:: create new project file (overwrite option only needed once)
%advinst% /newproject %prjpath% -lang "en" -overwrite
:: pass version number to advanced installer
%advinst% /edit %prjpath% /SetVersion %version%

:: edit project properties
%advinst% /edit %prjpath% /SetProperty ProductName="PlenoptiCam"
%advinst% /edit %prjpath% /SetProperty Manufacturer="plenoptic.info"
%advinst% /edit %prjpath% /SetProperty ARPURLINFOABOUT="https://github.com/hahnec/plenopticam/issues"
%advinst% /edit %prjpath% /SetProperty ARPURLUPDATEINFO="https://github.com/hahnec/plenopticam/releases"
%advinst% /edit %prjpath% /SetProperty ARPCONTACT="inbox[ät]christopherhahne.de"
%advinst% /edit %prjpath% /SetProperty ARPHELPLINK="https://hahnec.github.io/plenopticam/build/html/index.html"

:: place shortcut on desktop
::%advinst% /edit %prjpath% /NewShortcut -name PlenoptiCam -dir DesktopFolder -target APPDIR\plenopticam.exe -icon "plenopticam\gui\icns\1055104.ico"

:: set installer output path
python -c "import os,sys; print(os.getcwd())" > tmp.txt
set /P target=<tmp.txt
echo !target!
%advinst% /edit %prjpath% /SetOutputLocation -buildname DefaultBuild -path %target%\dist
%advinst% /edit %prjpath% /AddFile APPDIR "dist\plenopticam.exe"
%advinst% /edit %prjpath% /SetIcon -icon "..\..\gui\icns\1055104.ico"
%advinst% /edit %prjpath% /SetPackageName plenopticam_%version%.msi

:: run build
%advinst% /build %prjpath%