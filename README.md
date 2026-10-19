# Buscador de ofertas laborales

Herramienta personal que lee ofertas de trabajo desde grupos de **Telegram** y chats exportados de **WhatsApp**, las filtra y puntúa según parámetros definidos por el usuario, y guarda los resultados en **Google Sheets** (V1) o en una **base de datos SQLite con dashboard** (V2).

> **Estado:** en planificación. Este documento define el alcance, las decisiones de diseño y la hoja de ruta.

---

## Objetivo

Recibo muchas ofertas en grupos de Telegram y WhatsApp y no tengo tiempo de revisarlas una por una. Esta herramienta lo hace por mí: lee los mensajes, descarta lo que no sirve y me deja una lista ordenada por coincidencia con lo que busco.

## Decisiones de diseño

| Tema | Decisión |
|---|---|
| Puntuación | **Solo por parámetros** (reglas y palabras clave). Sin IA. |
| Telegram | Telethon, leyendo los grupos de los que ya soy miembro. |
| WhatsApp | Archivos `.txt` exportados manualmente. Sin automatizar WhatsApp Web. |
| LinkedIn | **Descartado.** |
| Base de datos (V2) | SQLite. |
| Dashboard (V2) | Streamlit. |
| Hoja de cálculo (V1) | **Google Sheets online** (service account). El Excel local quedó descartado como salida; se puede exportar a `.xlsx` solo como backup. |
| Hardware objetivo | PC para desarrollo y Raspberry Pi 3B+ (Debian 13, 64 bits, sin escritorio, datos en USB) para producción. |
| Ejecución | On-demand: sin servicios permanentes ni tareas programadas. |

## Arquitectura

```
Fuentes  →  Normalización  →  Deduplicación  →  Filtro y puntuación  →  Almacenamiento
(Telegram,   (texto, fecha,    (hash del          (reglas por             (Google Sheets
 WhatsApp)    origen, link)     contenido)         parámetros)             en V1, SQLite en V2)
```

La V1 se construye como un **núcleo reutilizable**. La V2 reutiliza esos mismos módulos: solo cambia la capa de almacenamiento y se agrega la interfaz.

## Estructura del repositorio (propuesta)

```
buscador-ofertas/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── config/
│   └── parametros.example.yaml
├── src/
│   ├── fuentes/
│   │   ├── telegram.py        # lectura con Telethon
│   │   └── whatsapp.py        # parser de .txt exportados
│   ├── normalizacion.py       # formato común de mensaje
│   ├── filtro.py              # reglas y puntuación
│   ├── cv.py                  # PDF → texto → palabras clave sugeridas
│   ├── almacenamiento/
│   │   ├── sheets.py          # Google Sheets (V1)
│   │   └── sqlite.py          # V2
│   └── cli.py                 # punto de entrada V1
├── dashboard/                 # V2 (Streamlit)
│   └── app.py
├── data/                      # ignorado por git
│   ├── chats/                 # .txt de WhatsApp
│   ├── credentials/
│   │   └── service-account.json   # clave de Google, ignorada por git
│   └── ofertas.db
└── tests/
```

---

## V1: script de línea de comandos

### Entradas
- **CV en PDF**: se convierte a texto una vez y se usa para sugerir palabras clave.
- **Archivo de parámetros** (YAML) con las reglas del filtro.
- **Fuentes**: grupos de Telegram (por nombre o ID) y/o archivos `.txt` de WhatsApp.
- **Google Sheets**: hoja destino, definida por `GOOGLE_SHEET_URL` en el `.env`.

### Proceso
1. Leer mensajes de cada fuente.
2. Normalizar a un formato común: texto, fecha, origen, autor, link.
3. Deduplicar por hash del texto.
4. Aplicar filtro y calcular puntaje.
5. Escribir en la hoja de Google Sheets sin repetir filas ya existentes.

### Ejemplo de parámetros

```yaml
# config/parametros.yaml
obligatorias:            # si falta alguna, se descarta
  puesto: [desarrollador, developer, dev, programador]

excluyentes:             # si aparece alguna, se descarta
  - pasante
  - pasantía
  - presencial

deseables:               # suman puntos según el peso
  python: 3
  remoto: 2
  sql: 1

ubicacion:
  aceptar_remoto: true
  ciudades: [Montevideo]

seniority: [semi senior, senior]
idiomas: [español, inglés]
sueldo_minimo: null      # opcional

umbral_minimo: 3         # puntaje mínimo para guardar la oferta
```

### Reglas de matching
- Se ignoran tildes y mayúsculas.
- Cada término admite variantes (`desarrollador`, `developer`, `dev`).
- **Obligatorias:** todas deben cumplirse.
- **Excluyentes:** si aparece una, se descarta o se penaliza.
- **Deseables:** suman su peso al puntaje.

### Columnas de la hoja

| Columna | Descripción |
|---|---|
| fecha | Fecha del mensaje |
| fuente | Telegram o WhatsApp, y nombre del grupo |
| puesto, empresa | Extraídos del texto cuando es posible |
| ubicación, modalidad, sueldo | Extraídos del texto cuando es posible |
| puntaje | Resultado de la puntuación |
| coincidencias | Palabras que hicieron match |
| contacto / link | Dato para postular |
| texto | Mensaje original completo |
| estado | pendiente / postulé / descartada |

### Telegram
1. Crear credenciales en <https://my.telegram.org> (`api_id` y `api_hash`).
2. Guardarlas en `.env` (nunca en el repo).
3. La primera ejecución pide el código de verificación y genera un **archivo de sesión**, que da acceso a la cuenta y debe protegerse.
4. Listar los grupos en `data/groups/data.txt`, uno por línea (las líneas con `#` se ignoran). `--telegram` sin argumentos lee ese archivo; también acepta nombres o IDs directamente en el comando.

### WhatsApp
Exportar cada grupo desde la app (**Exportar chat → Sin multimedia**) y dejar el `.txt` en `data/chats/`. El flag `--whatsapp` sin argumentos procesa todos los `.txt` de esa carpeta; después de escribir correctamente en la hoja, los archivos se mueven a `data/chats/processed/`. El parser contempla:
- Formatos de fecha distintos según idioma y sistema del teléfono.
- Mensajes de varias líneas.
- Mensajes de sistema (altas, bajas, cambios de grupo) que se ignoran.

### Google Sheets
1. Crear un proyecto en <https://console.cloud.google.com> y habilitar la **Google Sheets API** (y la **Drive API** si se quiere buscar o crear hojas).
2. Crear una **service account** y descargar su clave JSON.
3. Compartir la hoja destino con el email de la service account (como editor).
4. Guardar el JSON en `data/credentials/service-account.json` y la ruta en `.env`. La clave equivale a acceso a la cuenta: no subirla al repo.
5. Poner la URL (o ID) de la hoja en `GOOGLE_SHEET_URL` dentro del `.env`.
6. El script escribe en esa hoja, sin repetir filas ya existentes (dedupe por hash del texto).

---

## V2: dashboard con base de datos

### Stack
SQLite + Streamlit, reutilizando los módulos de la V1.

### Tablas

| Tabla | Contenido |
|---|---|
| `perfil` | CV (archivo y texto) y fecha de carga |
| `parametros` | Reglas del filtro, editables desde el dashboard |
| `corridas` | Fecha, fuentes usadas, mensajes leídos, ofertas encontradas, duración |
| `ofertas` | Campos extraídos, puntaje, coincidencias, fuente, id de corrida y estado |
| `fuentes_estado` | Última fecha leída por fuente, para procesar solo lo nuevo |

### Pantallas
1. **Correr búsqueda:** botón on-demand, selección de fuentes y subida de `.txt` de WhatsApp.
2. **Resultados:** tabla con filtros por puntaje, fuente, fecha y estado. Permite cambiar el estado de cada oferta.
3. **Historial de corridas:** qué se corrió, cuándo y qué devolvió.
4. **Perfil y parámetros:** subir o cambiar el CV y editar palabras clave y pesos.
5. **Backup:** exportación a `.xlsx`, manual o automática al terminar cada corrida.

### Notas de implementación
- Las búsquedas largas se lanzan en un **proceso aparte** para que la interfaz no se congele.
- Todas las corridas y resultados quedan registrados en la base de datos.
- En V2 la fuente de verdad es SQLite; la exportación a `.xlsx` es solo un backup. Todo se consulta desde el dashboard.

---

## Requisitos

- Python 3.10 o superior.
- Dependencias previstas:
  - V1: `telethon`, `pyyaml`, `pypdf`, `gspread`, `google-auth`, `python-dotenv`.
  - V2: `streamlit`.

## Instalación (cuando exista código)

```bash
git clone <url-del-repo>
cd buscador-ofertas
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # completar credenciales de Telegram, JSON de Google y GOOGLE_SHEET_URL
mkdir -p data/credentials
cp /ruta/a/service-account.json data/credentials/   # clave de la service account
cp config/parametros.example.yaml config/parametros.yaml
```

## Uso previsto (V1)

Los parámetros salen de `config/parametros.yaml` y la hoja de `GOOGLE_SHEET_URL` en el `.env`; no hay que pasarlos por comando.

```bash
python -m src.cli \
  --cv data/mi_cv.pdf \
  --telegram \
  --whatsapp
```

- `--telegram` sin argumentos lee los grupos de `data/groups/data.txt` (uno por línea).
- `--whatsapp` sin argumentos procesa todos los `.txt` de `data/chats/` y los archiva en `data/chats/processed/` al terminar.
- Para probar sin escribir en la hoja: `--dry-run`.

## Despliegue en Raspberry Pi

**Hardware y sistema objetivo:** Raspberry Pi 3B+ (1 GB de RAM) con Raspberry Pi OS basado en Debian 13, de 64 bits y sin escritorio. Todo el proyecto (código, entorno virtual, base de datos, sesión de Telegram y chats) vive en un **USB**. Todo corre **on-demand**: no hay servicios permanentes ni tareas programadas.

La RAM es el límite real, no la CPU. Sin IA, lo único pesado es Streamlit (unos 150 a 300 MB), y al correr solo cuando se lo necesita queda margen de sobra.

### Preparación
- Instalar `python3-venv` y crear un entorno virtual dentro del USB. Debian 13 bloquea `pip` fuera de un venv.
- Debian 13 trae Python 3.13. Hay que **probar primero la instalación de Streamlit** (`pyarrow`, `pandas`) antes de escribir la V2. Con 64 bits suele haber paquetes precompilados, pero se verifica.
- Montar el USB por **UUID** en `/etc/fstab` con la opción `nofail`, para que la Pi arranque aunque el USB no esté.
- Mantener un swap pequeño o zram como colchón de memoria.

### Modo on-demand
- **V1:** se ejecuta el comando por SSH, procesa y termina. No queda nada corriendo.
- **V2:** el dashboard se inicia cuando se necesita y se apaga al terminar.
  ```bash
  systemctl start buscador-dashboard   # o: streamlit run dashboard/app.py
  systemctl stop buscador-dashboard
  ```
  Se deja el servicio **sin habilitar** al arranque, para que no consuma RAM en reposo.
- Con corridas on-demand, la tabla `fuentes_estado` (última fecha leída por fuente) es clave para procesar solo lo nuevo.
- Las búsquedas siguen lanzándose en un proceso aparte para que la interfaz no se congele.

### Almacenamiento en USB
- Al escribir en USB y no en la SD, el desgaste de la SD deja de ser un problema.
- Un USB también puede fallar o corromperse por cortes de luz. Conviene **apagar la Pi con `sudo shutdown`** y mantener backups (una exportación a `.xlsx` y una copia del `.db`) en otro lado.
- El login inicial de Telegram se hace una sola vez por SSH. El `.session` queda en el USB y hay que protegerlo.

### Acceso al dashboard
- Desde la red local: `http://ip-de-la-raspberry:8501`.
- Desde afuera: **Tailscale** o VPN. No abrir el puerto 8501 a internet.

### Plan B
Si Streamlit resultara demasiado pesado o difícil de instalar en la Pi, el dashboard se reemplaza por una interfaz más liviana (FastAPI + HTMX o Flask). Como la lógica está en el núcleo de la V1, el cambio solo afecta la capa de interfaz.

## Seguridad y privacidad

Agregar al `.gitignore`:

```
.env
*.session
data/
config/parametros.yaml
```

- El archivo `.session` de Telegram equivale a una sesión iniciada de la cuenta.
- La clave JSON de la service account da acceso a Google Sheets/Drive: vive en `data/credentials/` (cubierto por `data/` en el `.gitignore`) y nunca se sube al repo.
- Los chats de WhatsApp y el CV contienen datos personales y no deben subirse al repo.

## Hoja de ruta

- [ ] **Fase 0:** estructura del repo, configuración y definición de parámetros.
- [ ] **Fase 1 (V1):** lectura de Telegram, parser de WhatsApp, filtro por reglas y salida a Google Sheets.
- [ ] **Fase 1.5:** sugerencia de palabras clave a partir del CV.
- [ ] **Fase 2 (V2):** esquema SQLite, migración de la lógica de guardado y registro de corridas.
- [ ] **Fase 3 (V2):** dashboard Streamlit con las cinco pantallas.
- [ ] **Fase 4:** despliegue en Raspberry Pi 3B+ (USB, servicio systemd on-demand y acceso remoto).

## Fuera de alcance

- LinkedIn en cualquiera de sus formas.
- Puntuación o extracción con IA.
- Automatización de WhatsApp Web.

## Licencia

Proyecto de uso personal. Definir licencia si se decide publicar.
