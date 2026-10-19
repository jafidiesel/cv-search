from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.almacenamiento.sqlite import ESTADOS, BaseOfertas

RUTA_DB = os.environ.get("OFERTAS_DB", str(RAIZ / "data" / "ofertas.db"))
POR_PAGINA = 20

st.set_page_config(page_title="Ofertas laborales", layout="wide")

db = BaseOfertas(RUTA_DB)

titulo, boton = st.columns([4, 1])
titulo.title("Ofertas laborales")
if boton.button("Correr búsqueda", type="primary", use_container_width=True):
    with st.spinner("Leyendo fuentes y filtrando..."):
        res = subprocess.run(
            [sys.executable, "-m", "src.cli", "--telegram", "--whatsapp"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
        )
    if res.returncode == 0:
        st.success("Corrida terminada")
        st.code(res.stdout, language=None)
    else:
        st.error("La corrida falló")
        st.code(res.stderr, language=None)

contadores = db.contar_estados()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Pendientes", contadores.get("pendiente", 0))
c2.metric("Ignoradas", contadores.get("ignorado", 0))
c3.metric("Postuladas", contadores.get("postulado", 0))
c4.metric("Total", sum(contadores.values()))

ultima = db.ultima_corrida()
if ultima:
    st.caption(
        f"Última corrida: {ultima['fecha']} · "
        f"{ultima['mensajes_leidos']} mensajes · "
        f"{ultima['nuevas']} ofertas nuevas · {ultima['duracion_s']}s"
    )

f1, f2, f3, f4, f5 = st.columns([2, 1, 1, 1, 3])
estado_sel = f1.selectbox("Estado", ["Todos", *ESTADOS])
puntaje_min = f2.number_input("Puntaje mínimo", min_value=0, value=0, step=1)
fuente_sel = f3.selectbox("Fuente", ["Todas", "telegram", "whatsapp"])
pagina = f4.number_input("Página", min_value=1, value=1, step=1)
buscar = f5.text_input("Buscar en el texto")

ofertas = db.consultar(
    estado=None if estado_sel == "Todos" else estado_sel,
    fuente=None if fuente_sel == "Todas" else fuente_sel,
    puntaje_minimo=puntaje_min or None,
    texto=buscar or None,
)

total = len(ofertas)
paginas = max(1, -(-total // POR_PAGINA))
pagina = min(int(pagina), paginas)
inicio = (pagina - 1) * POR_PAGINA
pagina_ofertas = ofertas[inicio : inicio + POR_PAGINA]

st.caption(f"{total} ofertas · página {pagina} de {paginas}")


def cambiar_estado(oferta_id: int, estado: str) -> None:
    db.cambiar_estado(oferta_id, estado)
    st.rerun()


for oferta in pagina_ofertas:
    with st.container(border=True):
        contenido, acciones = st.columns([6, 4])
        with contenido:
            st.markdown(
                f"**{oferta['puntaje']} pts** · {oferta['estado']} · "
                f"{oferta['grupo']} · {oferta['fuente']} · {oferta['fecha']}"
            )
            st.write(oferta["texto"])
            detalles = []
            if oferta["coincidencias"]:
                detalles.append(f"coincidencias: {oferta['coincidencias']}")
            if oferta["autor"]:
                detalles.append(f"autor: {oferta['autor']}")
            if oferta["link"]:
                detalles.append(f"[link]({oferta['link']})")
            if detalles:
                st.caption(" · ".join(detalles))
        with acciones:
            b1, b2, b3 = st.columns(3)
            if b1.button(
                "Pendiente",
                key=f"pend-{oferta['id']}",
                disabled=oferta["estado"] == "pendiente",
            ):
                cambiar_estado(oferta["id"], "pendiente")
            if b2.button(
                "Ignorado",
                key=f"igno-{oferta['id']}",
                disabled=oferta["estado"] == "ignorado",
            ):
                cambiar_estado(oferta["id"], "ignorado")
            if b3.button(
                "Postulado",
                key=f"post-{oferta['id']}",
                disabled=oferta["estado"] == "postulado",
            ):
                cambiar_estado(oferta["id"], "postulado")

db.cerrar()
