from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Mensaje:
    texto: str
    fecha: datetime | None
    fuente: str
    grupo: str
    autor: str
    link: str | None = None
    hash: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        self.texto = self.texto.strip()
        if not self.hash:
            self.hash = hash_texto(self.texto)


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def hash_texto(texto: str) -> str:
    return hashlib.sha256(normalizar(texto).encode("utf-8")).hexdigest()


def coincide(texto_normalizado: str, termino_normalizado: str) -> bool:
    patron = r"(?<!\w)" + re.escape(termino_normalizado) + r"(?!\w)"
    return re.search(patron, texto_normalizado) is not None
