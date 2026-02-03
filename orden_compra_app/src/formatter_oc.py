"""
formatter_oc.py

Genera un PDF formateado de Orden de Compra a partir de los datos extraídos.
Incluye logo, datos del proveedor, tabla de productos y totales.

Uso:
- generar_orden_compra(df): título y tabla para preview
- exportar_orden_compra_a_pdf(df, output_path, logo_path): genera el PDF
"""

import pandas as pd
from typing import Tuple, Optional
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors


def _extrae(df: pd.DataFrame, key: str, default: str = "N/A") -> str:
    """Extrae valor de la primera fila por nombre de columna (normalizado)."""
    key_norm = key.lower().replace(" ", "_").replace("%", "pct")
    for col in df.columns:
        col_norm = col.lower().replace(" ", "_").replace("%", "pct")
        if col_norm == key_norm or key_norm in col_norm:
            val = df[col].iloc[0]
            return str(val).strip() if pd.notna(val) and str(val).strip() else default
    return default


def generar_orden_compra(df: pd.DataFrame) -> Tuple[str, pd.DataFrame]:
    """
    Dado un DataFrame de orden de compra extraído, devuelve:
    - Título para la orden
    - Tabla de productos (columnas principales)
    """
    if df.empty:
        raise ValueError("El DataFrame está vacío")

    numero_orden = _extrae(df, "numero_orden")
    fecha = _extrae(df, "fecha")
    proveedor = _extrae(df, "proveedor")

    titulo = f"Orden de Compra | {proveedor} | N° {numero_orden} | {fecha}"

    # Columnas para tabla resumida (sin metadatos repetidos)
    columnas_tabla = ["Codigo Producto", "Descripcion", "Cantidad", "Unidad", "Precio", "Importe"]
    existentes = [c for c in columnas_tabla if c in df.columns]
    tabla = df[existentes].copy() if existentes else df.copy()

    return titulo, tabla


def exportar_orden_compra_a_pdf(
    df: pd.DataFrame,
    output_path: Optional[str] = None,
    logo_path: Optional[str] = None,
) -> bytes:
    """
    Genera un PDF formateado de Orden de Compra con logo, datos del proveedor,
    tabla de productos y totales.

    Args:
        df: DataFrame con los datos extraídos (extractor_oc).
        output_path: Ruta donde guardar el PDF. Si es None, solo devuelve bytes.
        logo_path: Ruta al logo (ej: Logo_Solquim_Limpio.png).

    Returns:
        bytes del PDF generado.
    """
    if df.empty:
        raise ValueError("El DataFrame está vacío")

    # Colores SolQuim MG (misma identidad que Orden de Despacho)
    color_primario = colors.HexColor("#2c5f8d")
    color_secundario = colors.HexColor("#10B981")
    color_texto_header = colors.HexColor("#2c5f8d")

    # Metadatos
    meta = {
        "numero_orden": _extrae(df, "numero_orden"),
        "fecha": _extrae(df, "fecha"),
        "proveedor": _extrae(df, "proveedor"),
        "direccion": _extrae(df, "direccion_proveedor"),
        "rnc": _extrae(df, "rnc"),
        "terminos": _extrae(df, "terminos"),
        "moneda": _extrae(df, "moneda"),
        "codigo_suplidor": _extrae(df, "codigo_suplidor"),
    }
    def _num(col: str) -> float:
        if col not in df.columns:
            return 0.0
        try:
            return float(df[col].iloc[0])
        except (TypeError, ValueError):
            return 0.0

    subtotal = _num("Subtotal")
    total = _num("Total")
    impuesto = _num("Monto Impuesto")

    # Columnas para tabla de productos
    cols_tabla = ["Codigo Producto", "Descripcion", "Cantidad", "Unidad", "Precio", "Importe"]
    cols_disponibles = [c for c in cols_tabla if c in df.columns]
    if not cols_disponibles:
        raise ValueError("No se encontraron columnas de productos en el DataFrame")

    # Estilo Paragraph para descripción: word wrap dentro de la celda (celda se hace más alta)
    style_desc = ParagraphStyle(
        name="DescripcionOC",
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        alignment=TA_LEFT,
        textColor=colors.black,
        wordWrap="LTR",
        leftIndent=2,
        rightIndent=2,
    )

    # Construir filas: descripción como Paragraph para que haga wrap y la celda crezca en alto
    filas_datos = []
    for _, row in df[cols_disponibles].iterrows():
        fila = []
        for i, col in enumerate(cols_disponibles):
            val = str(row[col]) if pd.notna(row[col]) else ""
            if col == "Descripcion" and val:
                fila.append(Paragraph(val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style_desc))
            else:
                fila.append(val)
        filas_datos.append(fila)

    headers_tabla = cols_disponibles
    tabla_data = [headers_tabla] + filas_datos
    ncols = len(headers_tabla)

    # Anchos fijos para que Código no solape con Descripción (total útil ≈ 468 pt)
    ancho_total = 468
    # Código suficiente ancho; Descripción con el resto; números compactos
    w_codigo = 88
    w_cantidad = 48
    w_unidad = 42
    w_precio = 52
    w_importe = 58
    w_descripcion = ancho_total - w_codigo - w_cantidad - w_unidad - w_precio - w_importe  # ~180
    anchos = [w_codigo, w_descripcion, w_cantidad, w_unidad, w_precio, w_importe][:ncols]

    table = Table(tabla_data, colWidths=anchos)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), color_primario),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("ALIGN", (2, 0), (-2, -1), "CENTER"),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("LINEBELOW", (0, 0), (-1, 0), 2, color_secundario),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecfdf5")]),
    ]
    table.setStyle(TableStyle(estilo))

    # ─────────────────────────────────────────────────────────
    # Generar PDF
    # ─────────────────────────────────────────────────────────
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER

    y = height - 0.5 * inch

    # Logo (arriba a la izquierda, un poco más grande)
    if logo_path and Path(logo_path).exists():
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            logo_h = 0.65 * inch
            logo_w = (iw / ih) * logo_h
            c.drawImage(logo_path, inch, y - logo_h, width=logo_w, height=logo_h)
        except Exception:
            pass
        y -= logo_h + 10

    # Línea superior y título
    c.setStrokeColor(color_primario)
    c.setLineWidth(3)
    c.line(inch, y, width - inch, y)
    y -= 22

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(color_texto_header)
    c.drawString(inch, y, "ORDEN DE COMPRA")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawRightString(width - inch, y, f"N° Orden: {meta['numero_orden']}")
    y -= 24

    # Bloque proveedor
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(inch, y, "Proveedor:")
    c.setFont("Helvetica", 10)
    c.drawString(inch + 55, y, (meta["proveedor"] or "N/A")[:60])
    y -= 14

    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, y, "Fecha:")
    c.setFont("Helvetica", 10)
    c.drawString(inch + 55, y, meta["fecha"])
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch + 200, y, "RNC:")
    c.setFont("Helvetica", 10)
    c.drawString(inch + 230, y, meta["rnc"])
    y -= 14

    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, y, "Términos:")
    c.setFont("Helvetica", 10)
    c.drawString(inch + 55, y, (meta["terminos"] or "N/A")[:40])
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch + 200, y, "Moneda:")
    c.setFont("Helvetica", 10)
    c.drawString(inch + 250, y, meta["moneda"])
    y -= 20

    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.setLineWidth(1)
    c.line(inch, y, width - inch, y)
    y -= 18

    # Tabla de productos
    table.wrapOn(c, width - 2 * inch, height)
    th = table.wrap(width - 2 * inch, height)[1]
    table.drawOn(c, inch, y - th)
    y -= th + 20

    # Totales
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(width - inch - 120, y, "Subtotal:")
    c.drawRightString(width - inch, y, f"{meta['moneda']} {subtotal:,.2f}")
    y -= 14
    c.drawString(width - inch - 120, y, "Impuesto:")
    c.drawRightString(width - inch, y, f"{meta['moneda']} {impuesto:,.2f}")
    y -= 14
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(color_primario)
    c.drawString(width - inch - 120, y, "TOTAL:")
    c.drawRightString(width - inch, y, f"{meta['moneda']} {total:,.2f}")
    y -= 30

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(inch, y, "Documento generado automáticamente — Soluciones Químicas MG")
    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(inch, y, "Firma / Autorizado:")
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.line(inch + 95, y - 2, inch + 320, y - 2)

    c.save()
    buf.seek(0)
    pdf_bytes = buf.read()

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"✅ PDF generado: {output_path}")

    return pdf_bytes
