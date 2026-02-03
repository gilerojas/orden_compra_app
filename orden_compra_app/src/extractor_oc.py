"""
extractor_oc.py

Extrae y normaliza los datos clave de Órdenes de Compra (PDF).
Basado en extractor_mon.py para mantener consistencia con el formato Monica.

Formato esperado: Orden de Compra de SOLUCIONES QUIMICAS MG SRL
Similar a facturas Monica formato clásico con tabla estructurada.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Dict
import pdfplumber
import pandas as pd

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Configuración global (similar a extractor_mon.py)
CONFIG = {
    "table_settings": {
        "vertical_strategy": "lines",
        "horizontal_strategy": "text",
        "snap_tolerance": 3,
        "join_tolerance": 3
    },
    "orden_header": "Itm",  # Header de la tabla de productos
    "campos_requeridos": ["Codigo Producto", "Descripcion", "Cantidad"],
    "decimales": 3
}

# Utilidades genéricas
NUMERO_ORDEN_RE = re.compile(r"N°\s*Orden\s*:?\s*(\d+)", re.IGNORECASE)
FECHA_RE = re.compile(r"Fecha\s*:?\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
RNC_RE = re.compile(r"RNC\s*:?\s*(\d+)", re.IGNORECASE)
MONEDA_RE = re.compile(r"(USD|DOP|US\s*\$|Extranjera\s*US\s*\$)", re.IGNORECASE)


def configurar_logging(debug: bool = False):
    """Configura el nivel de logging"""
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)


def extraer_datos_generales(tabla_cruda: List[List], texto: str) -> Dict:
    """
    Extrae metadatos de órdenes de compra (similar a extractor_mon.py).
    Busca en la tabla estructurada y en el texto.
    """
    datos = {
        "Proveedor": None,
        "Direccion Proveedor": None,
        "RNC": None,
        "Terminos": None,
        "Moneda": "USD",
        "Codigo Suplidor": None,
    }
    
    try:
        lineas = texto.split('\n')
        
        # Buscar proveedor en texto (después de "Solicitado a:")
        # Formato: "Solicitado a: Enviar a:\nPROVEEDOR ..."
        for i, linea in enumerate(lineas):
            if "Solicitado a:" in linea:
                # La siguiente línea puede tener el proveedor
                if i + 1 < len(lineas):
                    siguiente = lineas[i + 1].strip()
                    # Separar proveedor y cliente (están en la misma línea separados por espacios)
                    partes = siguiente.split("SOLUCIONES QUIMICAS")
                    if partes:
                        datos["Proveedor"] = partes[0].strip()
                break
        
        # Buscar dirección del proveedor (línea con "AV." o similar)
        for i, linea in enumerate(lineas):
            if "AV." in linea or "C/" in linea:
                # Separar dirección proveedor y dirección cliente
                if "C/ Jatfres" in linea:
                    partes = linea.split("C/ Jatfres")
                    if partes:
                        datos["Direccion Proveedor"] = partes[0].strip()
                else:
                    datos["Direccion Proveedor"] = linea.strip()
                break
        
        # Buscar en tabla estructurada (similar a Monica)
        for i, row in enumerate(tabla_cruda):
            if not row:
                continue
            
            # Buscar fila con "Código Suplidor" y extraer datos de la siguiente fila
            if "Código Suplidor" in str(row[0]) or "Codigo Suplidor" in str(row[0]):
                if i + 2 < len(tabla_cruda):
                    fila_datos = tabla_cruda[i + 2]
                    if len(fila_datos) > 0:
                        datos["Codigo Suplidor"] = str(fila_datos[0]).strip() if fila_datos[0] else None
                    if len(fila_datos) > 3:
                        datos["RNC"] = str(fila_datos[3]).strip() if fila_datos[3] else None
                    if len(fila_datos) > 9:
                        datos["Terminos"] = str(fila_datos[9]).strip() if fila_datos[9] else None
            
            # Buscar moneda (fila con "Vendedor" y "Moneda")
            if "Moneda" in str(row[0]):
                if i + 2 < len(tabla_cruda):
                    fila_moneda = tabla_cruda[i + 2]
                    if len(fila_moneda) > 3:
                        moneda_raw = str(fila_moneda[3]).strip() if fila_moneda[3] else ""
                        if "USD" in moneda_raw.upper() or "US" in moneda_raw.upper() or "Extranjera" in moneda_raw:
                            datos["Moneda"] = "USD"
                        elif "DOP" in moneda_raw.upper():
                            datos["Moneda"] = "DOP"
    
    except Exception as e:
        logger.error(f"Error extrayendo datos generales: {str(e)}")
    
    return datos


def extraer_numero_y_fecha(texto: str) -> tuple:
    """Extrae número de orden y fecha (similar a extractor_mon.py)"""
    try:
        # Buscar número de orden (puede ser "Nº Orden" o "N° Orden")
        match_orden = re.search(r"N[º°°]\s*Orden\s*[:]?\s*(\d+)", texto, re.IGNORECASE)
        num_orden = match_orden.group(1) if match_orden else None
        
        # Buscar fecha (formato: "Fecha DD/MM/YYYY")
        match_fecha = re.search(r"Fecha\s+(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
        fecha = match_fecha.group(1) if match_fecha else None
        
        return (num_orden, fecha)
    except Exception as e:
        logger.error(f"Error buscando número/fecha: {str(e)}")
        return (None, None)


# Función legacy eliminada - ahora se usa extraer_datos_generales (basada en extractor_mon.py)


def procesar_tabla_productos(raw_data: List[List], page_num: int) -> pd.DataFrame:
    """
    Procesa tabla de productos en formato de orden de compra (similar a extractor_mon.py).
    
    Busca header "Itm" y procesa filas de productos.
    """
    try:
        # Buscar inicio de tabla (header "Itm")
        start_idx = next(
            (i for i, row in enumerate(raw_data) if row and str(row[0]).strip() == CONFIG["orden_header"]),
            None,
        )
        if start_idx is None:
            logger.warning(f"Página {page_num}: No se encontró inicio de tabla (header '{CONFIG['orden_header']}')")
            return pd.DataFrame()
        
        productos = []
        current_product = None
        
        # Procesar filas después del header
        for row in raw_data[start_idx + 1:]:
            try:
                if not any(row):
                    continue
                
                # Verificar si es fila de producto (tiene código en columna 1 y Itm numérico en columna 0)
                itm = str(row[0]).strip() if len(row) > 0 and row[0] else ""
                codigo = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                
                # Es fila de producto si tiene Itm numérico y código
                if itm.isdigit() and codigo:
                    # Guardar producto anterior si existe
                    if current_product:
                        productos.append(current_product)
                    
                    # Extraer datos del producto según estructura real:
                    # [Itm, Codigo, Descripcion, None, Bodg., Cantidad, Unid., None, Precio, None, Dto.%, Imp.%, None, Importe]
                    descripcion = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                    
                    # Cantidad (columna 5)
                    cantidad_str = str(row[5]).replace(",", "").strip() if len(row) > 5 and row[5] else "0"
                    try:
                        cantidad = float(cantidad_str) if cantidad_str else 0.0
                    except:
                        cantidad = 0.0
                    
                    # Unidad (columna 6)
                    unidad = str(row[6]).strip() if len(row) > 6 and row[6] else "UN"
                    if not unidad or unidad == "":
                        unidad = "UN"  # Default
                    
                    # Precio (columna 8)
                    precio_str = str(row[8]).replace(",", "").strip() if len(row) > 8 and row[8] else "0"
                    try:
                        precio = float(precio_str) if precio_str else 0.0
                    except:
                        precio = 0.0
                    
                    # Descuento % (columna 10)
                    descuento_pct = 0.0
                    if len(row) > 10 and row[10]:
                        desc_str = str(row[10]).replace("%", "").replace(",", "").strip()
                        try:
                            descuento_pct = float(desc_str) if desc_str else 0.0
                        except:
                            pass
                    
                    # Impuesto % (columna 11)
                    impuesto_pct = 0.0
                    if len(row) > 11 and row[11]:
                        imp_str = str(row[11]).replace("%", "").replace(",", "").strip()
                        try:
                            impuesto_pct = float(imp_str) if imp_str else 0.0
                        except:
                            pass
                    
                    # Importe (columna 13)
                    importe_str = str(row[13]).replace(",", "").strip() if len(row) > 13 and row[13] else "0"
                    try:
                        importe = float(importe_str) if importe_str else (cantidad * precio)
                    except:
                        importe = cantidad * precio
                    
                    # Validar que tenga código o descripción
                    if codigo or descripcion:
                        current_product = [
                            codigo,
                            descripcion,
                            cantidad,
                            unidad,
                            precio,
                            descuento_pct,
                            impuesto_pct,
                            importe,
                        ]
                
                # Si no hay Itm pero hay descripción en columna 2, puede ser continuación de descripción
                elif current_product and not itm.isdigit() and len(row) > 2 and row[2] and str(row[2]).strip():
                    # Continuar descripción en múltiples líneas
                    descripcion_extra = str(row[2]).strip()
                    # Solo agregar si no es numérico y no está vacío
                    if descripcion_extra and not descripcion_extra.replace(".", "").replace(",", "").isdigit():
                        current_product[1] += " " + descripcion_extra
                
                # Detectar fin de tabla (filas de totales)
                primera_celda = str(row[0] if row[0] else "").upper().strip()
                if any(keyword in primera_celda for keyword in ["SUBTOTAL", "TOTAL", "IMPUESTO", "IMpto", "AVISO", "FIRMA"]):
                    if current_product:
                        productos.append(current_product)
                    current_product = None
                    break
                    
            except (IndexError, ValueError) as e:
                logger.warning(f"Fila inválida: {row[:5]}. Error: {str(e)}")
                continue
        
        # Agregar último producto
        if current_product:
            productos.append(current_product)
        
        if not productos:
            logger.warning(f"Página {page_num}: No se encontraron productos")
            return pd.DataFrame()
        
        # Crear DataFrame
        columnas = [
            "Codigo Producto",
            "Descripcion",
            "Cantidad",
            "Unidad",
            "Precio",
            "Descuento %",
            "Impuesto %",
            "Importe",
        ]
        df = pd.DataFrame(productos, columns=columnas)
        
        # Validar columnas requeridas
        if not all(col in df.columns for col in CONFIG["campos_requeridos"]):
            logger.error(f"Página {page_num}: Faltan columnas requeridas")
            return pd.DataFrame()
        
        # Convertir a numérico
        numeric_cols = ["Cantidad", "Precio", "Descuento %", "Impuesto %", "Importe"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").round(CONFIG["decimales"])
        
        # Calcular campos derivados
        df["Monto Descuento"] = (df["Importe"] * (df["Descuento %"] / 100)).round(CONFIG["decimales"])
        df["Monto Impuesto"] = (df["Importe"] * (df["Impuesto %"] / 100)).round(CONFIG["decimales"])
        df["Total por Producto"] = (df["Importe"] + df["Monto Impuesto"] - df["Monto Descuento"]).round(CONFIG["decimales"])
        
        # Eliminar filas inválidas
        df = df.dropna(subset=["Total por Producto"])
        
        return df
    
    except Exception as e:
        logger.error(f"Error crítico en página {page_num}: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


# Funciones obsoletas eliminadas - ahora se usa procesar_tabla_productos y _extraer_totales_del_texto


def procesar_pagina(pdf_page, page_num: int) -> pd.DataFrame:
    """
    Procesa una página de orden de compra (similar a procesar_pagina_clasica de extractor_mon.py).
    
    Args:
        pdf_page: Página de pdfplumber.
        page_num: Índice de página (0-based).
    """
    try:
        texto = pdf_page.extract_text()
        if not texto:
            logger.warning(f"Página {page_num}: No se pudo extraer texto")
            return pd.DataFrame()
        
        # Extraer tabla usando find_table (como extractor_mon.py)
        try:
            tabla_cruda = pdf_page.find_table(table_settings=CONFIG["table_settings"]).extract()
        except Exception as e:
            logger.warning(f"Página {page_num}: No se pudo extraer tabla estructurada: {e}")
            # Fallback: intentar extract_tables()
            tabla_cruda = pdf_page.extract_tables()
            if tabla_cruda:
                tabla_cruda = tabla_cruda[0]  # Usar primera tabla
            else:
                tabla_cruda = []
        
        # Extraer metadatos
        datos_generales = extraer_datos_generales(tabla_cruda, texto)
        num_orden, fecha = extraer_numero_y_fecha(texto)
        datos_generales.update({
            "Numero Orden": num_orden,
            "Fecha": fecha
        })
        
        # Procesar tabla de productos
        df = procesar_tabla_productos(tabla_cruda, page_num)
        if df.empty:
            return pd.DataFrame()
        
        # Agregar metadatos a cada fila
        for key, value in datos_generales.items():
            df[key] = value
        
        # Extraer totales del texto
        totales = _extraer_totales_del_texto(texto)
        df["Subtotal"] = totales.get("subtotal", 0.0)
        df["Monto Impuesto"] = totales.get("impuesto", 0.0)
        df["Total"] = totales.get("total", 0.0)
        
        # Ordenar columnas
        columnas_orden = [
            "Numero Orden", "Fecha", "Proveedor", "Direccion Proveedor", "RNC", "Terminos",
            "Moneda", "Codigo Suplidor",
            "Codigo Producto", "Descripcion", "Cantidad", "Unidad",
            "Precio", "Descuento %", "Impuesto %", "Importe",
            "Monto Descuento", "Monto Impuesto", "Total por Producto",
            "Subtotal", "Total"
        ]
        
        # Asegurar que todas las columnas existan
        for col in columnas_orden:
            if col not in df.columns:
                df[col] = None
        
        return df[columnas_orden]
    
    except Exception as e:
        logger.error(f"Fallo en página {page_num}: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def _extraer_totales_del_texto(texto: str) -> Dict[str, float]:
    """
    Extrae totales de la orden de compra desde el texto.
    """
    totales = {
        "subtotal": 0.0,
        "impuesto": 0.0,
        "total": 0.0
    }
    
    try:
        # Buscar subtotal (puede estar en formato "Subtotal 3,486.20")
        match = re.search(r"Subtotal\s+(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", texto, re.IGNORECASE)
        if match:
            totales["subtotal"] = float(match.group(1).replace(",", ""))
        
        # Buscar impuesto (puede estar como "Impto. 627.52")
        match = re.search(r"Impto\.?\s+(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", texto, re.IGNORECASE)
        if match:
            totales["impuesto"] = float(match.group(1).replace(",", ""))
        
        # Buscar total (puede estar como "T O T A L 4,113.72" con espacios)
        # El patrón debe permitir espacios entre letras
        match = re.search(r"T\s+O\s+T\s+A\s+L\s+(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", texto, re.IGNORECASE)
        if match:
            totales["total"] = float(match.group(1).replace(",", ""))
        else:
            # Fallback: buscar "TOTAL" normal (sin espacios)
            match = re.search(r"TOTAL\s+(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", texto, re.IGNORECASE)
            if match:
                totales["total"] = float(match.group(1).replace(",", ""))
    
    except Exception as e:
        logger.warning(f"Error extrayendo totales: {e}")
    
    return totales


def procesar_pdf(ruta_pdf: str, debug: bool = False) -> pd.DataFrame:
    """
    Procesa un PDF de Orden de Compra y extrae los datos.
    Basado en extractor_mon.py para mantener consistencia.
    
    Args:
        ruta_pdf: Ruta al archivo PDF
        debug: Si True, muestra información de debug
    
    Returns:
        DataFrame con los datos extraídos
    """
    configurar_logging(debug)
    
    try:
        logger.info(f"📄 Procesando PDF: {ruta_pdf}")
        
        resultados = []
        with pdfplumber.open(ruta_pdf) as pdf:
            total_paginas = len(pdf.pages)
            
            if total_paginas == 0:
                logger.error("PDF vacío")
                return pd.DataFrame()
            
            # Procesar todas las páginas
            for i in range(total_paginas):
                logger.info(f"Procesando página {i + 1}/{total_paginas}")
                page_data = procesar_pagina(pdf.pages[i], i)
                if not page_data.empty:
                    resultados.append(page_data)
        
        if not resultados:
            logger.error("No se extrajeron datos del PDF")
            return pd.DataFrame()
        
        # Concatenar resultados de todas las páginas
        df = pd.concat(resultados, ignore_index=True)
        
        numero_orden = df["Numero Orden"].iloc[0] if "Numero Orden" in df.columns and not df.empty else "N/A"
        logger.info(f"✅ Extraídos {len(df)} productos de orden {numero_orden}")
        
        return df
    
    except Exception as e:
        logger.error(f"❌ Error procesando PDF: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
        df = procesar_pdf(ruta, debug=True)
        print(f"\n{'='*60}")
        print(f"Resultado: {len(df)} productos")
        print(f"{'='*60}")
        if not df.empty:
            print(df.to_string())
    else:
        print("Uso: python extractor_oc.py <ruta_pdf>")
