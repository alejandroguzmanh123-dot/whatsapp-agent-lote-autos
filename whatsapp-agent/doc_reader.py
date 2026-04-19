"""
Lector de documentos del cliente

Soporta:
  - .txt  → lectura directa
  - .pdf  → extracción de texto con pdfplumber
  - .docx → extracción de texto con python-docx

El agente busca el primer archivo compatible en la carpeta /docs
y lo carga al iniciar.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

EXTENSIONES_SOPORTADAS = [".txt", ".pdf", ".docx"]


def cargar_documento(carpeta: str) -> str:
    """
    Busca y carga el primer documento compatible en la carpeta indicada.
    Devuelve el contenido como texto plano.
    """
    carpeta_path = Path(carpeta)

    if not carpeta_path.exists():
        logger.warning(f"La carpeta '{carpeta}' no existe.")
        return ""

    # Buscar archivos compatibles
    archivos = []
    for ext in EXTENSIONES_SOPORTADAS:
        archivos.extend(carpeta_path.glob(f"*{ext}"))

    if not archivos:
        logger.warning(f"No se encontró ningún documento en '{carpeta}'.")
        return ""

    # Tomar el primero encontrado
    archivo = archivos[0]
    logger.info(f"Cargando documento: {archivo.name}")

    ext = archivo.suffix.lower()

    try:
        if ext == ".txt":
            return _leer_txt(archivo)
        elif ext == ".pdf":
            return _leer_pdf(archivo)
        elif ext == ".docx":
            return _leer_docx(archivo)
    except Exception as e:
        logger.error(f"Error leyendo {archivo.name}: {e}")
        return ""

    return ""


def _leer_txt(path: Path) -> str:
    """Lee un archivo de texto plano."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
    logger.info(f"TXT cargado: {len(contenido)} caracteres")
    return contenido


def _leer_pdf(path: Path) -> str:
    """Extrae texto de un PDF usando pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber no instalado. Corre: pip install pdfplumber")
        return ""

    texto = ""
    with pdfplumber.open(path) as pdf:
        for pagina in pdf.pages:
            texto += pagina.extract_text() or ""
            texto += "\n"

    logger.info(f"PDF cargado: {len(texto)} caracteres, {len(pdf.pages)} páginas")
    return texto.strip()


def _leer_docx(path: Path) -> str:
    """Extrae texto de un archivo Word (.docx)."""
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx no instalado. Corre: pip install python-docx")
        return ""

    doc = Document(path)
    parrafos = [p.text for p in doc.paragraphs if p.text.strip()]
    texto = "\n".join(parrafos)

    logger.info(f"DOCX cargado: {len(texto)} caracteres, {len(parrafos)} párrafos")
    return texto


def recargar_documento(carpeta: str) -> str:
    """
    Recarga el documento desde disco (útil si el cliente actualiza el archivo
    sin reiniciar el servidor).
    """
    logger.info("Recargando documento...")
    return cargar_documento(carpeta)
