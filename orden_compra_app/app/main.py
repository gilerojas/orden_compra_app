"""
main.py

App de Streamlit para subir una Orden de Compra PDF, extraer datos con extractor_oc.py,
y visualizar los datos listos para subirlos a Google Sheets.
"""

import sys
import importlib.util
from pathlib import Path
import streamlit as st
import pandas as pd
import tempfile
from datetime import datetime
import logging

# ═══════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA (Debe ir primero)
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="Orden de Compra | Compras", layout="wide", page_icon="📋", initial_sidebar_state="expanded")

# ═══════════════════════════════════════════════════════════
# PATHS E IMPORTS
# ═══════════════════════════════════════════════════════════
root_path = Path(__file__).resolve().parent.parent
src_path = root_path / "src"
sys.path.insert(0, str(root_path))
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv
load_dotenv()

from extractor_oc import procesar_pdf
# Cargar sheets_uploader_oc desde src explícitamente (evita caché/ruta equivocada)
_sheets_spec = importlib.util.spec_from_file_location(
    "sheets_uploader_oc",
    src_path / "sheets_uploader_oc.py",
    submodule_search_locations=[str(src_path)],
)
sheets_uploader_oc = importlib.util.module_from_spec(_sheets_spec)
sys.modules["sheets_uploader_oc"] = sheets_uploader_oc
_sheets_spec.loader.exec_module(sheets_uploader_oc)

subir_a_hoja = sheets_uploader_oc.subir_a_hoja
ya_existe_en_sheet = sheets_uploader_oc.ya_existe_en_sheet
obtener_hash_orden_en_sheet = sheets_uploader_oc.obtener_hash_orden_en_sheet
calcular_hash_oc = sheets_uploader_oc.calcular_hash_oc

from formatter_oc import exportar_orden_compra_a_pdf

# WhatsApp (WaSender) — grupo test por defecto
try:
    from notification_manager_oc import enviar_orden_compra_pdf as enviar_oc_whatsapp
    WHATSAPP_OC_DISPONIBLE = True
except ImportError as e:
    logger.warning("WhatsApp OC no disponible: %s", e)
    WHATSAPP_OC_DISPONIBLE = False
    def enviar_oc_whatsapp(*args, **kwargs):
        return {"success": False, "error": "Módulo WhatsApp no disponible"}

# Configuración del logger
logger = logging.getLogger("orden_compra_app")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ══════════════════════════════════════════════════════════
# 🔐 SISTEMA DE AUTENTICACIÓN (OPCIONAL)
# ══════════════════════════════════════════════════════════

def check_password():
    """
    Verifica contraseña contra Admin o Basic y asigna roles.
    """
    
    def password_entered():
        """Callback para validar password"""
        try:
            pwd_basic = st.secrets.get("passwords", {}).get("basic", "")
            pwd_admin = st.secrets.get("passwords", {}).get("admin", "")
        except Exception:
            # Sin secrets.toml o error al leer: permitir acceso sin contraseña
            st.session_state["password_correct"] = True
            st.session_state["role"] = "BASIC"
            st.session_state["user_name"] = "Usuario"
            if "password" in st.session_state:
                del st.session_state["password"]
            return

        entered = st.session_state.get("password", "")

        if entered == pwd_admin:
            st.session_state["password_correct"] = True
            st.session_state["role"] = "ADMIN"
            st.session_state["user_name"] = "Gil"
            del st.session_state["password"]
        elif entered == pwd_basic:
            st.session_state["password_correct"] = True
            st.session_state["role"] = "BASIC"
            st.session_state["user_name"] = "Usuario"
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Si no está autenticado
    if "password_correct" not in st.session_state:
        try:
            pwd_basic = st.secrets.get("passwords", {}).get("basic", "")
            pwd_admin = st.secrets.get("passwords", {}).get("admin", "")
            if not pwd_basic and not pwd_admin:
                st.session_state["password_correct"] = True
                st.session_state["role"] = "BASIC"
                st.session_state["user_name"] = "Usuario"
                return True
        except Exception:
            # No secrets.toml o "No secrets found": permitir acceso
            st.session_state["password_correct"] = True
            st.session_state["role"] = "BASIC"
            st.session_state["user_name"] = "Usuario"
            return True
        
        st.markdown("""
        <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #0D9488 0%, #059669 50%, #D97706 100%); 
                    border-radius: 12px; color: white; margin-bottom: 1.5rem;'>
            <h1 style='color: white; margin: 0;'>📋 Orden de Compra</h1>
            <p style='margin: 0.5rem 0 0 0; opacity: 0.95;'>Sistema de Compras — Inicia sesión para continuar</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.text_input(
            "🔑 Contraseña", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    
    elif not st.session_state.get("password_correct", True):
        st.markdown("""
        <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #0D9488 0%, #059669 100%); 
                    border-radius: 12px; color: white; margin-bottom: 1rem;'>
            <h1 style='color: white; margin: 0;'>📋 Orden de Compra</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.text_input(
            "🔑 Contraseña", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ Contraseña incorrecta")
        return False
    
    else:
        return True

# ══════════════════════════════════════════════════════════
# 🚪 BLOQUEO DE ACCESO Y UI SEGÚN ROL
# ══════════════════════════════════════════════════════════

if not check_password():
    st.stop()

# Obtener rol y nombre
role = st.session_state.get("role", "BASIC")
user_name = st.session_state.get("user_name", "Usuario")

# ══════════════════════════════════════════════════════════
# 🎨 INTERFAZ PRINCIPAL — Orden de Compra (identidad distinta a Orden de Despacho)
# ══════════════════════════════════════════════════════════

st.markdown("""
<div style='background: linear-gradient(135deg, #0D9488 0%, #059669 100%); color: white; padding: 1rem 1.25rem; 
            border-radius: 10px; margin-bottom: 1rem; border-left: 6px solid #D97706;'>
    <span style='font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.9;'>Sistema de Compras</span>
    <h2 style='color: white; margin: 0.25rem 0 0 0; font-weight: 700;'>📋 Procesador de Orden de Compra</h2>
    <p style='margin: 0.25rem 0 0 0; opacity: 0.9; font-size: 0.95rem;'>Extrae datos del PDF y súbelos a Google Sheets</p>
</div>
""", unsafe_allow_html=True)
st.caption(f"Conectado como **{user_name}** ({role})")

st.markdown("Sube una **orden de compra en PDF** para extraer los datos y registrarlos en la hoja de compras.")
uploaded_file = st.file_uploader("📄 Arrastra o selecciona el PDF de la orden de compra", type=["pdf"])

# ══════════════════════════════════════════════════════════
# LOGICA DE PROCESAMIENTO Y SUBIDA
# ══════════════════════════════════════════════════════════

def procesar_y_subir_oc(df, logo_path=None):
    """
    Verifica duplicados y, si no hay OC duplicada, sube automáticamente a Google Sheets
    y envía el PDF al grupo de WhatsApp (como en orden de despacho).
    """
    st.markdown("---")
    numero_orden = df["Numero Orden"].iloc[0] if "Numero Orden" in df.columns else None

    if not numero_orden:
        st.error("❌ No se pudo extraer número de orden. No se puede subir a Google Sheets.")
        st.caption("Revisa que el PDF sea una orden de compra válida con número de orden visible.")
        return

    if ya_existe_en_sheet(numero_orden):
        st.error(f"🚫 La orden **{numero_orden}** ya está registrada en Google Sheets. No se permiten duplicados.")
        hash_guardado = obtener_hash_orden_en_sheet(numero_orden)
        hash_actual = calcular_hash_oc(df)
        if hash_guardado and hash_actual and hash_guardado != hash_actual:
            st.warning("⚠️ **Modificación detectada:** el contenido de este PDF es distinto al registrado (mismo número de orden). No se puede subir.")
        st.info("Si necesitas modificar algo, hazlo directamente en la hoja. No puedes volver a subir esta misma orden.")
        st.caption("📱 No se enviará a WhatsApp (la orden ya está registrada).")
        return

    # Nueva orden: subir automáticamente y enviar por WhatsApp (solo una vez por orden en esta sesión)
    auto_uploaded = st.session_state.setdefault("auto_uploaded_orders", set())
    if numero_orden not in auto_uploaded:
        st.success(f"✅ Nueva orden detectada: **{numero_orden}** — subiendo a Google Sheets y enviando al grupo WhatsApp...")
        # Generar PDF formateado para envío (y para descarga)
        try:
            pdf_bytes = exportar_orden_compra_a_pdf(df, output_path=None, logo_path=logo_path)
        except Exception as e:
            logger.exception("Error generando PDF para WhatsApp")
            pdf_bytes = None
        resultado = subir_orden(df)
        # Solo marcar como subida si Sheets respondió OK (así si falló, se puede reintentar)
        if resultado.get("success"):
            auto_uploaded.add(numero_orden)
            if pdf_bytes and WHATSAPP_OC_DISPONIBLE:
                with st.spinner("📱 Enviando PDF al grupo de WhatsApp..."):
                    proveedor = str(df["Proveedor"].iloc[0]) if "Proveedor" in df.columns else "N/A"
                    total_str = f"${df['Total'].iloc[0]:,.2f}" if "Total" in df.columns else "N/A"
                    r_wa = enviar_oc_whatsapp(
                        pdf_bytes=pdf_bytes,
                        numero_orden=numero_orden,
                        proveedor=proveedor,
                        total=total_str,
                        filename=f"Orden_Compra_{numero_orden}.pdf",
                    )
                if r_wa.get("success"):
                    st.markdown("""
                    <div style='background: linear-gradient(135deg, #059669 0%, #10B981 100%); color: white; padding: 1rem 1.25rem; 
                                border-radius: 10px; margin: 1rem 0; border-left: 6px solid #047857; font-weight: 600;'>
                        📱 <strong>Notificación enviada a WhatsApp</strong><br>
                        <span style='font-size: 0.95rem; opacity: 0.95;'>El PDF de la orden fue enviado al grupo. La encargada de ventas puede verlo en el chat.</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                else:
                    st.warning(f"⚠️ WhatsApp no enviado: {r_wa.get('error', 'Error desconocido')}")
    else:
        st.success(f"✅ Orden **{numero_orden}** ya fue subida a Google Sheets en esta sesión.")


def subir_orden(df):
    """Sube la orden de compra a Google Sheets. Retorna el dict resultado."""
    with st.spinner("💾 Subiendo a Google Sheets..."):
        resultado = subir_a_hoja(df)
        if resultado["success"]:
            st.success(f"✅ {resultado['message']}")
            st.info(f"📊 Filas agregadas: {resultado['rows_added']}")
            st.markdown("### Resumen de la orden")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Número Orden", df["Numero Orden"].iloc[0] if "Numero Orden" in df.columns else "N/A")
            with col2:
                st.metric("Proveedor", df["Proveedor"].iloc[0] if "Proveedor" in df.columns else "N/A")
            with col3:
                st.metric("Total", f"${df['Total'].iloc[0]:,.2f}" if "Total" in df.columns else "N/A")
            st.markdown("### Productos")
            productos_df = df[["Codigo Producto", "Descripcion", "Cantidad", "Unidad", "Precio", "Importe"]].copy()
            st.dataframe(productos_df, use_container_width=True)
        else:
            st.error(f"❌ Error: {resultado['message']}")
        return resultado


# ══════════════════════════════════════════════════════════
# 🔄 FLUJO PRINCIPAL (UPLOAD & PROCESS)
# ══════════════════════════════════════════════════════════

if uploaded_file:
    # Cache por file_id: no reprocesar el mismo PDF en cada rerun (más rápido)
    file_id = getattr(uploaded_file, "file_id", id(uploaded_file))
    cache = st.session_state.get("pdf_extract_cache", {})
    cache_key = file_id
    if cache_key in cache:
        df = cache[cache_key]
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        with st.spinner("🔍 Procesando PDF..."):
            df = procesar_pdf(tmp_path, debug=False)
        st.session_state.setdefault("pdf_extract_cache", {})[cache_key] = df

    if df.empty:
        st.error("❌ No se encontraron datos válidos en el archivo PDF.")
        st.info("💡 Asegúrate de que el PDF sea una Orden de Compra válida.")
    else:
        st.success("✅ Datos extraídos correctamente")
        
        # Mostrar información general
        st.markdown("### Información de la Orden")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("N° Orden", df["Numero Orden"].iloc[0] if "Numero Orden" in df.columns else "N/A")
        with col2:
            st.metric("Fecha", df["Fecha"].iloc[0] if "Fecha" in df.columns else "N/A")
        with col3:
            st.metric("Proveedor", df["Proveedor"].iloc[0][:30] + "..." if "Proveedor" in df.columns and len(str(df["Proveedor"].iloc[0])) > 30 else (df["Proveedor"].iloc[0] if "Proveedor" in df.columns else "N/A"))
        with col4:
            st.metric("Total", f"${df['Total'].iloc[0]:,.2f}" if "Total" in df.columns else "N/A")
        
        # Mostrar datos completos
        st.markdown("### Datos extraídos")
        st.dataframe(df, use_container_width=True)
        
        # Ruta del logo (para PDF y WhatsApp)
        logo_path = root_path.parent / "Logo_Solquim_Limpio.png"
        if not logo_path.exists():
            logo_path = root_path.parent.parent / "Logo_Solquim_Limpio.png"
        logo_path = str(logo_path) if logo_path.exists() else None

        # Subir a Sheets (auto) y enviar por WhatsApp
        procesar_y_subir_oc(df, logo_path=logo_path)
        
        # ─────────────────────────────────────────────────────────
        # Descargar PDF formateado (integrado)
        # ─────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### Descargar PDF formateado")
        numero_orden = df["Numero Orden"].iloc[0] if "Numero Orden" in df.columns else "OC"

        # Generar PDF una vez por orden y guardar en sesión para el botón de descarga
        if st.session_state.get("pdf_orden_numero") != numero_orden:
            try:
                with st.spinner("Generando PDF formateado..."):
                    pdf_bytes = exportar_orden_compra_a_pdf(
                        df,
                        output_path=None,
                        logo_path=logo_path,
                    )
                    st.session_state["pdf_bytes_oc"] = pdf_bytes
                    st.session_state["pdf_nombre_oc"] = (
                        f"Orden_Compra_{numero_orden}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    )
                    st.session_state["pdf_orden_numero"] = numero_orden
            except Exception as e:
                st.error(f"Error al generar el PDF: {e}")
                logger.exception("Error generando PDF")

        if st.session_state.get("pdf_bytes_oc") is not None and st.session_state.get("pdf_orden_numero") == numero_orden:
            st.download_button(
                label="⬇️ Descargar PDF formateado (SolQuim)",
                data=st.session_state["pdf_bytes_oc"],
                file_name=st.session_state["pdf_nombre_oc"],
                mime="application/pdf",
                type="primary",
                key="btn_descargar_pdf",
            )
            st.caption("PDF con logo y formato de marca listo para enviar o imprimir.")

# ══════════════════════════════════════════════════════════
# 🎨 SIDEBAR — Orden de Compra (identidad teal/ámbar)
# ══════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #0D9488 0%, #059669 100%); color: white; padding: 0.75rem; 
                border-radius: 8px; text-align: center; margin-bottom: 1rem; font-weight: 600;'>
        📋 Orden de Compra
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"**{user_name}**")
    st.caption(f"Rol: {role}")
    
    # Badge de rol (teal/ámbar, distinto a Orden de Despacho)
    if role == "ADMIN":
        st.markdown("""
        <div style='background: linear-gradient(135deg, #0F766E 0%, #D97706 100%); 
                    color: white; padding: 0.5rem; border-radius: 8px; 
                    text-align: center; font-weight: bold; margin-bottom: 1rem; font-size: 0.9rem;'>
            🔑 Administrador
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #14B8A6 0%, #F59E0B 100%); 
                    color: white; padding: 0.5rem; border-radius: 8px; 
                    text-align: center; font-weight: bold; margin-bottom: 1rem; font-size: 0.9rem;'>
            👤 Usuario
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("**ℹ️ Compras**")
    st.caption("Procesa PDFs de órdenes de compra y regístralas en Google Sheets.")
    st.markdown("---")
    
    if st.button("Cerrar sesión", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
