from src.fuentes.whatsapp import parsear_texto

ANDROID = """\
12/3/2024, 14:30 - Los mensajes y llamadas están cifrados de extremo a extremo
12/3/2024, 14:31 - Ana: Buscamos frontend react, remoto
12/3/2024, 14:32 - Ana: Enviar CV a rrhh@empresa.com
con experiencia en typescript
12/3/2024, 14:33 - Pedro se unió al grupo
"""

IOS = """\
[31/12/23, 9:15:20 p. m.] Carlos: Oferta frontend angular
[31/12/23, 9:16:00 p. m.] +5491155555555: Interesado
"""


def test_parsea_mensajes_android():
    mensajes = parsear_texto(ANDROID, "Empleos IT")
    assert len(mensajes) == 2
    assert mensajes[0].autor == "Ana"
    assert mensajes[0].fecha.year == 2024
    assert mensajes[0].fecha.month == 3
    assert mensajes[0].fuente == "whatsapp"
    assert mensajes[0].grupo == "Empleos IT"


def test_multilinea_se_unifica():
    mensajes = parsear_texto(ANDROID, "Empleos IT")
    assert "typescript" in mensajes[1].texto
    assert mensajes[1].texto.count("\n") == 1


def test_mensajes_de_sistema_se_ignoran():
    mensajes = parsear_texto(ANDROID, "Empleos IT")
    textos = " ".join(m.texto for m in mensajes)
    assert "se unió" not in textos
    assert "cifrado" not in textos


def test_parsea_mensajes_ios():
    mensajes = parsear_texto(IOS, "Dev Jobs")
    assert len(mensajes) == 2
    assert mensajes[0].autor == "Carlos"
    assert mensajes[0].fecha.hour == 21
    assert mensajes[1].autor == "+5491155555555"


def test_archivo_vacio():
    assert parsear_texto("", "x") == []
