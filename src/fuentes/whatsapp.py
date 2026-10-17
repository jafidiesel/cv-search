from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from dateutil import parser as date_parser

from src.normalizacion import Mensaje

RE_INICIO_FECHA = re.compile(r"^\W*\[?\d{1,4}[\/.-]\d{1,2}[\/.-]\d{1,4}")
RE_MENSAJE = re.compile(
    r"^\W*\[?(?P<fecha>[^\],:]+),\s*"
    r"(?P<hora>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[apAP]\.?\s?[mM]\.?)?)\]?\s*"
    r"[-–—]?\s*"
    r"(?P<autor>[^:\n]+):\s(?P<texto>.+)$"
)


def parsear_archivo(ruta: str | Path) -> list[Mensaje]:
    ruta = Path(ruta)
    contenido = ruta.read_text(encoding="utf-8", errors="replace")
    return parsear_texto(contenido, grupo=ruta.stem)


def parsear_texto(contenido: str, grupo: str) -> list[Mensaje]:
    mensajes: list[Mensaje] = []
    actual: list[str] | None = None
    actual_autor = ""
    actual_fecha: datetime | None = None

    for linea in contenido.splitlines():
        linea = linea.replace("‎", "").replace("\xa0", " ").rstrip()
        if RE_INICIO_FECHA.match(linea):
            if actual:
                mensajes.append(_construir(actual, actual_autor, actual_fecha, grupo))
            match = RE_MENSAJE.match(linea)
            if match:
                actual = [match.group("texto")]
                actual_autor = match.group("autor").strip()
                actual_fecha = _parsear_fecha(match.group("fecha"), match.group("hora"))
            else:
                actual = None
        elif actual is not None:
            actual.append(linea)

    if actual:
        mensajes.append(_construir(actual, actual_autor, actual_fecha, grupo))

    return [m for m in mensajes if m.texto]


def _construir(
    lineas: list[str], autor: str, fecha: datetime | None, grupo: str
) -> Mensaje:
    return Mensaje(
        texto="\n".join(lineas).strip(),
        fecha=fecha,
        fuente="whatsapp",
        grupo=grupo,
        autor=autor,
    )


def _parsear_fecha(fecha: str, hora: str) -> datetime | None:
    hora = re.sub(r"(?i)a\.\s*m\.", "AM", hora)
    hora = re.sub(r"(?i)p\.\s*m\.", "PM", hora)
    try:
        return date_parser.parse(f"{fecha.strip()} {hora.strip()}", dayfirst=True)
    except (ValueError, OverflowError):
        return None
