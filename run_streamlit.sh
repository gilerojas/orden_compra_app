#!/bin/bash
# Ejecuta Streamlit. Usa el venv de este proyecto si existe; si no, el de orden_despacho_app.

cd "$(dirname "$0")"
VENV_LOCAL="venv"
VENV_ORDEN_DESPACHO="/Users/gilrojasb/Desktop/SOLQUIM/orden_despacho_app/env_orden"

if [ -d "$VENV_LOCAL" ]; then
    echo "🔧 Usando entorno virtual del proyecto ($VENV_LOCAL)..."
    exec "$VENV_LOCAL/bin/streamlit" run orden_compra_app/app/main.py "$@"
elif [ -d "$VENV_ORDEN_DESPACHO" ]; then
    echo "🔧 Usando entorno de orden_despacho_app..."
    exec "$VENV_ORDEN_DESPACHO/bin/streamlit" run orden_compra_app/app/main.py "$@"
else
    echo "❌ No se encontró ningún entorno virtual."
    echo "Crea uno con: ./setup_venv.sh"
    echo "O instala dependencias: pip install -r requirements.txt"
    exit 1
fi
