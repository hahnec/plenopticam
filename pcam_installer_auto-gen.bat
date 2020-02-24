:: determine version number from __init__.py file
@ECHO OFF
SETLOCAL ENABLEDELAYEDEXPANSION
for /f "tokens=*" %%a in (./plenopticam/__init__.py) do (
    SET b=%%a
    SET prefix=!b:~0,11!
    IF !prefix!==__version__ (
        SET version=!b:~15,5!
        ECHO !version!
    )
)

:: path where advanced installer resides
set advinst="C:\Program Files (x86)\Caphyon\Advanced Installer 16.6.1\bin\x86\advinst.exe"
set prjpath=".\pcam_installer_auto-gen.aip"
:: create new project file (overwrite option only needed once)
%advinst% /newproject %prjpath% -lang "en" -overwrite
:: pass version number to advanced installer
%advinst% /edit %prjpath% /SetVersion %version%

%advinst% /edit %prjpath% /SetProperty ProductName="PlenoptiCam"
%advinst% /edit %prjpath% /SetProperty Manufacturer="plenoptic.info"
%advinst% /edit %prjpath% /SetAppdir -buildname DefaultBuild -path [ProgramFilesFolder][Manufacturer]\[ProductName]
:: %advinst% /edit %prjpath% /SetProperty ="https://github.com/hahnec/plenopticam/releases"

:: set installer output path
%advinst% /edit %prjpath% /SetOutputLocation -buildname DefaultBuild -path .\dist -overwrite

%advinst% /edit %prjpath% /AddFile APPDIR ".\dist\plenopticam.exe" -overwrite

%advinst% /edit %prjpath% /SetIcon -icon ".\plenopticam\gui\icns\1055104.ico"

SET productname = PlenoptiCam
SET ext = ".msi"
SET packagename = .\DIST\TEST.MSI
%advinst% /edit %prjpath% /SetPackageName %packagename%
@ECHO ON
ECHO %packagename%
::%advinst% /edit %prjpath% /SetPackageName ".\dist\blabla.msi"
@ECHO OFF
:: save project
%advinst% /save %prjpath%

:: run build
%advinst% /build %prjpath%