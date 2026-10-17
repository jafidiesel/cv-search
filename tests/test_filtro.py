from src.filtro import puntuar

PARAMS = {
    "obligatorias": {
        "puesto": ["frontend", "react developer"],
        "stack": ["javascript", "typescript", "react"],
    },
    "excluyentes": ["pasante", "pasantía", "junior"],
    "deseables": {"react": 3, "typescript": 3, "remoto": 2},
    "ubicacion": {
        "aceptar_remoto": True,
        "aceptar_hibrido": True,
        "aceptar_presencial": True,
        "ciudades": ["Montevideo", "Mendoza"],
        "descartar_presencial_fuera_de_ciudades": True,
    },
    "umbral_minimo": 3,
}


def test_pasa_con_lo_minimo():
    r = puntuar("Frontend React con experiencia", PARAMS)
    assert not r.descartada
    assert r.puntaje == 3


def test_descarta_sin_obligatoria():
    r = puntuar("Buscamos desarrollador backend Python", PARAMS)
    assert r.descartada
    assert r.motivo == "sin puesto"


def test_todas_las_obligatorias_se_cumplen():
    r = puntuar("React developer con JavaScript", PARAMS)
    assert not r.descartada


def test_excluyente_descarta():
    r = puntuar("Frontend React, pasante", PARAMS)
    assert r.descartada
    assert "excluyente" in r.motivo


def test_excluyente_con_tildes_y_mayusculas():
    r = puntuar("Frontend React PASANTÍA", PARAMS)
    assert r.descartada


def test_deseables_suman_peso():
    r = puntuar("React developer TypeScript 100% remoto", PARAMS)
    assert r.puntaje == 3 + 3 + 2


def test_deseable_no_suma_dos_veces():
    r = puntuar("React developer con React y más React", PARAMS)
    assert r.puntaje == 3


def test_umbral_descarta():
    params = dict(PARAMS, umbral_minimo=10)
    r = puntuar("Frontend React", params)
    assert r.descartada
    assert "umbral" in r.motivo


def test_presencial_en_ciudad_aceptado():
    r = puntuar("Frontend React, presencial en Montevideo", PARAMS)
    assert not r.descartada


def test_presencial_fuera_de_ciudades_descartado():
    r = puntuar("Frontend React, presencial en Buenos Aires", PARAMS)
    assert r.descartada
    assert r.motivo == "ubicación: fuera de ciudades"


def test_hibrido_fuera_de_ciudades_descartado():
    r = puntuar("Frontend React, híbrido en Córdoba", PARAMS)
    assert r.descartada


def test_sin_modalidad_se_conserva():
    r = puntuar("Frontend React", PARAMS)
    assert not r.descartada


def test_presencial_desactivado():
    params = {
        **PARAMS,
        "ubicacion": {**PARAMS["ubicacion"], "aceptar_presencial": False},
    }
    r = puntuar("Frontend React presencial en Montevideo", params)
    assert r.descartada
