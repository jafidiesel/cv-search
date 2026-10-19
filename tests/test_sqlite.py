from datetime import datetime

import pytest

from src.almacenamiento.sqlite import BaseOfertas
from src.filtro import Resultado
from src.normalizacion import Mensaje


def mensaje(texto: str, fuente: str = "whatsapp") -> Mensaje:
    return Mensaje(
        texto=texto,
        fecha=datetime(2026, 3, 12, 14, 30),
        fuente=fuente,
        grupo="Empleos IT",
        autor="Ana",
        link="https://t.me/x/1" if fuente == "telegram" else None,
    )


def evaluado(texto: str, puntaje: int = 5) -> tuple[Mensaje, Resultado]:
    m = mensaje(texto)
    return m, Resultado(puntaje=puntaje, coincidencias=["react +5"])


def test_guardar_y_dedupe(tmp_path):
    db = BaseOfertas(tmp_path / "test.db")
    assert db.guardar_ofertas([evaluado("Oferta python")]) == 1
    assert db.guardar_ofertas([evaluado("Oferta python")]) == 0
    assert len(db.consultar()) == 1


def test_ofertas_separadas_por_texto(tmp_path):
    db = BaseOfertas(tmp_path / "test.db")
    db.guardar_ofertas([evaluado("Oferta python"), evaluado("Oferta node")])
    assert len(db.consultar()) == 2


def test_cambiar_estado(tmp_path):
    db = BaseOfertas(tmp_path / "test.db")
    db.guardar_ofertas([evaluado("Oferta python")])
    oferta = db.consultar()[0]
    assert oferta["estado"] == "pendiente"
    db.cambiar_estado(oferta["id"], "postulado")
    assert db.consultar()[0]["estado"] == "postulado"
    db.cambiar_estado(oferta["id"], "ignorado")
    assert db.consultar()[0]["estado"] == "ignorado"


def test_estado_invalido(tmp_path):
    db = BaseOfertas(tmp_path / "test.db")
    with pytest.raises(ValueError):
        db.cambiar_estado(1, "cualquiera")


def test_consultar_filtros(tmp_path):
    db = BaseOfertas(tmp_path / "test.db")
    db.guardar_ofertas(
        [
            evaluado("Oferta python remoto", puntaje=8),
            evaluado("Oferta node", puntaje=2),
        ]
    )
    assert len(db.consultar(estado="pendiente")) == 2
    assert len(db.consultar(puntaje_minimo=5)) == 1
    assert len(db.consultar(texto="python")) == 1
    assert len(db.consultar(texto="no-existe")) == 0
    assert len(db.consultar(fuente="whatsapp")) == 2
    assert len(db.consultar(fuente="telegram")) == 0


def test_contar_estados(tmp_path):
    db = BaseOfertas(tmp_path / "test.db")
    db.guardar_ofertas([evaluado("A"), evaluado("B"), evaluado("C")])
    ids = [o["id"] for o in db.consultar()]
    db.cambiar_estado(ids[0], "ignorado")
    db.cambiar_estado(ids[1], "postulado")
    assert db.contar_estados() == {"pendiente": 1, "ignorado": 1, "postulado": 1}


def test_corrida(tmp_path):
    db = BaseOfertas(tmp_path / "test.db")
    corrida_id = db.iniciar_corrida()
    assert db.ultima_corrida()["id"] == corrida_id
    db.finalizar_corrida(corrida_id, 10, 8, 3, 2, 1.234)
    corrida = db.ultima_corrida()
    assert corrida["mensajes_leidos"] == 10
    assert corrida["unicos"] == 8
    assert corrida["guardadas"] == 3
    assert corrida["nuevas"] == 2
    assert corrida["duracion_s"] == 1.23


def test_oferta_guarda_corrida(tmp_path):
    db = BaseOfertas(tmp_path / "test.db")
    corrida_id = db.iniciar_corrida()
    db.guardar_ofertas([evaluado("Oferta python")], corrida_id=corrida_id)
    assert db.consultar()[0]["corrida_id"] == corrida_id
