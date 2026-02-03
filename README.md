# Orden de Compra — SolQuim

App Streamlit para procesar órdenes de compra en PDF: extrae datos, los sube a Google Sheets, genera un PDF formateado y notifica por WhatsApp.

## Qué hace

- Sube un PDF de orden de compra → extrae número, fecha, proveedor, productos y totales.
- **Subida automática** a Google Sheets si la orden no está duplicada (no se permiten duplicados).
- **Hash** para detectar si una orden ya registrada fue modificada.
- **PDF formateado** con logo SolQuim para descargar o enviar.
- **WhatsApp**: envía el PDF al grupo configurado al subir una orden nueva.

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run orden_compra_app/app/main.py
```

## Desplegar en Streamlit Cloud

1. Sube este repositorio a GitHub.
2. En [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. **Repository**: `tu-usuario/orden_compra_app`
4. **Branch**: `main` (o el que uses)
5. **Main file path**: `orden_compra_app/app/main.py`
6. **Advanced settings** → **Secrets**: pega la configuración siguiente.

### Secrets (Streamlit Cloud) — obligatorio para Google Sheets

Si ves *"No se encontraron credenciales de Google Cloud"*, tienes que configurar los Secrets en Streamlit Cloud.

1. Entra en **share.streamlit.io** → tu app → **Settings** (⚙️) → **Secrets**.
2. Pega el contenido que corresponda (Google + WhatsApp).

#### Cómo obtener las credenciales de Google

1. Ve a [Google Cloud Console](https://console.cloud.google.com/) → tu proyecto (o crea uno).
2. **APIs y servicios** → **Biblioteca** → busca **Google Sheets API** y **Google Drive API** → **Habilitar**.
3. **APIs y servicios** → **Credenciales** → **Crear credenciales** → **Cuenta de servicio**.
4. Nombre (ej. `streamlit-oc`) → **Crear y continuar** → rol **Editor** (o el que prefieras) → **Listo**.
5. En la tabla, clic en la cuenta creada → pestaña **Claves** → **Añadir clave** → **JSON** → se descarga un `.json`.
6. Abre ese JSON. Tiene `type`, `project_id`, `private_key_id`, `private_key`, `client_email`, etc.
7. En Streamlit Cloud → **Secrets**, pega en formato TOML (cambia los valores por los de tu JSON):

```toml
[gcp_service_account]
type = "service_account"
project_id = "id-de-tu-proyecto"
private_key_id = "valor de private_key_id del JSON"
private_key = "-----BEGIN PRIVATE KEY-----\nTU_CLAVE_EN_UNA_LINEA_CON_\\n_ENTRE_LINEAS\n-----END PRIVATE KEY-----\n"
client_email = "nombre@proyecto.iam.gserviceaccount.com"
client_id = "numero"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

**Importante:** En `private_key` pega la clave completa. Si el JSON tiene la clave en varias líneas, conviértela a **una sola línea** y donde había salto de línea pon `\n` (barra invertida + n). Ejemplo: `"-----BEGIN PRIVATE KEY-----\nMIIEvQIBA...\n-----END PRIVATE KEY-----\n"`.

**Compartir el Sheet:** El Google Sheet debe llamarse **"OrdenesCompra (OCS)"** (o el nombre que tengas en el código). Comparte ese documento con el **client_email** de la cuenta de servicio (ej. `xxx@tu-proyecto.iam.gserviceaccount.com`) como **Editor**.

**Alternativa (pegar JSON completo):** En Secrets puedes pegar el JSON tal cual. Crea una clave y pega el contenido del archivo descargado:

```toml
# Pega el contenido completo del JSON entre las comillas (una sola línea o varias)
gcp_service_account = """
{"type": "service_account", "project_id": "tu-proyecto", "private_key_id": "...", "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n", "client_email": "...", "client_id": "...", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "client_x509_cert_url": "..."}
"""
```

En `private_key` mantén los `\n` para los saltos de línea. Guarda y reinicia la app.

#### WhatsApp y contraseñas (opcional)

```toml
[wasender]
api_key = "tu_api_key_wasender"
grupo_oc_id = "120363417146363570@g.us"

[passwords]
basic = "password_basico"
admin = "password_admin"
```

- Sin `[passwords]` la app abre sin contraseña.
- Sin `[wasender]` la app funciona pero no enviará WhatsApp.

## Estructura

```
orden_compra_app/
├── orden_compra_app/
│   ├── app/
│   │   └── main.py
│   └── src/
│       ├── extractor_oc.py
│       ├── formatter_oc.py
│       ├── hash_oc.py
│       ├── notification_manager_oc.py
│       └── sheets_uploader_oc.py
├── .streamlit/
│   ├── config.toml
│   └── style.css
├── requirements.txt
└── README.md
```

## Licencia

Uso interno — SOLUCIONES QUIMICAS MG SRL.
