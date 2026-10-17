from __future__ import annotations

from dataclasses import dataclass, field

import yaml

from src.normalizacion import coincide, normalizar

REMOTOS = ("remoto", "remote", "teletrabajo", "home office")
HIBRIDOS = ("hibrido", "hybrid")
PRESENCIALES = ("presencial", "on site", "onsite")


@dataclass
class Resultado:
    puntaje: int = 0
    coincidencias: list[str] = field(default_factory=list)
    descartada: bool = False
    motivo: str = ""

    def coincidencias_texto(self) -> str:
        return ", ".join(self.coincidencias)


def cargar_parametros(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        params = yaml.safe_load(f) or {}
    params.setdefault("obligatorias", {})
    params.setdefault("excluyentes", [])
    params.setdefault("deseables", {})
    params.setdefault("ubicacion", {})
    params.setdefault("umbral_minimo", 0)
    return params


def puntuar(texto: str, params: dict) -> Resultado:
    t = normalizar(texto)

    for grupo, terminos in (params.get("obligatorias") or {}).items():
        if not any(coincide(t, normalizar(x)) for x in terminos):
            return Resultado(descartada=True, motivo=f"sin {grupo}")

    for termino in params.get("excluyentes") or []:
        if coincide(t, normalizar(termino)):
            return Resultado(descartada=True, motivo=f"excluyente: {termino}")

    motivo_ubicacion = _chequear_ubicacion(t, params.get("ubicacion") or {})
    if motivo_ubicacion:
        return Resultado(descartada=True, motivo=motivo_ubicacion)

    resultado = Resultado()
    for termino, peso in (params.get("deseables") or {}).items():
        if coincide(t, normalizar(termino)):
            resultado.puntaje += int(peso)
            resultado.coincidencias.append(f"{termino} +{int(peso)}")

    umbral = int(params.get("umbral_minimo") or 0)
    if resultado.puntaje < umbral:
        resultado.descartada = True
        resultado.motivo = f"puntaje {resultado.puntaje} < umbral {umbral}"
    return resultado


def _chequear_ubicacion(t: str, ubicacion: dict) -> str:
    es_remoto = any(coincide(t, r) for r in REMOTOS)
    es_hibrido = any(coincide(t, h) for h in HIBRIDOS)
    es_presencial = any(coincide(t, p) for p in PRESENCIALES)

    if es_remoto and not ubicacion.get("aceptar_remoto", True):
        return "ubicación: remoto no aceptado"
    if es_hibrido and not ubicacion.get("aceptar_hibrido", True):
        return "ubicación: híbrido no aceptado"
    if es_presencial and not ubicacion.get("aceptar_presencial", True):
        return "ubicación: presencial no aceptado"

    if ubicacion.get("descartar_presencial_fuera_de_ciudades") and (
        es_presencial or es_hibrido
    ):
        ciudades = ubicacion.get("ciudades") or []
        en_ciudad = any(coincide(t, normalizar(c)) for c in ciudades)
        if not en_ciudad and not es_remoto:
            return "ubicación: fuera de ciudades"
    return ""
