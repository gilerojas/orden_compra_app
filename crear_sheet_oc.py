#!/usr/bin/env python3
"""
Script para crear el Google Sheet de Órdenes de Compra.

Este script:
1. Crea un nuevo Google Sheet llamado "OrdenesCompra (OCS)"
2. Crea la hoja "OrdenesCompra" con los headers correctos
3. Comparte el sheet con el correo especificado
4. Configura permisos de edición

Uso:
    python crear_sheet_oc.py
"""

import os
import sys
from pathlib import Path

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent))

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ Error: Faltan dependencias")
    print("Instala con: pip install gspread google-auth google-auth-oauthlib")
    sys.exit(1)

# Configuración
SPREADSHEET_NAME = "OrdenesCompra (OCS)"
WORKSHEET_NAME = "OrdenesCompra"
EMAIL_COMPARTIR = "gilerojas@gmail.com"

# Headers basados en los datos que extraemos
HEADERS = [
    "Numero Orden",
    "Fecha",
    "Proveedor",
    "Direccion Proveedor",
    "RNC",
    "Terminos",
    "Moneda",
    "Codigo Suplidor",
    "Codigo Producto",
    "Descripcion",
    "Cantidad",
    "Unidad",
    "Precio",
    "Descuento %",
    "Impuesto %",
    "Importe",
    "Monto Descuento",
    "Monto Impuesto",
    "Total por Producto",
    "Subtotal",
    "Total",
    "Fecha_Ultima_Mod",
    "Estado"
]


def obtener_credenciales():
    """Obtiene las credenciales de Google Cloud Platform."""
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Buscar archivo de credenciales (prioridad al nuevo archivo)
    posibles_rutas = [
        Path(__file__).parent / "idyllic-striker-454314-r7-c28d9f15d391.json",  # Nuevo archivo
        Path(__file__).parent / "secrets_gsheets.json",
        Path(__file__).parent.parent / "secrets_gsheets.json",
        Path(__file__).parent.parent / "orden_despacho_app" / "secrets_gsheets.json",
    ]
    
    for ruta in posibles_rutas:
        if ruta.exists():
            print(f"✅ Usando credenciales: {ruta}")
            return Credentials.from_service_account_file(str(ruta), scopes=SCOPES)
    
    raise FileNotFoundError(
        "❌ No se encontró el archivo de credenciales\n"
        "Asegúrate de tener el archivo JSON de credenciales en el directorio del proyecto"
    )


def crear_sheet():
    """Crea el Google Sheet y configura la hoja."""
    print("🔐 Obteniendo credenciales...")
    creds = obtener_credenciales()
    
    print("📊 Conectando con Google Sheets...")
    gc = gspread.authorize(creds)
    
    # Verificar si el sheet ya existe
    try:
        sh = gc.open(SPREADSHEET_NAME)
        print(f"✅ El sheet '{SPREADSHEET_NAME}' ya existe")
    except gspread.SpreadsheetNotFound:
        print(f"📝 Intentando crear nuevo sheet: '{SPREADSHEET_NAME}'...")
        try:
            sh = gc.create(SPREADSHEET_NAME)
            print(f"✅ Sheet creado con ID: {sh.id}")
        except Exception as e:
            if "quota" in str(e).lower() or "storage" in str(e).lower():
                print("\n" + "="*60)
                print("⚠️  ERROR: Cuota de almacenamiento de Google Drive excedida")
                print("="*60)
                print("\nOpciones:")
                print("1. Crear el sheet manualmente y usar su ID")
                print("2. Limpiar espacio en Google Drive")
                print("3. Usar un sheet existente")
                print("\nPara crear manualmente:")
                print("1. Ve a https://sheets.google.com")
                print(f"2. Crea un nuevo sheet llamado '{SPREADSHEET_NAME}'")
                print("3. Copia el ID del sheet de la URL")
                print("   (ej: https://docs.google.com/spreadsheets/d/ID_AQUI/edit)")
                print("4. Ejecuta este script con el ID:")
                print("   python crear_sheet_oc.py --sheet-id ID_AQUI")
                print("\nO modifica este script y agrega el ID directamente.")
                return
            else:
                raise
    
    # Crear o actualizar la hoja
    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
        print(f"⚠️  La hoja '{WORKSHEET_NAME}' ya existe")
        respuesta = input("¿Deseas sobrescribir los headers? (s/n): ").lower()
        if respuesta == 's':
            worksheet.clear()
            worksheet.update('A1', [HEADERS], value_input_option="USER_ENTERED")
            print(f"✅ Headers actualizados en '{WORKSHEET_NAME}'")
        else:
            print("✅ Usando hoja existente")
    except gspread.WorksheetNotFound:
        print(f"📋 Creando hoja '{WORKSHEET_NAME}'...")
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(HEADERS))
        worksheet.update('A1', [HEADERS], value_input_option="USER_ENTERED")
        print(f"✅ Hoja '{WORKSHEET_NAME}' creada con {len(HEADERS)} columnas")
    
    # Formatear header (negrita, fondo)
    try:
        worksheet.format('A1:Z1', {
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
    print("✅ Sheet creado exitosamente!")
    print("="*60)
    print(f"📊 Nombre: {SPREADSHEET_NAME}")
    print(f"📋 Hoja: {WORKSHEET_NAME}")
    print(f"🔗 URL: {sh.url}")
    print(f"📧 Compartido con: {EMAIL_COMPARTIR}")
    print(f"📏 Columnas: {len(HEADERS)}")
    print("\nColumnas configuradas:")
    for i, header in enumerate(HEADERS, 1):
        print(f"  {i:2d}. {header}")
    print("="*60)


def usar_sheet_existente(sheet_id: str):
    """Configura un sheet existente usando su ID."""
    print("🔐 Obteniendo credenciales...")
    creds = obtener_credenciales()
    
    print("📊 Conectando con Google Sheets...")
    gc = gspread.authorize(creds)
    
    try:
        sh = gc.open_by_key(sheet_id)
        print(f"✅ Sheet encontrado: {sh.title}")
    except Exception as e:
        print(f"❌ Error abriendo sheet: {e}")
        print("Verifica que:")
        print("1. El ID del sheet sea correcto")
        print("2. La cuenta de servicio tenga acceso al sheet")
        return
    
    # Continuar con la configuración de la hoja
    try:
        worksheet = sh.worksheet(WORKSHEET_NAME)
        print(f"⚠️  La hoja '{WORKSHEET_NAME}' ya existe")
        respuesta = input("¿Deseas sobrescribir los headers? (s/n): ").lower()
        if respuesta == 's':
            worksheet.clear()
            worksheet.update('A1', [HEADERS], value_input_option="USER_ENTERED")
            print(f"✅ Headers actualizados en '{WORKSHEET_NAME}'")
        else:
            print("✅ Usando hoja existente")
    except gspread.WorksheetNotFound:
        print(f"📋 Creando hoja '{WORKSHEET_NAME}'...")
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(HEADERS))
        worksheet.update('A1', [HEADERS], value_input_option="USER_ENTERED")
        print(f"✅ Hoja '{WORKSHEET_NAME}' creada con {len(HEADERS)} columnas")
    
    # Formatear header
    try:
        worksheet.format('A1:Z1', {
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
    print(f"🆔 ID: {sheet_id}")
    print(f"📧 Compartido con: {EMAIL_COMPARTIR}")
    print(f"📏 Columnas: {len(HEADERS)}")
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Crear o configurar Google Sheet para Órdenes de Compra')
    parser.add_argument('--sheet-id', type=str, help='ID de un sheet existente para configurar')
    args = parser.parse_args()
    
    try:
        if args.sheet_id:
            usar_sheet_existente(args.sheet_id)
        else:
            crear_sheet()
    except KeyboardInterrupt:
        print("\n❌ Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
