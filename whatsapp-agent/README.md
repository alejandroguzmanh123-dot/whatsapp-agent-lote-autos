# 🚗 Agente WhatsApp - Lote de Autos
### Agente de IA para Servicios y Refacciones

MVP funcional que responde mensajes de WhatsApp como un asesor humano,
usando la información del negocio del cliente para responder preguntas
sobre servicios, precios, horarios y refacciones.

---

## Arquitectura

```
Cliente escribe en WhatsApp
        ↓
  Webhook (Twilio o Meta)
        ↓
  Servidor FastAPI (Python)
        ↓
  Lee documento del cliente (PDF / Word / TXT)
        ↓
  Claude API → respuesta natural
        ↓
  Responde al cliente por WhatsApp
```

---

## Requisitos previos

- Python 3.10 o superior
- Una cuenta de [Anthropic](https://console.anthropic.com) con API key
- Una cuenta de [Twilio](https://www.twilio.com) (gratis para probar) O Meta WhatsApp Cloud API

---

## Instalación local

### 1. Clonar / descargar el proyecto

```bash
cd whatsapp-agent
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv

# En Mac/Linux:
source venv/bin/activate

# En Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

Abre `.env` y llena:
- `ANTHROPIC_API_KEY` → tu API key de Anthropic
- `NOMBRE_AGENTE` → nombre del asesor (ej: "Carlos")

### 4. Agregar el documento del cliente

Pon el archivo de información del negocio en la carpeta `docs/`.
Puede ser `.txt`, `.pdf` o `.docx`. Solo debe haber UN archivo.

Hay un archivo de ejemplo (`ejemplo_info_negocio.txt`) que puedes editar
o reemplazar con el documento real del cliente.

### 5. Correr el servidor

```bash
uvicorn main:app --reload --port 8000
```

El servidor estará en `http://localhost:8000`

---

## Opción A: Probar con Twilio Sandbox (recomendado para MVP)

**Ventaja:** No necesitas número real ni aprobación de Meta. Sirve para demostrar al cliente.

### Paso 1: Crear cuenta en Twilio
- Ve a https://www.twilio.com/try-twilio
- Crea una cuenta gratuita

### Paso 2: Activar WhatsApp Sandbox
- En el dashboard de Twilio, busca: **Messaging → Try it out → Send a WhatsApp message**
- Te dará un número de sandbox y un código para unirte (ej: "join purple-elephant")
- El cliente envía ese código al número de Twilio para activar la prueba

### Paso 3: Exponer tu servidor local con ngrok
```bash
# Instalar ngrok: https://ngrok.com/download
ngrok http 8000
```
Copia la URL que te da ngrok (ej: `https://abc123.ngrok.io`)

### Paso 4: Configurar el webhook en Twilio
- En Twilio, en el sandbox de WhatsApp
- En "When a message comes in", pon:
  ```
  https://abc123.ngrok.io/webhook/twilio
  ```
- Método: HTTP POST
- Guardar

### Paso 5: ¡Probar!
Envía un WhatsApp al número del sandbox desde tu teléfono y el agente responderá.

---

## Opción B: Meta WhatsApp Cloud API (para producción con número real)

**Úsala cuando el cliente quiera conectar su número real de WhatsApp Business.**

### Paso 1: Crear una App en Meta for Developers
- Ve a https://developers.facebook.com
- Crear nueva app → tipo "Business"
- Agregar producto "WhatsApp"

### Paso 2: Obtener credenciales
En la sección de WhatsApp de tu app:
- `Phone Number ID` → cópialo
- `Access Token` → genera uno temporal o permanente

### Paso 3: Configurar el webhook
- En Meta, ir a "Webhooks" en la configuración de WhatsApp
- URL del webhook: `https://TU-SERVIDOR.railway.app/webhook/meta`
- Verify Token: el valor que pusiste en `META_VERIFY_TOKEN` en tu `.env`
- Suscribir al evento: `messages`

### Paso 4: Migrar el número del cliente
- En Meta puedes agregar el número existente del cliente (WhatsApp Business)
- Esto requiere verificación por llamada o SMS al número

---

## Deploy en Railway (hosting gratuito)

Railway es la forma más sencilla de tener el servidor en internet de forma permanente.

### Paso 1: Subir el código a GitHub
```bash
git init
git add .
git commit -m "Agente WhatsApp MVP"
git remote add origin https://github.com/TU-USUARIO/whatsapp-agent.git
git push -u origin main
```

> **IMPORTANTE:** Asegúrate de que el archivo `.env` esté en `.gitignore`
> para no subir tus API keys a GitHub.

Crea un `.gitignore`:
```
.env
venv/
__pycache__/
*.pyc
```

### Paso 2: Crear proyecto en Railway
- Ve a https://railway.app
- "New Project" → "Deploy from GitHub repo"
- Selecciona tu repositorio

### Paso 3: Agregar variables de entorno en Railway
- En el proyecto, ir a "Variables"
- Agregar todas las variables de tu `.env`

### Paso 4: Configurar el start command
Railway detecta automáticamente Python. Crea un archivo `Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Paso 5: Obtener la URL pública
Railway te dará una URL tipo `https://tu-proyecto.up.railway.app`
Usa esa URL para configurar el webhook en Twilio o Meta.

---

## Actualizar el documento del cliente

Para cambiar la información del negocio:
1. Reemplaza el archivo en la carpeta `docs/`
2. Reinicia el servidor (Railway lo hace automático con cada deploy)

---

## Estructura del proyecto

```
whatsapp-agent/
├── main.py                    # Servidor FastAPI + webhooks
├── claude_handler.py          # Integración con Claude API
├── doc_reader.py              # Lector de documentos (PDF/DOCX/TXT)
├── requirements.txt           # Dependencias Python
├── .env.example               # Plantilla de variables de entorno
├── .env                       # Variables reales (NO subir a GitHub)
├── Procfile                   # Para Railway
└── docs/
    └── info_negocio.txt       # Documento del cliente
```

---

## Cómo funciona el agente

1. El cliente escribe un mensaje en WhatsApp
2. El webhook recibe el mensaje y lo manda al servidor
3. El servidor lee el documento del negocio y lo incluye como contexto
4. Claude recibe: el documento + historial de la conversación + el nuevo mensaje
5. Claude genera una respuesta natural y concisa (máx ~500 tokens)
6. El servidor envía la respuesta de regreso al cliente por WhatsApp

El historial de cada conversación se mantiene en memoria (se limpia si se reinicia el servidor). Para un sistema más robusto en producción se puede agregar una base de datos.

---

## Personalización

### Cambiar el tono/personalidad del agente
Edita el `SYSTEM_PROMPT` en `claude_handler.py`.

### Cambiar el nombre del agente
Cambia `NOMBRE_AGENTE` en el archivo `.env`.

### Manejar más tipos de mensajes
Actualmente solo se procesan mensajes de texto. Para agregar soporte a
imágenes o audios, modifica la función `webhook_meta` en `main.py`.

---

## Preguntas frecuentes

**¿El agente inventa información?**
No, el prompt le instruye explícitamente que solo use la información del documento.
Si no sabe algo, dice que va a consultar.

**¿Qué pasa si el documento es muy largo?**
Claude soporta documentos largos. Para documentos muy extensos (>50 páginas),
se puede implementar búsqueda semántica (RAG) en una versión posterior.

**¿Se puede usar con múltiples clientes/negocios?**
Sí, cada instancia del servidor usa un documento diferente. Para manejar
múltiples clientes se recomienda un servidor por cliente o una versión
multi-tenant más avanzada.
