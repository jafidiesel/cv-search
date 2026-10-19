from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.filtro import cargar_parametros, puntuar
from src.normalizacion import Mensaje

DIR_CHATS = Path("data/chats")
DIR_PROCESADOS = DIR_CHATS / "processed"
ARCHIVO_GRUPOS = Path("data/groups/data.txt")


def main() -> None:
    load_dotenv()
    args = _parsear_args()

    if args.cv:
        print("aviso: --cv se ignora por ahora (Fase 1.5)", file=sys.stderr)

    params = cargar_parametros(args.parametros)
    mensajes, chats = _recolectar(args)

    if not mensajes:
        print("No se leyó ningún mensaje.")
        return

    vistos: set[str] = set()
    unicos: list[Mensaje] = []
    for m in mensajes:
        if m.hash not in vistos:
            vistos.add(m.hash)
            unicos.append(m)

    evaluados = [(m, puntuar(m.texto, params)) for m in unicos]
    guardables = [(m, r) for m, r in evaluados if not r.descartada]

    motivos = Counter(r.motivo for _, r in evaluados if r.descartada)
    print(f"Leídos: {len(mensajes)}  únicos: {len(unicos)}")
    for motivo, cantidad in motivos.most_common():
        print(f"  descartados por {motivo}: {cantidad}")
    print(f"Pasan el filtro: {len(guardables)}")

    if args.dry_run:
        for m, r in guardables[:20]:
            print(f"  [{r.puntaje}] {m.grupo}: {m.texto[:70]}")
        return

    from src.almacenamiento.sqlite import BaseOfertas

    ruta_db = os.environ.get("OFERTAS_DB", "data/ofertas.db")
    db = BaseOfertas(ruta_db)
    corrida_id = db.iniciar_corrida()
    t0 = time.monotonic()
    nuevas_bd = db.guardar_ofertas(guardables, corrida_id=corrida_id)
    print(
        f"Agregadas a la BD: {nuevas_bd} "
        f"(ya existían: {len(guardables) - nuevas_bd})"
    )

    sheet_url = os.environ.get("GOOGLE_SHEET_URL", "")
    if sheet_url:
        ruta_credenciales = os.environ.get(
            "GOOGLE_SERVICE_ACCOUNT_JSON", "data/credentials/service-account.json"
        )
        if not Path(ruta_credenciales).exists():
            sys.exit(f"No se encontró la clave de Google en {ruta_credenciales}")
        from src.almacenamiento.sheets import HojaOfertas

        hoja = HojaOfertas(sheet_url, ruta_credenciales)
        existentes = hoja.hashes_existentes()
        nuevas_hoja = [(m, r) for m, r in guardables if m.hash not in existentes]
        escritas = hoja.agregar(nuevas_hoja)
        print(
            f"Agregadas a la hoja: {escritas} "
            f"(ya existían: {len(guardables) - len(nuevas_hoja)})"
        )

    db.finalizar_corrida(
        corrida_id,
        mensajes_leidos=len(mensajes),
        unicos=len(unicos),
        guardadas=len(guardables),
        nuevas=nuevas_bd,
        duracion_s=time.monotonic() - t0,
    )
    db.cerrar()

    for ruta in chats:
        destino = _archivar(ruta)
        print(f"Archivado: {destino}")


def _archivar(ruta: Path) -> Path:
    DIR_PROCESADOS.mkdir(parents=True, exist_ok=True)
    destino = DIR_PROCESADOS / ruta.name
    if destino.exists():
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        destino = DIR_PROCESADOS / f"{ruta.stem}-{marca}{ruta.suffix}"
    shutil.move(str(ruta), str(destino))
    return destino


def _recolectar(args) -> tuple[list[Mensaje], list[Path]]:
    mensajes: list[Mensaje] = []
    chats: list[Path] = []
    if args.whatsapp is not None:
        from src.fuentes.whatsapp import parsear_archivo

        rutas = [Path(r) for r in args.whatsapp] or sorted(DIR_CHATS.glob("*.txt"))
        if not rutas:
            print(f"Aviso: no hay .txt en {DIR_CHATS}/", file=sys.stderr)
        for ruta in rutas:
            mensajes.extend(parsear_archivo(ruta))
            chats.append(ruta)
    if args.telegram is not None:
        faltan = [
            v
            for v in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH")
            if not os.environ.get(v)
        ]
        if faltan:
            sys.exit(f"Faltan variables de entorno: {', '.join(faltan)}")
        from src.fuentes.telegram import leer_grupos

        grupos = args.telegram or _leer_grupos_archivo()
        mensajes.extend(leer_grupos(grupos, limite=args.limite))
    return mensajes, chats


def _leer_grupos_archivo() -> list[str]:
    if not ARCHIVO_GRUPOS.exists():
        sys.exit(
            f"No existe {ARCHIVO_GRUPOS}. Crealo con un nombre de grupo por línea."
        )
    grupos = [
        linea.strip()
        for linea in ARCHIVO_GRUPOS.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    ]
    if not grupos:
        sys.exit(f"{ARCHIVO_GRUPOS} no tiene ningún grupo (uno por línea).")
    return grupos


def _parsear_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Buscador de ofertas laborales")
    parser.add_argument("--parametros", default="config/parametros.yaml")
    parser.add_argument("--cv", help="PDF del CV (se ignora hasta la Fase 1.5)")
    parser.add_argument(
        "--telegram",
        nargs="*",
        metavar="GRUPO",
        help="nombres o IDs; sin argumentos usa data/groups/data.txt",
    )
    parser.add_argument(
        "--whatsapp",
        nargs="*",
        metavar="ARCHIVO",
        help="archivos .txt; sin argumentos usa todos los de data/chats/",
    )
    parser.add_argument("--limite", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.telegram is None and args.whatsapp is None:
        parser.error("indicá al menos una fuente: --telegram o --whatsapp")
    if not Path(args.parametros).exists():
        parser.error(
            f"No existe {args.parametros}. Copiá el ejemplo: "
            "cp config/parametros.example.yaml config/parametros.yaml"
        )
    return args


if __name__ == "__main__":
    main()
