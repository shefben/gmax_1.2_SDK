@echo off
setlocal EnableExtensions

if "%~1"=="" (
    set "SDKROOT=%~dp0..\output\gmax12-sdk"
) else (
    set "SDKROOT=%~1"
)

for %%I in ("%SDKROOT%") do set "SDKROOT=%%~fI"
set "OUTDIR=%~dp0build"

where cl.exe >nul 2>nul
if errorlevel 1 (
    echo cl.exe was not found.
    echo Run this from an x86 Visual Studio Native Tools Command Prompt.
    exit /b 1
)

if not exist "%SDKROOT%\Include\max.h" (
    echo Missing SDK header: %SDKROOT%\Include\max.h
    exit /b 1
)

if not exist "%SDKROOT%\Lib\core.lib" (
    echo Missing SDK library: %SDKROOT%\Lib\core.lib
    exit /b 1
)

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

pushd "%~dp0"
cl.exe /nologo /LD /EHsc /GR /O2 /MT /W3 ^
 /DWIN32 /D_WINDOWS /D_USRDLL /DGAME_VER ^
 /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_WARNINGS ^
 /I"%SDKROOT%\Include" ^
 GmaxTestExporter.cpp ^
 /link /MACHINE:X86 /SUBSYSTEM:WINDOWS ^
 /DEF:GmaxTestExporter.def ^
 /LIBPATH:"%SDKROOT%\Lib" ^
 core.lib maxutil.lib comctl32.lib ^
 /OUT:"%OUTDIR%\GmaxTestExporter.dle"

set "RESULT=%ERRORLEVEL%"
popd

if not "%RESULT%"=="0" (
    echo Build failed.
    exit /b %RESULT%
)

echo.
echo Built:
echo %OUTDIR%\GmaxTestExporter.dle
exit /b 0
