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
from google_sheets_reader import (
    cargar_informacion,
    buscar_archivos_por_mensaje,
    construir_url_drive,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agente WhatsApp - Lote de Autos")


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

    documento = cargar_informacion()
    respuesta = await responder_mensaje(
        mensaje=Body,
        numero_cliente=From,
        documento=documento,
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

# Imagen de bienvenida (se envia solo la primera vez que un cliente escribe)
IMAGE_BIENVENIDA = "https://raw.githubusercontent.com/alejandroguzmanh123-dot/whatsapp-agent-lote-autos/main/whatsapp-agent/images/concesionario.jpg.jpeg"
primeros_contactos: set = set()


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

        # Cargar información del negocio desde Google Sheets (con cache)
        documento = cargar_informacion()

        respuesta = await responder_mensaje(
            mensaje=texto,
            numero_cliente=numero_cliente,
            documento=documento,
        )

        logger.info(f"[Meta] Respuesta: {respuesta}")

        # Si es el primer mensaje del cliente, enviar imagen de bienvenida primero
        if numero_cliente not in primeros_contactos:
            primeros_contactos.add(numero_cliente)
            await enviar_imagen_meta(
                numero_cliente,
                IMAGE_BIENVENIDA,
                "Bienvenido a AutoMax!"
            )

        # Enviar respuesta de texto
        await enviar_mensaje_meta(numero_cliente, respuesta)

        # Buscar archivos (imágenes/PDFs) relacionados con el mensaje y enviarlos
        archivos = buscar_archivos_por_mensaje(texto)
        for archivo in archivos:
            url = construir_url_drive(archivo["file_id"])
            if archivo["tipo"] == "pdf":
                await enviar_pdf_meta(numero_cliente, url, archivo["nombre"])
            else:
                await enviar_imagen_meta(numero_cliente, url, archivo["nombre"])

    except (KeyError, IndexError) as e:
        logger.error(f"[Meta] Error procesando mensaje: {e}")

    return {"status": "ok"}


# ---------------------------------------------
#  FUNCIONES DE ENVÍO
# ---------------------------------------------

def normalizar_numero_mexicano(numero: str) -> str:
    """
    WhatsApp Cloud API entrega numeros mexicanos moviles con un 1 extra:
      521XXXXXXXXXX -> 52XXXXXXXXXX
    Esta funcion quita el 1 redundante cuando aplica.
    """
    n = numero.lstrip("+")
    if n.startswith("521") and len(n) == 13:
        n = "52" + n[3:]
        logger.info(f"[Meta] Numero normalizado: {numero} -> {n}")
    return n


async def enviar_imagen_meta(numero: str, url: str, caption: str = ""):
    """Envia una imagen via Meta WhatsApp Cloud API usando un link externo."""
    numero = normalizar_numero_mexicano(numero)
    url_api = f"https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "image",
        "image": {"link": url, "caption": caption},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url_api, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.error(f"[Meta] Error enviando imagen: {resp.text}")
        else:
            logger.info(f"[Meta] Imagen enviada a {numero}")


async def enviar_pdf_meta(numero: str, url: str, nombre: str = "documento.pdf"):
    """Envia un PDF via Meta WhatsApp Cloud API usando un link externo."""
    numero = normalizar_numero_mexicano(numero)
    url_api = f"https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "document",
        "document": {
            "link": url,
            "filename": nombre if nombre.endswith(".pdf") else nombre + ".pdf",
        },
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url_api, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.error(f"[Meta] Error enviando PDF: {resp.text}")
        else:
            logger.info(f"[Meta] PDF enviado a {numero}")


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
    documento = cargar_informacion()
    return {
        "status": "ok",
        "agente": "Lote de Autos - Servicios y Refacciones",
        "documento_cargado": bool(documento),
    }
