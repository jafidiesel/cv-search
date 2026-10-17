from datetime import datetime

from src.normalizacion import Mensaje, coincide, hash_texto, normalizar


def test_normalizar_quita_tildes_y_mayusculas():
    assert normalizar("Desarrollador Réact") == "desarrollador react"


def test_normalizar_colapsa_espacios():
    assert normalizar("  hola   \n mundo ") == "hola mundo"


def test_hash_ignora_tildes_y_mayusculas():
    assert hash_texto("Python Remoto") == hash_texto("PYTHON remoto")
    assert hash_texto("Python Remoto") == hash_texto("  python   remoto ")


def test_hash_distinto_para_textos_distintos():
    assert hash_texto("oferta python") != hash_texto("oferta node")


def test_coincide_por_palabra_completa():
    t = normalizar("desarrollador javascript")
    assert coincide(t, "javascript")
    assert not coincide(t, "java")
    assert not coincide(t, "script")


def test_coincide_ignora_tildes():
    assert coincide(normalizar("estamos buscando un desarrollador"), "desarrollador")


def test_mensaje_calcula_hash():
    m = Mensaje(
        texto="  Oferta Python  ",
        fecha=datetime(2026, 1, 1),
        fuente="whatsapp",
        grupo="Empleos",
        autor="Ana",
    )
    assert m.texto == "Oferta Python"
    assert m.hash == hash_texto("Oferta Python")
