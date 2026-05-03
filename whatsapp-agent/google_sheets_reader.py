"""
Lector de información del negocio desde Google Drive.

- Lee un Google Doc con la info del negocio (el cliente solo edita el doc en el navegador)
- Lista imágenes y PDFs de la carpeta de Drive para enviarlos por WhatsApp
- Cache de 60 segundos para no sobrecargar la API
"""

import os
import re
import io
import json
import time
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_cache = {
    "info": None,
    "archivos": None,
    "timestamp_info": 0.0,
    "timestamp_archivos": 0.0,
}
CACHE_TTL = 60

logger = logging.getLogger(__name__)


def _get_credentials():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(creds_json)
    return service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )


def _nombre_a_keywords(nombre: str) -> list:
    sin_extension = re.sub(r"\.[^.]+$", "", nombre)
    palabras = re.split(r"[\s\-_]+", sin_extension.lower())
    return [p for p in palabras if len(p) > 2]


def cargar_informacion() -> str:
    """
    Exporta el primer Google Doc que encuentre en la carpeta de Drive como texto plano.
    El cliente solo abre el doc en Google Drive y edita directamente en el navegador.
    """
    now = time.time()
    if _cache["info"] and (now - _cache["timestamp_info"]) < CACHE_TTL:
        return _cache["info"]

    try:
        creds = _get_credentials()
        drive = build("drive", "v3", credentials=creds)
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

        # Buscar Google Docs en la carpeta
        query = (
            f"'{folder_id}' in parents and trashed=false "
            f"and mimeType='application/vnd.google-apps.document'"
        )
        result = drive.files().list(
            q=query,
            fields="files(id, name)",
            pageSize=5,
            orderBy="modifiedTime desc",
        ).execute()

        files = result.get("files", [])
        if not files:
            logger.warning("No se encontró Google Doc en la carpeta de Drive")
            return "No hay información del negocio disponible todavía."

        file_id = files[0]["id"]
        file_name = files[0]["name"]
        logger.info(f"Leyendo Google Doc: {file_name}")

        # Exportar como texto plano
        request = drive.files().export_media(
            fileId=file_id,
            mimeType="text/plain"
        )
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        texto = buffer.read().decode("utf-8")

        _cache["info"] = texto
        _cache["timestamp_info"] = now
        logger.info(f"Google Doc cargado: {len(texto)} caracteres")
        return texto

    except Exception as e:
        logger.error(f"Error leyendo Google Doc de Drive: {e}")
        return "No hay información del negocio disponible."


def cargar_archivos_drive() -> list:
    """
    Lista imágenes y PDFs de la carpeta de Drive.
    El cliente sube archivos con nombres descriptivos y el agente los detecta automáticamente.
    """
    now = time.time()
    if _cache["archivos"] and (now - _cache["timestamp_archivos"]) < CACHE_TTL:
        return _cache["archivos"]

    try:
        creds = _get_credentials()
        drive = build("drive", "v3", credentials=creds)
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

        query = (
            f"'{folder_id}' in parents and trashed=false "
            f"and (mimeType contains 'image/' or mimeType='application/pdf')"
        )
        result = drive.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            pageSize=50,
        ).execute()

        archivos = []
        for f in result.get("files", []):
            tipo = "pdf" if f["mimeType"] == "application/pdf" else "imagen"
            archivos.append({
                "nombre": f["name"],
                "tipo": tipo,
                "file_id": f["id"],
                "palabras_clave": _nombre_a_keywords(f["name"]),
            })

        _cache["archivos"] = archivos
        _cache["timestamp_archivos"] = now
        logger.info(f"Archivos multimedia en Drive: {len(archivos)}")
        return archivos

    except Exception as e:
        logger.error(f"Error listando archivos Drive: {e}")
        return []


def buscar_archivos_por_mensaje(mensaje: str) -> list:
    """Encuentra imágenes/PDFs cuyo nombre coincide con palabras del mensaje."""
    archivos = cargar_archivos_drive()
    palabras_mensaje = set(re.split(r"\W+", mensaje.lower()))

    encontrados = []
    for archivo in archivos:
        for kw in archivo["palabras_clave"]:
            if kw in palabras_mensaje:
                encontrados.append(archivo)
                break

    return encontrados


def construir_url_drive(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}"
