"""
Lector de Google Sheets y Google Drive para el agente de WhatsApp.

Estructura:
  - Google Sheet "Informacion": columnas A (Categoría) y B (Contenido)
    → El cliente edita este sheet para cambiar precios, horarios, etc.

  - Carpeta de Google Drive (GOOGLE_DRIVE_FOLDER_ID):
    → El cliente simplemente sube imágenes y PDFs con nombres descriptivos.
    → El agente detecta qué archivo enviar según las palabras en el nombre del archivo.
    → Ejemplos de nombres: "lista-de-precios.pdf", "foto-taller.jpg", "mapa-ubicacion.png"
    → NO se necesita editar ningún sheet para los archivos.

Cache de 60 segundos para no saturar las APIs de Google.
"""

import os
import re
import json
import time
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Tipos MIME de imágenes soportados por WhatsApp
_MIME_IMAGENES = {
    "image/jpeg", "image/png", "image/webp",
    "image/gif", "image/bmp",
}

# Cache en memoria
_cache: dict = {
    "info": None,
    "archivos": None,
    "timestamp_info": 0.0,
    "timestamp_archivos": 0.0,
}
CACHE_TTL = 60  # segundos


# ─────────────────────────────────────────────
#  AUTENTICACIÓN
# ─────────────────────────────────────────────

def _get_credentials():
    """Carga las credenciales desde la variable de entorno GOOGLE_CREDENTIALS."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("Variable de entorno GOOGLE_CREDENTIALS no configurada.")
    creds_dict = json.loads(creds_json)
    return service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )


def _sheets_service():
    return build("sheets", "v4", credentials=_get_credentials(), cache_discovery=False)


def _drive_service():
    return build("drive", "v3", credentials=_get_credentials(), cache_discovery=False)


def _leer_hoja(sheet_id: str, rango: str) -> list:
    """Lee un rango de Google Sheets y retorna lista de filas."""
    service = _sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=rango)
        .execute()
    )
    return result.get("values", [])


# ─────────────────────────────────────────────
#  INFORMACIÓN DEL NEGOCIO (Google Sheets)
# ─────────────────────────────────────────────

def cargar_informacion() -> str:
    """
    Lee la hoja 'Informacion' y retorna el contenido como texto para el agente.
    El cliente puede editar este sheet directamente para actualizar precios,
    horarios o cualquier dato del negocio.
    Usa caché de 60 segundos.
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        logger.warning("GOOGLE_SHEET_ID no configurado.")
        return ""

    now = time.time()
    if _cache["info"] and (now - _cache["timestamp_info"]) < CACHE_TTL:
        logger.info("[Sheets] Usando caché de información.")
        return _cache["info"]

    try:
        rows = _leer_hoja(sheet_id, "Informacion!A:B")
        if not rows:
            return ""

        lineas = []
        for row in rows:
            if len(row) >= 2:
                lineas.append(f"{row[0]}: {row[1]}")
            elif len(row) == 1 and row[0].strip():
                lineas.append(row[0])

        texto = "\n".join(lineas)
        _cache["info"] = texto
        _cache["timestamp_info"] = now
        logger.info(f"[Sheets] Información cargada: {len(texto)} caracteres.")
        return texto

    except Exception as e:
        logger.error(f"[Sheets] Error leyendo información: {e}")
        return _cache["info"] or ""


# ─────────────────────────────────────────────
#  ARCHIVOS MULTIMEDIA (Google Drive folder)
# ─────────────────────────────────────────────

def _nombre_a_keywords(nombre: str) -> list[str]:
    """
    Convierte el nombre de un archivo en palabras clave para matching.
    Ejemplo: "lista-de-precios-2024.pdf" → ["lista", "de", "precios", "2024"]
    """
    sin_extension = re.sub(r"\.[^.]+$", "", nombre)          # quita extensión
    palabras = re.split(r"[\s\-_]+", sin_extension.lower())  # divide por guiones/espacios
    return [p for p in palabras if len(p) > 2]               # filtra palabras muy cortas


def cargar_archivos_drive() -> list:
    """
    Lista todos los archivos (imágenes y PDFs) en la carpeta de Drive configurada.
    El cliente solo necesita subir archivos a esa carpeta con nombres descriptivos.
    El agente detecta automáticamente qué archivo enviar según el mensaje del cliente.
    Usa caché de 60 segundos.
    """
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        logger.warning("GOOGLE_DRIVE_FOLDER_ID no configurado. No se enviarán archivos.")
        return []

    now = time.time()
    if _cache["archivos"] is not None and (now - _cache["timestamp_archivos"]) < CACHE_TTL:
        return _cache["archivos"]

    try:
        service = _drive_service()
        query = (
            f"'{folder_id}' in parents "
            f"and trashed=false "
            f"and (mimeType contains 'image/' or mimeType='application/pdf')"
        )
        resultado = (
            service.files()
            .list(
                q=query,
                fields="files(id, name, mimeType)",
                pageSize=50,
            )
            .execute()
        )
        archivos_raw = resultado.get("files", [])

        archivos = []
        for f in archivos_raw:
            tipo = "pdf" if f["mimeType"] == "application/pdf" else "image"
            archivos.append({
                "nombre":         f["name"],
                "tipo":           tipo,
                "file_id":        f["id"],
                "palabras_clave": _nombre_a_keywords(f["name"]),
            })

        _cache["archivos"] = archivos
        _cache["timestamp_archivos"] = now
        logger.info(f"[Drive] Archivos cargados desde carpeta: {len(archivos)}")
        return archivos

    except Exception as e:
        logger.error(f"[Drive] Error listando archivos: {e}")
        return _cache["archivos"] or []


def buscar_archivos_por_mensaje(mensaje: str) -> list:
    """
    Retorna los archivos de Drive cuyo nombre coincide con palabras del mensaje.
    Ejemplo: si el cliente pregunta por "precios" y hay un archivo "lista-de-precios.pdf",
    el agente lo enviará automáticamente.
    """
    mensaje_lower = mensaje.lower()
    coincidencias = []
    for archivo in cargar_archivos_drive():
        for palabra in archivo["palabras_clave"]:
            if palabra and palabra in mensaje_lower:
                coincidencias.append(archivo)
                break
    return coincidencias


def construir_url_drive(file_id: str) -> str:
    """Construye la URL de descarga directa de un archivo de Google Drive."""
    return f"https://drive.google.com/uc?export=download&id={file_id}"
