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

### Secrets (Streamlit Cloud)

En la app → **Settings** → **Secrets** usa este formato. Sin esto la app no podrá usar Sheets ni WhatsApp.

```toml
# Google Sheets (cuenta de servicio)
[gcp_service_account]
type = "service_account"
project_id = "tu-proyecto"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

# WhatsApp (WaSender)
[wasender]
api_key = "tu_api_key_wasender"
grupo_oc_id = "120363417146363570@g.us"

# Opcional: contraseñas para la app
[passwords]
basic = "password_basico"
admin = "password_admin"
```

- **Google**: crea una cuenta de servicio en Google Cloud, habilita Sheets API y Drive API, descarga el JSON y copia su contenido a `[gcp_service_account]`. El Sheet debe llamarse **"OrdenesCompra (OCS)"** y estar compartido con el `client_email`.
- **WhatsApp**: API key de [WaSender](https://www.wasenderapi.com). `grupo_oc_id` es el ID del grupo de WhatsApp (p. ej. el de test).
- **passwords**: si no pones nada, la app abre sin contraseña.

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
