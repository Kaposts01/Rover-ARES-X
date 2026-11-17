#!/usr/bin/env bash
# ARES-X: crea el entorno (.venv-ares) si no existe, instala requirements.txt y arranca la API.
# Uso: ./arrancar.sh            -> servidor en http://127.0.0.1:8765/
#      ./arrancar.sh pruebas    -> pruebas de la API (no arranca el servidor)
# Puerto: ARES_PUERTO=8790 ./arrancar.sh
set -euo pipefail
cd "$(dirname "$0")"

# Requisito: Python 3.14 o superior (ver requirements.txt). ARES_PYTHON permite elegir el intérprete a probar.
BASE="${ARES_PYTHON:-python}"
command -v "$BASE" >/dev/null 2>&1 || BASE=python3
VERSION=$("$BASE" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null || echo "0.0")
MAYOR="${VERSION%%.*}"; MENOR="${VERSION#*.}"
if [ "$MAYOR" -lt 3 ] || { [ "$MAYOR" -eq 3 ] && [ "$MENOR" -lt 14 ]; }; then
    echo "ARES-X requiere Python 3.14 o superior; versión detectada ${VERSION}; instálalo desde python.org" >&2
    exit 2
fi

if [ -x ".venv-ares/bin/python" ]; then PY=".venv-ares/bin/python"
elif [ -x ".venv-ares/Scripts/python.exe" ]; then PY=".venv-ares/Scripts/python.exe"
else python3 -m venv .venv-ares 2>/dev/null || python -m venv .venv-ares
     PY=$( [ -x .venv-ares/bin/python ] && echo .venv-ares/bin/python || echo .venv-ares/Scripts/python.exe )
fi
if [ "${1:-}" = "pruebas" ]; then
    "$PY" -m pip install -q -r requirements-dev.txt
    "$PY" -m pytest -q api/tests
    exit 0
fi
"$PY" -m pip install -q -r requirements.txt
PUERTO="${ARES_PUERTO:-8765}"
echo "Servidor en http://127.0.0.1:${PUERTO}/  (Ctrl+C para parar)"
exec "$PY" -m uvicorn api.servidor:app --host 127.0.0.1 --port "$PUERTO"
