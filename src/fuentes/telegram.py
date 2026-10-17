from __future__ import annotations

import os
from datetime import datetime

from src.normalizacion import Mensaje


def leer_grupos(grupos: list[str], limite: int = 200) -> list[Mensaje]:
    import asyncio

    return asyncio.run(_leer(grupos, limite))


async def _leer(grupos: list[str], limite: int) -> list[Mensaje]:
    from telethon import TelegramClient

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    sesion = os.environ.get("TELEGRAM_SESSION", "data/telegram")

    os.makedirs(os.path.dirname(sesion) or ".", exist_ok=True)

    mensajes: list[Mensaje] = []
    async with TelegramClient(sesion, api_id, api_hash) as cliente:
        for nombre in grupos:
            entidad = await _buscar_entidad(cliente, nombre)
            async for msg in cliente.iter_messages(entidad, limit=limite):
                if not msg.text:
                    continue
                mensajes.append(
                    Mensaje(
                        texto=msg.text,
                        fecha=msg.date.astimezone().replace(tzinfo=None)
                        if msg.date
                        else None,
                        fuente="telegram",
                        grupo=getattr(entidad, "title", None) or nombre,
                        autor=_autor(msg),
                        link=_link(entidad, msg.id),
                    )
                )
    return mensajes


async def _buscar_entidad(cliente, nombre: str):
    if nombre.lstrip("-").isdigit():
        return await cliente.get_entity(int(nombre))
    try:
        return await cliente.get_entity(nombre)
    except (ValueError, TypeError):
        pass
    async for dialog in cliente.iter_dialogs():
        if dialog.name and dialog.name.casefold() == nombre.casefold():
            return dialog.entity
    raise SystemExit(f"No se encontró el grupo de Telegram {nombre!r}")


def _autor(msg) -> str:
    sender = msg.sender
    if sender is None:
        return ""
    partes = [getattr(sender, "first_name", None), getattr(sender, "last_name", None)]
    nombre = " ".join(p for p in partes if p)
    return nombre or getattr(sender, "username", None) or ""


def _link(entidad, msg_id: int) -> str | None:
    username = getattr(entidad, "username", None)
    if username:
        return f"https://t.me/{username}/{msg_id}"
    chat_id = str(getattr(entidad, "id", ""))
    if chat_id.startswith("-100"):
        return f"https://t.me/c/{chat_id[4:]}/{msg_id}"
    return None
