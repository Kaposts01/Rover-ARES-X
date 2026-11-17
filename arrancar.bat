@echo off
rem ARES-X: crea el entorno (.venv-ares) si no existe, instala requirements.txt y arranca la API.
rem Uso: arrancar.bat            -> servidor en http://127.0.0.1:8765/
rem      arrancar.bat pruebas    -> pruebas de la API (no arranca el servidor)
rem Puerto: set ARES_PUERTO=8790 antes de ejecutar, si hace falta.
setlocal
cd /d "%~dp0"
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
:error
echo Fallo al preparar o arrancar ARES-X.
exit /b 1
