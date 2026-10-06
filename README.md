# BACKEND-ARGUILA-

API de ARQUILA, una aplicación para organizar proyectos de arquitectura. Es una de las tres partes del proyecto:

```text
ARQUILA
├── FRONTEND-ARQUILA        Interfaz (React)
├── BACKEND-ARGUILA-        Este repositorio
└── BASE-DE-DATOS-ARQUILA   Migraciones y datos de ejemplo (PostgreSQL)
```

## Tecnología

Python 3.12 y FastAPI, con SQLAlchemy y psycopg sobre PostgreSQL, Argon2 para las contraseñas y pytest para las pruebas. Ruff para el formato y las reglas de estilo.

## Requisitos

- Python 3.12 con `pip`.
- PostgreSQL 16 o superior.
- El repositorio `BASE-DE-DATOS-ARQUILA` clonado junto a este:

  ```text
  carpeta/
  ├── BACKEND-ARGUILA-/
  └── BASE-DE-DATOS-ARQUILA/
  ```

## Instalación

En Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

En Linux o macOS cambia la activación: `source .venv/bin/activate`.

## Variables de entorno

Copiar `.env.example` a `.env` y completarlo. El archivo `.env` no se sube al repositorio.

| Variable | Uso | Por defecto |
|---|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL. Obligatoria. | — |
| `DATABASE_DIR` | Carpeta de `BASE-DE-DATOS-ARQUILA`. | `../BASE-DE-DATOS-ARQUILA` |
| `API_PORT` | Puerto de la API. | `8000` |
| `UPLOAD_DIR` | Carpeta de los archivos subidos. | `uploads` |
| `COOKIE_SECURE` | `1` para enviar la cookie de sesión solo por HTTPS. | `0` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` o `ERROR`. | `INFO` |
| `APP_URL` | Dirección de la interfaz; se usa en el enlace de recuperación de contraseña y como origen permitido. | `http://localhost:5173` |
| `CORS_ORIGINS` | Orígenes permitidos, separados por comas. | `APP_URL` |
| `OLLAMA_URL`, `OLLAMA_MODEL` | Modelo local del asistente. | `http://127.0.0.1:11434`, primer modelo instalado |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Correo de recuperación de contraseña. Sin `SMTP_HOST`, el mensaje se muestra en la terminal. | — |

## Conexión con la base de datos

1. Crear una base vacía:

   ```bash
   psql -U postgres -c "CREATE DATABASE arquila;"
   ```

2. Poner la conexión en `DATABASE_URL`, por ejemplo `postgresql+psycopg://postgres:CLAVE@localhost:5432/arquila`.

3. Crear las tablas con las migraciones de `BASE-DE-DATOS-ARQUILA`:

   ```bash
   python -m app.migrate          # solo el esquema
   python -m app.migrate --seed   # esquema y datos de ejemplo
   ```

Las migraciones (SQL) viven en `BASE-DE-DATOS-ARQUILA`; los modelos de SQLAlchemy que usa el código están en `app/models.py`.

## Iniciar el servidor

```bash
python -m app.dev
```

Lee `.env`, aplica las migraciones pendientes y arranca la API en `http://127.0.0.1:8000`.

- `http://localhost:8000/docs`: documentación interactiva con todas las operaciones.
- `http://localhost:8000/health`: responde `{"status": "ok"}`.

## Endpoints principales

La sesión viaja en una cookie `HttpOnly`. Las rutas con datos de proyectos requieren sesión iniciada.

| Recurso | Rutas |
|---|---|
| Estado | `GET /health` |
| Autenticación | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/password-reset`, `POST /auth/password-reset/confirm` |
| Proyectos | `GET`, `POST /projects` · `GET`, `PATCH`, `DELETE /projects/{id}` |
| Plantillas | `GET /templates` · `POST /templates/{template_id}/projects` |
| Terrenos, materiales, planos, elevaciones, cuartos, componentes | `GET`, `POST /projects/{id}/{recurso}` · `GET`, `PATCH`, `DELETE /{recurso}/{id}`, con `terrains`, `materials`, `plans`, `elevations`, `rooms` y `components` |
| Archivos | `GET`, `POST /projects/{id}/files` · `GET`, `DELETE /files/{id}` · `GET /files/{id}/content` |
| Estructura | `GET /projects/{id}/structure` · `PATCH /projects/{id}/structure/roof` · `PATCH /projects/{id}/structure/{kind}/{element_id}/surface` |
| Recomendaciones | `GET`, `POST /projects/{id}/recommendations` · `POST /projects/{id}/recommendations/generate` · `DELETE /recommendations/{id}` |
| Deshacer | `GET`, `POST /projects/{id}/undo` · `POST /projects/{id}/redo` |
| Asistente | `GET /assistant/status` · `GET`, `POST /projects/{id}/conversations` · `GET`, `DELETE /conversations/{id}` · `POST /conversations/{id}/messages` |
| Resumen | `GET /summary` |

## Servicios externos

No se usa ninguna API externa de pago ni con clave.

- **Ollama** (opcional): modelo de IA local, sin clave. Si no está en marcha, el asistente responde con reglas fijas.
- **SMTP** (opcional): correo de recuperación de contraseña.

`python -m app.check` comprueba el asistente, y `python -m app.check correo@ejemplo.com` también el correo.

## Conexión con la interfaz

`FRONTEND-ARQUILA` llama a esta API. Solo se aceptan peticiones de navegador desde los orígenes de `APP_URL` o `CORS_ORIGINS`.

## Organización

```text
app/
├── api/               Rutas
├── services/          Reglas de la aplicación
├── repositories/      Acceso a la base de datos
├── data_structures/   Estructuras de datos implementadas a mano
├── models.py          Modelos de SQLAlchemy
├── schemas.py         Validación de entrada y salida
└── main.py            Aplicación, CORS y manejo de errores
tests/                 Pruebas
```

## Pruebas y calidad

```bash
pytest
ruff format --check app tests
ruff check app tests
```

`pytest` usa SQLite en memoria. Para ejecutarlo contra PostgreSQL, definir `TEST_DATABASE_URL` con una base cuyo nombre termine en `test` (se vacía antes de cada prueba).

## Documentación

- `docs/BACKEND_Y_API.md`: decisiones del backend y de la interfaz (autenticación, seguridad, registro de eventos, archivos, terreno, IA).
- La documentación general del proyecto (requerimientos, estructuras de datos, complejidad, pruebas) está en el repositorio [ARQUILA](https://github.com/ssantivr/ARQUILA).

Para que Ruff formatee los archivos antes de cada commit, activar los hooks una vez con `pre-commit install`.
