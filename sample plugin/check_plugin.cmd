@echo off
setlocal

if "%~1"=="" (
    set "PLUGIN=%~dp0build\GmaxTestExporter.dle"
) else (
    set "PLUGIN=%~1"
)

where dumpbin.exe >nul 2>nul
if errorlevel 1 (
    echo dumpbin.exe was not found.
    echo Run this from a Visual Studio Native Tools Command Prompt.
    exit /b 1
)

if not exist "%PLUGIN%" (
    echo Plugin not found: %PLUGIN%
    exit /b 1
)

echo === Machine ===
dumpbin.exe /headers "%PLUGIN%" | findstr /I "machine"

echo.
echo === Required exports ===
dumpbin.exe /exports "%PLUGIN%" | findstr /I ^
 "LibDescription LibNumberClasses LibClassDesc LibVersion"

exit /b 0
