#!/bin/bash
# Crea el entorno virtual del proyecto e instala dependencias.
# Ejecutar una vez: ./setup_venv.sh

set -e
cd "$(dirname "$0")"

VENV_DIR="venv"

if [ -d "$VENV_DIR" ]; then
    echo "⚠️  El directorio '$VENV_DIR' ya existe."
    read -p "¿Recrear desde cero? (s/n): " -r
    if [[ $REPLY =~ ^[sS]$ ]]; then
        rm -rf "$VENV_DIR"
    else
        echo "Usando venv existente. Para instalar/actualizar dependencias:"
        echo "  source $VENV_DIR/bin/activate && pip install -r requirements.txt"
        exit 0
    fi
fi

echo "📦 Creando entorno virtual en $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "🔧 Activando y instalando dependencias..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Listo. Para activar el entorno:"
echo "   source $VENV_DIR/bin/activate"
echo ""
echo "Para ejecutar la app:"
echo "   ./run_streamlit.sh"
echo "   o: source venv/bin/activate && streamlit run orden_compra_app/app/main.py"
echo ""
echo "Para probar el formatter:"
echo "   ./run_test_formatter.sh"
echo "   o: source venv/bin/activate && python test_formatter_oc.py"
echo ""
