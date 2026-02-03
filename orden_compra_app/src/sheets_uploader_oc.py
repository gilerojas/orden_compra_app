"""
sheets_uploader_oc.py

Módulo para subir datos extraídos de órdenes de compra a Google Sheets.
Diseñado para funcionar tanto en local como en Streamlit Cloud.
"""

import os
import hashlib
from typing import Dict, Optional
import logging

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Configurar logger
logger = logging.getLogger("sheets_uploader_oc")


def calcular_hash_oc(df: pd.DataFrame) -> str:
    """
    Genera un hash MD5 robusto de la orden de compra (metadatos + productos)
    para detección de duplicados y de modificaciones (como en orden_despacho).
    """
    if df is None or df.empty:
        return "0" * 12

    meta_cols = ["Numero Orden", "Fecha", "Proveedor", "Total"]
    meta_parts = []
    for col in meta_cols:
        if col in df.columns:
            val = df[col].iloc[0]
            if pd.isna(val):
                meta_parts.append("")
            elif col == "Total":
                try:
                    meta_parts.append(f"{float(val):.2f}")
                except (TypeError, ValueError):
                    meta_parts.append(str(val).strip())
            else:
                meta_parts.append(str(val).strip())
        else:
            meta_parts.append("")
    meta_str = "|".join(meta_parts)

    columnas_producto = [
        "Codigo Producto", "Descripcion", "Cantidad", "Unidad", "Precio", "Importe",
    ]
    cols_disponibles = [c for c in columnas_producto if c in df.columns]
    if not cols_disponibles:
        return hashlib.md5(meta_str.encode("utf-8")).hexdigest()[:12]

    df_hash = df[cols_disponibles].copy()
    for col in cols_disponibles:
        df_hash[col] = df_hash[col].fillna("").astype(str).str.strip()
        if col in ("Cantidad", "Precio", "Importe"):
            try:
                df_hash[col] = pd.to_numeric(df_hash[col].str.replace(",", ""), errors="coerce")
                df_hash[col] = df_hash[col].fillna(0).round(2).astype(str)
            except Exception:
                pass

    if "Codigo Producto" in df_hash.columns:
        df_hash = df_hash.sort_values("Codigo Producto").reset_index(drop=True)
    elif "Descripcion" in df_hash.columns:
        df_hash = df_hash.sort_values("Descripcion").reset_index(drop=True)

    lineas = []
    for _, row in df_hash.iterrows():
        valores = [str(row[c]) for c in sorted(cols_disponibles)]
        lineas.append("|".join(valores))
    productos_str = "\n".join(lineas)
    contenido = f"{meta_str}\n{productos_str}"
    return hashlib.md5(contenido.encode("utf-8")).hexdigest()[:12]

# Configuración
SPREADSHEET_NAME = "OrdenesCompra (OCS)"  # Puedes cambiar este nombre

# Headers esperados para órdenes de compra
# Orden: Metadatos -> Productos -> Totales -> Control (incl. hash para detectar modificaciones)
HEADERS_OC = [
    # Metadatos de la orden
    "Numero Orden",
    "Fecha",
    "Proveedor",
    "Direccion Proveedor",
    "RNC",
    "Terminos",
    "Moneda",
    "Codigo Suplidor",
    # Datos del producto
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
    # Totales de la orden
    "Subtotal",
    "Total",
    # Campos de control (hash para detectar modificaciones, como en orden_despacho)
    "Hash_OC",
    "Fecha_Ultima_Mod",
    "Estado"
]


def _get_credentials():
    """
    Obtiene las credenciales de Google Cloud Platform.
    
    Detecta automáticamente si está corriendo en:
    - Streamlit Cloud: usa st.secrets
    - Local: usa archivo secrets_gsheets.json
    
    Returns:
        Credentials: Objeto de credenciales de Google
    """
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            sa = st.secrets["gcp_service_account"]
            if isinstance(sa, str):
                import json
                sa = json.loads(sa)
            else:
                sa = dict(sa)
            print("✅ Usando credenciales de Streamlit Secrets (producción)")
            return Credentials.from_service_account_info(sa, scopes=SCOPES)
    except (ImportError, KeyError, TypeError, ValueError) as e:
        pass
    
    # Fallback: usar archivo local (buscar nuevo archivo primero)
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    posibles_rutas = [
        os.path.join(base_path, "idyllic-striker-454314-r7-c28d9f15d391.json"),  # Nuevo archivo
        os.path.join(base_path, "secrets_gsheets.json"),
        os.path.join(os.path.dirname(base_path), "orden_despacho_app", "secrets_gsheets.json"),
    ]
    
    for local_path in posibles_rutas:
        if os.path.exists(local_path):
            print(f"✅ Usando credenciales de archivo local: {local_path}")
            return Credentials.from_service_account_file(local_path, scopes=SCOPES)
    
    # Si no encuentra nada
    raise FileNotFoundError(
        "❌ No se encontraron credenciales de Google Cloud.\n"
        "- En Streamlit Cloud: configura st.secrets['gcp_service_account']\n"
        "- En local: asegúrate de tener secrets_gsheets.json en la raíz del proyecto"
    )


def _abrir_hoja(nombre_worksheet: str = "OrdenesCompra") -> gspread.Worksheet:
    """
    Abre o crea una worksheet en el spreadsheet configurado.
    
    Args:
        nombre_worksheet: Nombre de la hoja (default: "OrdenesCompra")
    
    Returns:
        gspread.Worksheet: Objeto de la hoja de cálculo
    """
    creds = _get_credentials()
    gc = gspread.authorize(creds)
    sh = gc.open(SPREADSHEET_NAME)
    
    try:
        return sh.worksheet(nombre_worksheet)
    except gspread.WorksheetNotFound:
        print(f"⚠️ Hoja '{nombre_worksheet}' no existe, creándola...")
        ws = sh.add_worksheet(title=nombre_worksheet, rows=1, cols=1)
        # Inicializar headers
        ws.update('A1', [HEADERS_OC], value_input_option="USER_ENTERED")
        print(f"✅ Hoja '{nombre_worksheet}' creada con headers")
        return ws


def ya_existe_en_sheet(numero_orden: str) -> bool:
    """
    Verifica si un número de orden ya está registrado en la hoja.
    """
    try:
        ws = _abrir_hoja()
        valores = ws.get_all_values()
        
        if not valores or len(valores) < 2:
            return False

        headers = valores[0]
        
        if "Numero Orden" not in headers:
            print(f"⚠️ No se encontró columna 'Numero Orden'")
            return False

        idx = headers.index("Numero Orden")
        
        numero_limpio = str(numero_orden).strip().upper()
        
        for row in valores[1:]:  # Saltar header
            if len(row) > idx:
                valor_celda = str(row[idx]).strip().upper()
                if valor_celda == numero_limpio:
                    print(f"✓ Orden {numero_orden} encontrada en Sheets")
                    return True
        
        print(f"✓ Orden {numero_orden} NO existe en Sheets")
        return False
    
    except Exception as e:
        print(f"⚠️ Error al verificar duplicado: {e}")
        return False  # Fail-safe: permitir subida si hay error


def obtener_hash_orden_en_sheet(numero_orden: str) -> Optional[str]:
    """
    Devuelve el Hash_OC guardado para la primera fila con ese número de orden.
    Sirve para detectar si el PDF subido es una modificación (mismo número, contenido distinto).
    """
    try:
        ws = _abrir_hoja()
        valores = ws.get_all_values()
        if not valores or len(valores) < 2:
            return None
        headers = valores[0]
        idx_numero = headers.index("Numero Orden") if "Numero Orden" in headers else -1
        idx_hash = headers.index("Hash_OC") if "Hash_OC" in headers else -1
        if idx_numero < 0 or idx_hash < 0:
            return None
        numero_limpio = str(numero_orden).strip().upper()
        for row in valores[1:]:
            if len(row) > max(idx_numero, idx_hash):
                if str(row[idx_numero]).strip().upper() == numero_limpio:
                    h = str(row[idx_hash]).strip()
                    return h if h else None
        return None
    except Exception as e:
        logger.debug("Error obteniendo hash de orden %s: %s", numero_orden, e)
        return None


def subir_a_hoja(df: pd.DataFrame) -> Dict:
    """
    Sube datos de orden de compra a Google Sheets.
    
    Args:
        df: DataFrame con los datos a subir
    
    Returns:
        Dict con resultado: {"success": bool, "message": str, "rows_added": int}
    """
    try:
        logger.info("🔵 INICIO subir_a_hoja()")
        
        # Abrir hoja
        ws = _abrir_hoja()
        
        # Inicializar headers si es necesario
        headers_actuales = ws.row_values(1)
        if not headers_actuales or all(h.strip() == "" for h in headers_actuales):
            print(f"📋 Inicializando headers...")
            ws.update('A1', [HEADERS_OC], value_input_option="USER_ENTERED")
            print(f"✅ Headers creados: {len(HEADERS_OC)} columnas")
        
        # Verificar headers
        headers_en_sheet = ws.row_values(1)
        headers_faltantes = [h for h in HEADERS_OC if h not in headers_en_sheet]
        
        if headers_faltantes:
            error_msg = f"Headers faltantes en la hoja: {headers_faltantes}. "
            if headers_faltantes == ["Hash_OC"]:
                error_msg += "Agrega la columna 'Hash_OC' después de 'Total' y antes de 'Fecha_Ultima_Mod' para activar la detección de modificaciones."
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg.strip(),
                "rows_added": 0
            }
        
        # Preparar DataFrame
        for col in HEADERS_OC:
            if col not in df.columns:
                df[col] = ""
        
        # Agregar campos de control si no existen
        if "Fecha_Ultima_Mod" not in df.columns:
            df["Fecha_Ultima_Mod"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "Estado" not in df.columns:
            df["Estado"] = "Activa"
        # Hash para detectar modificaciones (como en orden_despacho)
        df["Hash_OC"] = calcular_hash_oc(df)
        
        # Ordenar según headers esperados
        df = df[HEADERS_OC]
        
        # Filtrar filas válidas
        if "Numero Orden" not in df.columns:
            error_msg = "Falta columna 'Numero Orden'"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "rows_added": 0
            }
        
        n_inicial = len(df)
        df = df[df["Numero Orden"].astype(str).str.strip() != ""]
        df = df[df["Numero Orden"].notna()]
        n_final = len(df)
        
        logger.info(f"📊 Filas válidas: {n_final}/{n_inicial}")
        
        if n_final == 0:
            error_msg = "No hay filas válidas (Numero Orden vacío)"
            logger.warning(f"⚠️ {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "rows_added": 0
            }
        
        # Bloquear duplicados: no se permite subir una orden que ya existe
        numero_orden = str(df["Numero Orden"].iloc[0]).strip()
        if ya_existe_en_sheet(numero_orden):
            error_msg = f"La orden {numero_orden} ya está registrada. No se permiten duplicados."
            logger.warning(f"🚫 {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "rows_added": 0
            }
        
        # Subir a Sheets
        filas = df.astype(str).values.tolist()
        
        logger.info(f"📤 Subiendo {len(filas)} filas...")
        ws.append_rows(filas, value_input_option="USER_ENTERED")
        
        logger.info(f"✅ ÉXITO: {len(filas)} filas subidas")
        
        return {
            "success": True,
            "message": f"Datos subidos exitosamente",
            "rows_added": len(filas)
        }
        
    except Exception as e:
        logger.error(f"❌ EXCEPCIÓN en subir_a_hoja(): {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "rows_added": 0
        }


if __name__ == "__main__":
    print("🧪 Testing sheets_uploader_oc...")
    
    try:
        ws = _abrir_hoja()
        print(f"✅ Conexión exitosa con hoja: {ws.title}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
