@echo off

set PYTHON=python

if exist "%~dp0.\bin\_props.bat" call "%~dp0.\bin\_props.bat"
if exist "%~dp0.\_props.bat" call "%~dp0.\_props.bat"


setlocal EnableDelayedExpansion
set PARAMS=
for %%P in (%*) do (
  if exist "%%~P" (
    set PARAMS=!PARAMS! "%%~fP"
  ) else (
    set PARAMS=!PARAMS! "%%~P"
  )
)
setlocal DisableDelayedExpansion


"%PYTHON%" main.py %PARAMS%
