#!/usr/bin/env python3
"""
Script simplificado para configurar el Google Sheet existente.
Usa el ID del sheet directamente.
"""

import sys
from pathlib import Path

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent))

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ Error: Faltan dependencias")
    print("Instala con: pip install gspread google-auth")
    sys.exit(1)

# Configuración
SHEET_ID = "1kjy-doYxPfdKMFIFpVB5_WD98-CkhXIdLA9XckvQTYw"
WORKSHEET_NAME = "OrdenesCompra"
EMAIL_COMPARTIR = "gilerojas@gmail.com"

# Headers
HEADERS = [
    "Numero Orden", "Fecha", "Proveedor", "Direccion Proveedor", "RNC", "Terminos",
    "Moneda", "Codigo Suplidor", "Codigo Producto", "Descripcion", "Cantidad", "Unidad",
    "Precio", "Descuento %", "Impuesto %", "Importe", "Monto Descuento", "Monto Impuesto",
    "Total por Producto", "Subtotal", "Total", "Fecha_Ultima_Mod", "Estado"
]

def main():
    # Obtener credenciales
    creds_path = Path(__file__).parent / "idyllic-striker-454314-r7-c28d9f15d391.json"
    
    if not creds_path.exists():
        print(f"❌ No se encontró el archivo de credenciales: {creds_path}")
        sys.exit(1)
    
    print(f"🔐 Usando credenciales: {creds_path}")
    creds = Credentials.from_service_account_file(
        str(creds_path),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    
    print("📊 Conectando con Google Sheets...")
    gc = gspread.authorize(creds)
    
    print(f"📝 Abriendo sheet con ID: {SHEET_ID}")
    try:
        sh = gc.open_by_key(SHEET_ID)
        print(f"✅ Sheet encontrado: {sh.title}")
    except Exception as e:
        print(f"❌ Error abriendo sheet: {e}")
        print("\nVerifica que:")
        print("1. El ID del sheet sea correcto")
        print("2. La cuenta de servicio tenga acceso al sheet")
        print(f"   (Comparte el sheet con: ordenescompras@idyllic-striker-454314-r7.iam.gserviceaccount.com)")
        sys.exit(1)
    
    # Crear o actualizar la hoja
    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
        print(f"⚠️  La hoja '{WORKSHEET_NAME}' ya existe")
        print("📝 Configurando headers...")
        worksheet.clear()
        worksheet.update('A1', [HEADERS], value_input_option="USER_ENTERED")
        print(f"✅ Headers configurados")
    except gspread.WorksheetNotFound:
        print(f"📋 Creando hoja '{WORKSHEET_NAME}'...")
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(HEADERS))
        worksheet.update('A1', [HEADERS], value_input_option="USER_ENTERED")
        print(f"✅ Hoja '{WORKSHEET_NAME}' creada con {len(HEADERS)} columnas")
    
    # Formatear header
    try:
        worksheet.format('A1:W1', {
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}},
            'horizontalAlignment': 'CENTER'
        })
        print("✅ Header formateado")
    except Exception as e:
        print(f"⚠️  No se pudo formatear el header: {e}")
    
    # Compartir con el correo
    print(f"🔗 Compartiendo sheet con {EMAIL_COMPARTIR}...")
    try:
        sh.share(EMAIL_COMPARTIR, perm_type='user', role='writer')
        print(f"✅ Sheet compartido con {EMAIL_COMPARTIR}")
    except Exception as e:
        print(f"⚠️  Error compartiendo sheet: {e}")
        print(f"   Puedes compartirlo manualmente desde: {sh.url}")
    
    # Mostrar información
    print("\n" + "="*60)
    print("✅ Sheet configurado exitosamente!")
    print("="*60)
    print(f"📊 Nombre: {sh.title}")
    print(f"📋 Hoja: {WORKSHEET_NAME}")
    print(f"🔗 URL: {sh.url}")
    print(f"🆔 ID: {SHEET_ID}")
    print(f"📧 Compartido con: {EMAIL_COMPARTIR}")
    print(f"📏 Columnas: {len(HEADERS)}")
    print("\nColumnas configuradas:")
    for i, header in enumerate(HEADERS, 1):
        print(f"  {i:2d}. {header}")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
