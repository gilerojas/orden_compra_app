#!/usr/bin/env python3
"""
Script de prueba para el extractor de órdenes de compra.
Uso: python test_extractor.py path/to/orden_compra.pdf
"""

import sys
from pathlib import Path

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent))

from orden_compra_app.src.extractor_oc import procesar_pdf

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_extractor.py <ruta_pdf>")
        sys.exit(1)
    
    ruta_pdf = sys.argv[1]
    
    if not Path(ruta_pdf).exists():
        print(f"❌ Error: El archivo {ruta_pdf} no existe")
        sys.exit(1)
    
    print(f"📄 Procesando: {ruta_pdf}")
    print("=" * 60)
    
    df = procesar_pdf(ruta_pdf, debug=True)
    
    print("\n" + "=" * 60)
    if df.empty:
        print("❌ No se extrajeron datos")
    else:
        print(f"✅ Extraídos {len(df)} productos")
        print("\n📊 Datos extraídos:")
        print(df.to_string())
        
        # Mostrar resumen
        print("\n" + "=" * 60)
        print("📋 Resumen:")
        if "Numero Orden" in df.columns:
            print(f"  N° Orden: {df['Numero Orden'].iloc[0]}")
        if "Fecha" in df.columns:
            print(f"  Fecha: {df['Fecha'].iloc[0]}")
        if "Proveedor" in df.columns:
            print(f"  Proveedor: {df['Proveedor'].iloc[0]}")
        if "Total" in df.columns:
            print(f"  Total: ${df['Total'].iloc[0]:,.2f}")
