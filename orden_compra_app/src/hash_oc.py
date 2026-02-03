"""
hash_oc.py

Sistema de hash para Órdenes de Compra.
Permite detectar si una orden ya registrada fue modificada (mismo número, contenido distinto).

Inspirado en change_detector.py de orden_despacho_app.
"""

import hashlib
import pandas as pd
import logging

logger = logging.getLogger("orden_compra_app.hash_oc")


def calcular_hash_oc(df: pd.DataFrame) -> str:
    """
    Genera un hash MD5 robusto de la orden de compra (metadatos + productos)
    para detección de duplicados y de modificaciones.

    Incluye:
    - Metadatos: Numero Orden, Fecha, Proveedor, Total
    - Productos: Codigo Producto, Descripcion, Cantidad, Unidad, Precio, Importe
    (ordenados por Codigo Producto para consistencia)

    Args:
        df: DataFrame con los datos extraídos de la OC (extractor_oc).

    Returns:
        str: Hash MD5 de 12 caracteres (hex).
    """
    if df is None or df.empty:
        return "0" * 12

    # Metadatos (una sola fila, primera)
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

    # Columnas de productos para el hash (mismo criterio que orden_despacho)
    columnas_producto = [
        "Codigo Producto",
        "Descripcion",
        "Cantidad",
        "Unidad",
        "Precio",
        "Importe",
    ]
    cols_disponibles = [c for c in columnas_producto if c in df.columns]
    if not cols_disponibles:
        logger.warning("No se encontraron columnas de producto para hash")
        solo_meta = meta_str.encode("utf-8")
        return hashlib.md5(solo_meta).hexdigest()[:12]

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
    hash_completo = hashlib.md5(contenido.encode("utf-8")).hexdigest()
    hash_value = hash_completo[:12]

    logger.debug("Hash OC calculado: %s (%d productos)", hash_value, len(df_hash))
    return hash_value
