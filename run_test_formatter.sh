#!/bin/bash
# Ejecuta test_formatter_oc.py. Usa el venv de este proyecto si existe.

cd "$(dirname "$0")"
VENV_LOCAL="venv"
VENV_ORDEN_DESPACHO="/Users/gilrojasb/Desktop/SOLQUIM/orden_despacho_app/env_orden"

if [ -d "$VENV_LOCAL" ]; then
    echo "Usando entorno virtual del proyecto ($VENV_LOCAL)..."
    "$VENV_LOCAL/bin/python" test_formatter_oc.py "$@"
elif [ -d "$VENV_ORDEN_DESPACHO" ]; then
    echo "Usando Python de orden_despacho_app..."
    "$VENV_ORDEN_DESPACHO/bin/python" test_formatter_oc.py "$@"
else
    echo "Ejecutando con python del sistema (puede faltar pdfplumber/reportlab)..."
    python3 test_formatter_oc.py "$@"
fi
