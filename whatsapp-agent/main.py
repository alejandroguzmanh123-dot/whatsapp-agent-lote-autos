"""
Agente de WhatsApp para Lote de Autos
MVP - Servicios y Refacciones

Compatible con:
  - Twilio (para pruebas con sandbox)
  - Meta WhatsApp Cloud API (para produccion con numero real)
"""

import os
import logging
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import PlainTextResponse
import httpx
from dotenv import load_dotenv

from claude_handler import responder_mensaje
from doc_reader import cargar_documento

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agente WhatsApp - Lote de Autos")

# Cargar el documento del cliente al iniciar el servidor
# El archivo debe estar en la carpeta /docs con cualquier nombre
DOCUMENTO_INFO = cargar_documento("docs/")


# ---------------------------------------------
#  TWILIO WEBHOOK  (para pruebas con sandbox)
# ---------------------------------------------
@app.post("/webhook/twilio")
async def webhook_twilio(
    Body: str = Form(...),
    From: str = Form(...),
):
    """
    Twilio envia los datos del mensaje como form-data.
    Responde con TwiML (XML).
    """
    logger.info(f"[Twilio] Mensaje de {From}: {Body}")

    respuesta = await responder_mensaje(
        mensaje=Body,
        numero_cliente=From,
        documento=DOCUMENTO_INFO,
    )

    logger.info(f"[Twilio] Respuesta: {respuesta}")

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Message>{respuesta}</Message>"
        "</Response>"
    )

    return Response(content=twiml, media_type="application/xml")


# ---------------------------------------------
#  META WEBHOOK  (para produccion con numero real)
# ---------------------------------------------
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "mi_token_secreto")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")


@app.get("/webhook/meta")
async def verificar_meta(request: Request):
    """
    Meta llama este endpoint GET para verificar el webhook.
    """
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        logger.info("[Meta] Webhook verificado correctamente.")
        return PlainTextResponse(params.get("hub.challenge", ""))
    return PlainTextResponse("Token invalido", status_code=403)


@app.post("/webhook/meta")
async def webhook_meta(request: Request):
    """
    Meta envia los mensajes entrantes como JSON.
    """
    data = await request.json()

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # Ignorar notificaciones que no son mensajes (ej: status updates)
        if "messages" not in value:
            return {"status": "ignored"}

        mensaje_data = value["messages"][0]
        numero_cliente = mensaje_data["from"]
        tipo = mensaje_data.get("type", "")

        # Por ahora solo procesamos mensajes de texto
        if tipo != "text":
            logger.info(f"[Meta] Tipo de mensaje ignorado: {tipo}")
            return {"status": "ignored"}

        texto = mensaje_data["text"]["body"]
        logger.info(f"[Meta] Mensaje de {numero_cliente}: {texto}")

        respuesta = await responder_mensaje(
            mensaje=texto,
            numero_cliente=numero_cliente,
            documento=DOCUMENTO_INFO,
        )

        logger.info(f"[Meta] Respuesta: {respuesta}")

        # Enviar respuesta via Meta API
        await enviar_mensaje_meta(numero_cliente, respuesta)

    except (KeyError, IndexError) as e:
        logger.error(f"[Meta] Error procesando mensaje: {e}")

    return {"status": "ok"}


def normalizar_numero_mexicano(numero: str) -> str:
    """
    WhatsApp Cloud API entrega numeros mexicanos moviles con un 1 extra:
      521XXXXXXXXXX  ->  52XXXXXXXXXX
    Esta funcion quita el 1 redundante cuando aplica.
    """
    n = numero.lstrip("+")
    if n.startswith("521") and len(n) == 13:
        n = "52" + n[3:]
        logger.info(f"[Meta] Numero normalizado: {numero} -> {n}")
    return n


async def enviar_mensaje_meta(numero: str, mensaje: str):
    """Envia un mensaje de texto via Meta WhatsApp Cloud API."""
    numero = normalizar_numero_mexicano(numero)
    url = f"https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.error(f"[Meta] Error enviando mensaje: {resp.text}")


# ---------------------------------------------
#  HEALTH CHECK
# ---------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "ok",
        "agente": "Lote de Autos - Servicios y Refacciones",
        "documento_cargado": bool(DOCUMENTO_INFO),
    }
