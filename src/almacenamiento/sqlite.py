from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from src.filtro import Resultado
from src.normalizacion import Mensaje

ESTADOS = ("pendiente", "ignorado", "postulado")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS corridas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    mensajes_leidos INTEGER NOT NULL DEFAULT 0,
    unicos INTEGER NOT NULL DEFAULT 0,
    guardadas INTEGER NOT NULL DEFAULT 0,
    nuevas INTEGER NOT NULL DEFAULT 0,
    duracion_s REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ofertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    fuente TEXT NOT NULL,
    grupo TEXT NOT NULL,
    autor TEXT NOT NULL,
    puntaje INTEGER NOT NULL,
    coincidencias TEXT NOT NULL,
    link TEXT,
    texto TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    hash TEXT NOT NULL UNIQUE,
    corrida_id INTEGER REFERENCES corridas(id),
    fecha_guardado TEXT NOT NULL
);
"""


class BaseOfertas:
    def __init__(self, ruta: str | Path = "data/ofertas.db"):
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(ruta))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(ESQUEMA)

    def cerrar(self) -> None:
        self.conn.close()

    def __enter__(self) -> BaseOfertas:
        return self

    def __exit__(self, *exc) -> None:
        self.cerrar()

    def iniciar_corrida(self) -> int:
        cur = self.conn.execute(
            "INSERT INTO corridas (fecha) VALUES (?)",
            (datetime.now().isoformat(timespec="seconds"),),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finalizar_corrida(
        self,
        corrida_id: int,
        mensajes_leidos: int,
        unicos: int,
        guardadas: int,
        nuevas: int,
        duracion_s: float,
    ) -> None:
        self.conn.execute(
            """UPDATE corridas
               SET mensajes_leidos=?, unicos=?, guardadas=?, nuevas=?, duracion_s=?
               WHERE id=?""",
            (mensajes_leidos, unicos, guardadas, nuevas, round(duracion_s, 2), corrida_id),
        )
        self.conn.commit()

    def guardar_ofertas(
        self,
        evaluados: list[tuple[Mensaje, Resultado]],
        corrida_id: int | None = None,
    ) -> int:
        ahora = datetime.now().isoformat(timespec="seconds")
        nuevas = 0
        for mensaje, resultado in evaluados:
            cur = self.conn.execute(
                """INSERT INTO ofertas
                   (fecha, fuente, grupo, autor, puntaje, coincidencias,
                    link, texto, hash, corrida_id, fecha_guardado)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(hash) DO NOTHING""",
                (
                    mensaje.fecha.isoformat(sep=" ", timespec="minutes")
                    if mensaje.fecha
                    else "",
                    mensaje.fuente,
                    mensaje.grupo,
                    mensaje.autor,
                    resultado.puntaje,
                    resultado.coincidencias_texto(),
                    mensaje.link or "",
                    mensaje.texto,
                    mensaje.hash,
                    corrida_id,
                    ahora,
                ),
            )
            nuevas += cur.rowcount
        self.conn.commit()
        return nuevas

    def consultar(
        self,
        estado: str | None = None,
        fuente: str | None = None,
        puntaje_minimo: int | None = None,
        texto: str | None = None,
    ) -> list[dict]:
        query = "SELECT * FROM ofertas WHERE 1=1"
        args: list = []
        if estado:
            query += " AND estado=?"
            args.append(estado)
        if fuente:
            query += " AND fuente=?"
            args.append(fuente)
        if puntaje_minimo is not None:
            query += " AND puntaje>=?"
            args.append(puntaje_minimo)
        if texto:
            query += " AND texto LIKE ?"
            args.append(f"%{texto}%")
        query += " ORDER BY fecha_guardado DESC, id DESC"
        return [dict(fila) for fila in self.conn.execute(query, args)]

    def cambiar_estado(self, oferta_id: int, estado: str) -> None:
        if estado not in ESTADOS:
            raise ValueError(f"Estado inválido: {estado!r}")
        self.conn.execute(
            "UPDATE ofertas SET estado=? WHERE id=?", (estado, oferta_id)
        )
        self.conn.commit()

    def contar_estados(self) -> dict[str, int]:
        filas = self.conn.execute(
            "SELECT estado, COUNT(*) AS n FROM ofertas GROUP BY estado"
        )
        return {fila["estado"]: fila["n"] for fila in filas}

    def ultima_corrida(self) -> dict | None:
        fila = self.conn.execute(
            "SELECT * FROM corridas ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(fila) if fila else None
