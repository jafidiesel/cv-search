from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from src.filtro import cargar_parametros, puntuar
from src.normalizacion import Mensaje


def main() -> None:
    load_dotenv()
    args = _parsear_args()

    if args.cv:
        print("aviso: --cv se ignora por ahora (Fase 1.5)", file=sys.stderr)

    params = cargar_parametros(args.parametros)
    mensajes = _recolectar(args)

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

    ruta_credenciales = os.environ.get(
        "GOOGLE_SERVICE_ACCOUNT_JSON", "data/credentials/service-account.json"
    )
    if not Path(ruta_credenciales).exists():
        sys.exit(f"No se encontró la clave de Google en {ruta_credenciales}")

    from src.almacenamiento.sheets import HojaOfertas

    hoja = HojaOfertas(args.sheet, ruta_credenciales)
    existentes = hoja.hashes_existentes()
    nuevas = [(m, r) for m, r in guardables if m.hash not in existentes]
    escritas = hoja.agregar(nuevas)
    print(f"Agregadas a la hoja: {escritas} (ya existían: {len(guardables) - len(nuevas)})")


def _recolectar(args) -> list[Mensaje]:
    mensajes: list[Mensaje] = []
    for ruta in args.whatsapp or []:
        from src.fuentes.whatsapp import parsear_archivo

        mensajes.extend(parsear_archivo(ruta))
    if args.telegram:
        faltan = [
            v
            for v in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH")
            if not os.environ.get(v)
        ]
        if faltan:
            sys.exit(f"Faltan variables de entorno: {', '.join(faltan)}")
        from src.fuentes.telegram import leer_grupos

        mensajes.extend(leer_grupos(args.telegram, limite=args.limite))
    return mensajes


def _parsear_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Buscador de ofertas laborales")
    parser.add_argument("--parametros", default="config/parametros.yaml")
    parser.add_argument("--cv", help="PDF del CV (se ignora hasta la Fase 1.5)")
    parser.add_argument(
        "--telegram", nargs="+", metavar="GRUPO", help="nombres o IDs de grupos"
    )
    parser.add_argument(
        "--whatsapp", nargs="+", metavar="ARCHIVO", help="archivos .txt exportados"
    )
    parser.add_argument("--sheet", help="URL o ID de la hoja de Google Sheets")
    parser.add_argument("--limite", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.telegram and not args.whatsapp:
        parser.error("indicá al menos una fuente: --telegram o --whatsapp")
    if not args.sheet and not args.dry_run:
        parser.error("falta --sheet (o usá --dry-run)")
    return args


if __name__ == "__main__":
    main()
