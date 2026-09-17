@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 goto error

py -3.11 "%~dp0mouthclick_mvp_opticalflow.py"
if errorlevel 1 goto error
exit /b 0

:error
echo.
echo No se pudo ejecutar MouthClick correctamente.
echo Revisa el mensaje de error que aparece arriba.
echo.
pause
exit /b 1
