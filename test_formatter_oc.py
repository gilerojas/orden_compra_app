#!/usr/bin/env python3
"""
Script de prueba para el formatter de Orden de Compra.

1. Extrae datos del PDF de muestra (ORDEN_DE_COMPRA_ENVASES.pdf)
2. Genera un PDF formateado con el logo
3. Guarda el resultado en data/processed/

Uso:
    python test_formatter_oc.py
    ./run_test_formatter.sh
"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Si faltan dependencias, intentar re-ejecutar con el venv del proyecto
def _check_and_reexec():
    try:
        import pdfplumber
        import pandas
        import reportlab
        return True
    except ImportError:
        pass
    # Buscar venv en este proyecto o en orden_despacho_app
    for venv_name in ["venv", "env"]:
        venv_py = ROOT / venv_name / "bin" / "python"
        if venv_py.exists():
            os.execv(str(venv_py), [str(venv_py), str(ROOT / "test_formatter_oc.py")] + sys.argv[1:])
    otro = ROOT.parent / "orden_despacho_app" / "env_orden" / "bin" / "python"
    if otro.exists():
        os.execv(str(otro), [str(otro), str(ROOT / "test_formatter_oc.py")] + sys.argv[1:])
    return False

if not _check_and_reexec():
    print("❌ Faltan dependencias (pdfplumber, pandas, reportlab).")
    print()
    print("Con el venv activado (venv), ejecuta:")
    print("   pip install -r requirements.txt")
    print("   python test_formatter_oc.py")
    print()
    print("O ejecuta el script que usa el venv:")
    print("   ./run_test_formatter.sh")
    sys.exit(1)

sys.path.insert(0, str(ROOT))

# PDF de prueba y logo
PDF_MUESTRA = ROOT / "ORDEN_DE_COMPRA_ENVASES.pdf"
LOGO = ROOT / "Logo_Solquim_Limpio.png"
OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_PDF = OUTPUT_DIR / "Orden_Compra_formateada.pdf"


def main():
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        pdf_path = PDF_MUESTRA

    if not pdf_path.exists():
        print(f"❌ No se encontró el PDF: {pdf_path}")
        sys.exit(1)

    if not LOGO.exists():
        print(f"⚠️ No se encontró el logo: {LOGO}")
        logo_path = None
    else:
        logo_path = str(LOGO)
        print(f"✅ Logo: {LOGO}")

    print(f"📄 PDF de entrada: {pdf_path}")
    print("=" * 60)

    # Importar después de agregar path
    from orden_compra_app.src.extractor_oc import procesar_pdf
    from orden_compra_app.src.formatter_oc import exportar_orden_compra_a_pdf, generar_orden_compra

    # 1. Extraer datos del PDF
    print("🔍 Extrayendo datos del PDF...")
    df = procesar_pdf(str(pdf_path), debug=False)

    if df.empty:
        print("❌ No se pudieron extraer datos del PDF.")
        sys.exit(1)

    print(f"✅ Extraídos {len(df)} productos")
    print(f"   N° Orden: {df['Numero Orden'].iloc[0]}")
    print(f"   Proveedor: {df['Proveedor'].iloc[0][:50]}...")
    print(f"   Total: {df['Total'].iloc[0]:,.2f}")
    print()

    # 2. Preview título y tabla
    titulo, tabla = generar_orden_compra(df)
    print("📋 Preview:")
    print(f"   Título: {titulo}")
    print(f"   Columnas tabla: {list(tabla.columns)}")
    print()

    # 3. Generar PDF formateado
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = str(OUTPUT_PDF)

    print("📝 Generando PDF formateado...")
    pdf_bytes = exportar_orden_compra_a_pdf(
        df,
        output_path=output_path,
        logo_path=logo_path,
    )

    print(f"✅ PDF generado: {output_path}")
    print(f"   Tamaño: {len(pdf_bytes):,} bytes")
    print()
    print("=" * 60)
    print("Abre el archivo para revisar el resultado:")
    print(f"   {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
