"""
notification_manager_oc.py

Notificaciones WhatsApp para Órdenes de Compra (WaSender API).
Al generar/subir una OC se envía el PDF formateado al grupo configurado.

Solo usa .env (no st.secrets) para evitar "No secrets found" en local.
Grupo de test por defecto: 120363417146363570@g.us
"""

import os
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

WASENDER_API_BASE = "https://www.wasenderapi.com"
GRUPO_OC_TEST_DEFAULT = "120363417146363570@g.us"


def _load_dotenv_multiple_paths():
    """Carga .env desde la raíz del proyecto (varias rutas posibles)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    base = Path(__file__).resolve().parent  # src/
    candidates = [
        base.parent / ".env",
        base.parent.parent / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    ]
    # Subir desde la carpeta del script hasta encontrar .env (máx. 5 niveles)
    folder = base
    for _ in range(5):
        folder = folder.parent
        candidates.append(folder / ".env")
        if not folder.parent or folder == folder.parent:
            break
    for path in candidates:
        if path.exists():
            load_dotenv(path)
            return


def _get_credentials() -> Dict[str, str]:
    """
    Obtiene credenciales WaSender: st.secrets (Cloud / secrets.toml) o .env (local).
    """
    # Primero intentar st.secrets (Cloud o local con secrets.toml rellenado)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets is not None and "wasender" in st.secrets:
            w = st.secrets["wasender"]
            # Convertir a dict si es AttrDict u otro mapping; luego leer api_key y grupo_oc_id
            if hasattr(w, "items"):
                w = dict(w)
            api_key = (w.get("api_key") if isinstance(w, dict) else getattr(w, "api_key", "")) or ""
            grupo_oc_id = (w.get("grupo_oc_id") if isinstance(w, dict) else getattr(w, "grupo_oc_id", "")) or GRUPO_OC_TEST_DEFAULT
            api_key = str(api_key).strip()
            grupo_oc_id = str(grupo_oc_id).strip() or GRUPO_OC_TEST_DEFAULT
            if api_key:
                return {"api_key": api_key, "grupo_oc_id": grupo_oc_id}
    except Exception:
        pass
    # Fallback: .env (local)
    _load_dotenv_multiple_paths()
    api_key = (os.getenv("WASENDER_API_KEY") or "").strip()
    grupo_oc_id = (os.getenv("GRUPO_OC_ID") or GRUPO_OC_TEST_DEFAULT).strip()
    return {"api_key": api_key, "grupo_oc_id": grupo_oc_id or GRUPO_OC_TEST_DEFAULT}


def _validar_credenciales(require_key: Optional[str] = None) -> Dict[str, str]:
    creds = _get_credentials()
    if not creds.get("api_key"):
        raise ValueError(
            "❌ Falta WASENDER_API_KEY. Crea un archivo .env en la raíz del proyecto con:\n"
            "WASENDER_API_KEY=tu_api_key\n"
            "O en producción: .streamlit/secrets.toml con [wasender] api_key = \"...\""
        )
    if require_key and not creds.get(require_key):
        raise ValueError(
            f"❌ Falta {require_key}. Configura en .streamlit/secrets.toml o .env"
        )
    return creds


def _upload_documento(pdf_bytes: bytes, api_key: str) -> Dict[str, Any]:
    """Sube el PDF al servidor WaSender y devuelve publicUrl."""
    try:
        url = f"{WASENDER_API_BASE}/api/upload"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/pdf",
        }
        logger.info(f"📤 Subiendo PDF OC ({len(pdf_bytes)} bytes)")
        response = requests.post(url, headers=headers, data=pdf_bytes, timeout=60)
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            return {
                "success": False,
                "error": data.get("message", "Upload falló"),
            }
        return {"success": True, "publicUrl": data["publicUrl"]}
    except requests.RequestException as e:
        logger.error(f"❌ Error al subir PDF: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def enviar_orden_compra_pdf(
    pdf_bytes: bytes,
    numero_orden: str,
    proveedor: str,
    total: str,
    filename: Optional[str] = None,
    destinatario: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Envía la Orden de Compra (PDF formateado) al grupo de WhatsApp.
    Por defecto usa el grupo de test: 120363417146363570@g.us

    Args:
        pdf_bytes: Contenido del PDF
        numero_orden: Número de orden
        proveedor: Nombre del proveedor
        total: Total (ej. "$1,234.56")
        filename: Nombre del archivo (opcional)
        destinatario: JID del grupo (opcional; si no se da, usa grupo_oc_id o test)

    Returns:
        {"success": bool, "message_id": str, "error": str}
    """
    try:
        creds = _validar_credenciales(require_key="api_key")
        api_key = creds["api_key"]
        destinatario = destinatario or creds.get("grupo_oc_id") or GRUPO_OC_TEST_DEFAULT

        if not filename:
            filename = f"Orden_Compra_{numero_orden}.pdf"

        caption = f"""📋 *NUEVA ORDEN DE COMPRA*

🔢 N° Orden: *{numero_orden}*
🏭 Proveedor: {proveedor}
💰 Total: {total}

⚠️ *Encargada de ventas:* Registrada en Google Sheets. PDF adjunto.

📎 Archivo: {filename}"""

        upload_result = _upload_documento(pdf_bytes, api_key)
        if not upload_result["success"]:
            return upload_result

        url = f"{WASENDER_API_BASE}/api/send-message"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": destinatario,
            "text": caption,
            "documentUrl": upload_result["publicUrl"],
            "fileName": filename,
        }

        logger.info(f"📨 Enviando OC {numero_orden} al grupo WhatsApp")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            return {
                "success": False,
                "error": data.get("message", "Envío falló"),
            }

        msg_id = data.get("data", {}).get("msgId", "unknown")
        logger.info(f"✅ OC enviada por WhatsApp. ID: {msg_id}")
        return {"success": True, "message_id": msg_id}

    except requests.RequestException as e:
        logger.error(f"❌ Error de red WhatsApp: {e}")
        return {"success": False, "error": f"Error de red: {str(e)}"}
    except Exception as e:
        logger.error(f"❌ Error enviando OC por WhatsApp: {e}")
        return {"success": False, "error": str(e)}
