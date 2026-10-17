from __future__ import annotations

from datetime import datetime

from src.filtro import Resultado
from src.normalizacion import Mensaje

COLUMNAS = [
    "fecha",
    "fuente",
    "grupo",
    "autor",
    "puntaje",
    "coincidencias",
    "link",
    "texto",
    "estado",
    "hash",
]


class HojaOfertas:
    def __init__(self, url_o_id: str, ruta_credenciales: str):
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credenciales = Credentials.from_service_account_file(
            ruta_credenciales, scopes=scopes
        )
        gc = gspread.authorize(credenciales)
        self.ws = gc.open_by_key(_extraer_id(url_o_id)).sheet1

    def hashes_existentes(self) -> set[str]:
        valores = self.ws.col_values(len(COLUMNAS))
        return set(v for v in valores[1:] if v)

    def agregar(self, filas: list[tuple[Mensaje, Resultado]]) -> int:
        if not self.ws.get_all_values():
            self.ws.append_row(COLUMNAS, value_input_option="RAW")
        filas_nuevas = [_a_fila(m, r) for m, r in filas]
        if filas_nuevas:
            self.ws.append_rows(filas_nuevas, value_input_option="RAW")
        return len(filas_nuevas)


def _a_fila(mensaje: Mensaje, resultado: Resultado) -> list[str]:
    fecha = (
        mensaje.fecha.strftime("%Y-%m-%d %H:%M")
        if isinstance(mensaje.fecha, datetime)
        else ""
    )
    return [
        fecha,
        mensaje.fuente,
        mensaje.grupo,
        mensaje.autor,
        str(resultado.puntaje),
        resultado.coincidencias_texto(),
        mensaje.link or "",
        mensaje.texto,
        "pendiente",
        mensaje.hash,
    ]


def _extraer_id(url_o_id: str) -> str:
    if "/d/" in url_o_id:
        return url_o_id.split("/d/")[1].split("/")[0]
    return url_o_id
