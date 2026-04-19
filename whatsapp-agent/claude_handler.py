"""
Integración con Claude API (Anthropic)

Cada mensaje del cliente:
1. Toma el documento completo del negocio como contexto
2. Mantiene historial de la conversación en memoria por número de teléfono
3. Responde de forma natural, como un asesor humano de servicios/refacciones
"""

import os
import logging
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Historial de conversaciones por número de cliente
# Formato: { "+521234567890": [ {role, content}, ... ] }
historial_conversaciones: dict[str, list[dict]] = {}

# Máximo de mensajes a recordar por conversación (para no gastar tokens de más)
MAX_HISTORIAL = 10


SYSTEM_PROMPT = """Eres un asesor de servicio y refacciones de un lote de autos.
Tu nombre es {nombre_agente}.

Tu trabajo es atender a los clientes por WhatsApp de manera amable, clara y profesional,
como lo haría un humano.

REGLAS IMPORTANTES:
- Responde SIEMPRE en español, de manera natural y conversacional.
- Sé conciso: mensajes cortos y directos, como una conversación de WhatsApp real.
- Usa el documento de información del negocio para responder preguntas sobre:
  * Servicios disponibles (cambio de aceite, alineación, frenos, etc.)
  * Precios y paquetes
  * Horarios y ubicación
  * Disponibilidad de refacciones
  * Políticas del taller/lote
- Si el cliente pregunta algo que NO está en el documento, di amablemente que
  vas a consultar con el equipo y que te dejen su nombre/contacto, o sugiere
  que llamen directamente.
- NO inventes precios ni información que no esté en el documento.
- Si el cliente quiere agendar una cita, pide: nombre, tipo de servicio,
  vehículo (marca/modelo/año) y horario de preferencia.
- Mantén un tono amigable pero profesional. Puedes usar emojis ocasionalmente 🚗🔧

INFORMACIÓN DEL NEGOCIO:
{documento}
"""


async def responder_mensaje(
    mensaje: str,
    numero_cliente: str,
    documento: str,
) -> str:
    """
    Procesa el mensaje del cliente y devuelve la respuesta del agente.

    Args:
        mensaje: Texto enviado por el cliente
        numero_cliente: Número de WhatsApp del cliente
        documento: Contenido del documento de información del negocio
    """
    nombre_agente = os.getenv("NOMBRE_AGENTE", "Carlos")

    # Obtener o crear historial para este cliente
    if numero_cliente not in historial_conversaciones:
        historial_conversaciones[numero_cliente] = []

    historial = historial_conversaciones[numero_cliente]

    # Agregar mensaje del cliente al historial
    historial.append({"role": "user", "content": mensaje})

    # Mantener solo los últimos N mensajes para no gastar tokens
    if len(historial) > MAX_HISTORIAL:
        historial = historial[-MAX_HISTORIAL:]
        historial_conversaciones[numero_cliente] = historial

    # Construir system prompt con el documento del cliente
    system = SYSTEM_PROMPT.format(
        nombre_agente=nombre_agente,
        documento=documento if documento else "No se ha cargado información del negocio aún.",
    )

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,  # Respuestas cortas para WhatsApp
            system=system,
            messages=historial,
        )

        respuesta = response.content[0].text

        # Guardar respuesta del agente en el historial
        historial.append({"role": "assistant", "content": respuesta})
        historial_conversaciones[numero_cliente] = historial

        return respuesta

    except Exception as e:
        logger.error(f"Error llamando a Claude API: {e}")
        return "Disculpa, tuve un pequeño problema técnico. ¿Puedes repetir tu mensaje? 🙏"


def limpiar_historial(numero_cliente: str):
    """Limpia el historial de conversación de un cliente (útil para reiniciar)."""
    if numero_cliente in historial_conversaciones:
        del historial_conversaciones[numero_cliente]
        logger.info(f"Historial limpiado para {numero_cliente}")
