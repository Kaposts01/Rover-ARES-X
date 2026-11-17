@echo off
rem ARES-X: crea el entorno (.venv-ares) si no existe, instala requirements.txt y arranca la API.
rem Uso: arrancar.bat            -> servidor en http://127.0.0.1:8765/
rem      arrancar.bat pruebas    -> pruebas de la API (no arranca el servidor)
rem Puerto: set ARES_PUERTO=8790 antes de ejecutar, si hace falta.
setlocal
cd /d "%~dp0"
rem Requisito: Python 3.14 o superior. ARES_PYTHON permite elegir el intérprete a probar.
if "%ARES_PYTHON%"=="" (set BASE=python) else (set BASE=%ARES_PYTHON%)
for /f "tokens=1,2" %%a in ('%BASE% -c "import sys; print(sys.version_info[0], sys.version_info[1])" 2^>nul') do (set MAYOR=%%a& set MENOR=%%b)
if not defined MAYOR (set MAYOR=0& set MENOR=0)
if %MAYOR% LSS 3 goto :version
if %MAYOR% EQU 3 if %MENOR% LSS 14 goto :version
if not exist ".venv-ares\Scripts\python.exe" (
    python -m venv .venv-ares || goto :error
)
if "%1"=="pruebas" (
    ".venv-ares\Scripts\python.exe" -m pip install -q -r requirements-dev.txt || goto :error
    ".venv-ares\Scripts\python.exe" -m pytest -q api/tests || goto :error
    goto :eof
)
".venv-ares\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :error
if "%ARES_PUERTO%"=="" set ARES_PUERTO=8765
echo Servidor en http://127.0.0.1:%ARES_PUERTO%/  (Ctrl+C para parar)
".venv-ares\Scripts\python.exe" -m uvicorn api.servidor:app --host 127.0.0.1 --port %ARES_PUERTO%
goto :eof
:version
echo ARES-X requiere Python 3.14 o superior; versión detectada %MAYOR%.%MENOR%; instálalo desde python.org
exit /b 2
:error
echo Fallo al preparar o arrancar ARES-X.
exit /b 1
