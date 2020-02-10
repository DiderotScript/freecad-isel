@ECHO off
REM Launch python.exe from the FreeCAD folder
SETLOCAL
REM search registry entries
FOR /F %%G IN ('REG QUERY HKLM\Software ^|findstr "FreeCAD"') DO SET "FCPATH=%%G"
REM search default value
FOR /F "tokens=2 delims=REG_SZ" %%G IN ('REG QUERY "%FCPATH%" /ve ^|findstr "REG_SZ"') DO SET "FCPATH=%%G"
REM trim leading spaces
FOR /F "tokens=*" %%G IN ("%FCPATH%") DO SET "FCPATH=%%G"

SET "PATH=%FCPATH%\bin;%PATH%"
SET "PYTHONPATH=%FCPATH%\Mod\Path"
SET "PYTHONPATH=%PYTHONPATH%;%FCPATH%\Ext"
SET "PYTHONPATH=%PYTHONPATH%;%APPDATA%\FreeCAD\Macro"

SET "_usermacro=%APPDATA%\FreeCAD\Macro\%~n1.py"
IF EXIST "%_usermacro%" (
	SHIFT
	"%FCPATH%\bin\python.exe" "%_usermacro%" %1 %2 %3 %4 %5 %6 %7 %8 %9
) ELSE (
	"%FCPATH%\bin\python.exe" %1 %2 %3 %4 %5 %6 %7 %8 %9
)
