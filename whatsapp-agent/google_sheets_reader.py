"""
Lector de Google Sheets y Google Drive para el agente de WhatsApp.

Estructura:
  - Google Sheet "Informacion": columnas A (Categoria) y B (Contenido)
    -> El cliente edita este sheet para cambiar precios, horarios, etc.

  - Carpeta de Google Drive (GOOGLE_DRIVE_FOLDER_ID):
    -> El cliente simplemente sube imagenes y PDFs con nombres descriptivos.
    -> El agente detecta que archivo enviar segun las palabras en el nombre del archivo.
    -> Ejemplos: "lista-de-precios.pdf", "foto-taller.jpg", "mapa-ubicacion.png"

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

_cache = {
    "info": None,
    "archivos": None,
    "timestamp_info": 0.0,
    "timestamp_archivos": 0.0,
}
CACHE_TTL = 60


def _get_credentials():
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


def _leer_hoja(sheet_id, rango):
    service = _sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=rango)
        .execute()
    )
    return result.get("values", [])


def cargar_informacion():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        logger.warning("GOOGLE_SHEET_ID no configurado.")
        return ""

    now = time.time()
    if _cache["info"] and (now - _cache["timestamp_info"]) < CACHE_TTL:
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
        logger.info(f"[Sheets] Informacion cargada: {len(texto)} caracteres.")
        return texto
    except Exception as e:
        logger.error(f"[Sheets] Error: {e}")
        return _cache["info"] or ""


def _nombre_a_keywords(nombre):
    sin_extension = re.sub(r"\.[^.]+$", "", nombre)
    palabras = re.split(r"[\s\-_]+", sin_extension.lower())
    return [p for p in palabras if len(p) > 2]


def cargar_archivos_drive():
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        logger.warning("GOOGLE_DRIVE_FOLDER_ID no configurado.")
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
            .list(q=query, fields="files(id, name, mimeType)", pageSize=50)
            .execute()
        )
        archivos_raw = resultado.get("files", [])
        archivos = []
        for f in archivos_raw:
            tipo = "pdf" if f["mimeType"] == "application/pdf" else "image"
            archivos.append({
                "nombre": f["name"],
                "tipo": tipo,
                "file_id": f["id"],
                "palabras_clave": _nombre_a_keywords(f["name"]),
            })
        _cache["archivos"] = archivos
        _cache["timestamp_archivos"] = now
        logger.info(f"[Drive] Archivos cargados: {len(archivos)}")
        return archivos
    except Exception as e:
        logger.error(f"[Drive] Error: {e}")
        return _cache["archivos"] or []


def buscar_archivos_por_mensaje(mensaje):
    mensaje_lower = mensaje.lower()
    coincidencias = []
    for archivo in cargar_archivos_drive():
        for palabra in archivo["palabras_clave"]:
            if palabra and palabra in mensaje_lower:
                coincidencias.append(archivo)
                break
    return coincidencias


def construir_url_drive(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"
