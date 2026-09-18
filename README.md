# ANKOR API — Backend Ferretería

API REST del ERP de distribución **ANKOR**: cubre el ciclo comercial completo
**pedido de cliente → solicitud de presupuesto → orden de compra → orden de envío**,
con catálogo, contactos, inventario (kardex) y un dashboard de resumen.

MVP de exhibición: **no tiene login**. Todos los endpoints operan con un usuario
interno fijo (`demo@ankor.local`) que crea el seed.

| | |
|---|---|
| Runtime | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic |
| Base de datos | PostgreSQL (Neon en producción), driver `pg8000` |
| Hosting | Render (plan Free) — `render.yaml` en la raíz |
| Frontend | [Frontend-Ferreteria](https://github.com/VarDevCoder/Frontend-Ferreteria) en Netlify |

**Producción:** https://ankor-backend-mqk4.onrender.com — documentación interactiva en
[`/docs`](https://ankor-backend-mqk4.onrender.com/docs).

---

## Estructura

Arquitectura por capas: el dominio no conoce a FastAPI ni a SQLAlchemy.

```
app/
├── core/config.py            # Settings desde variables de entorno (.env)
├── domain/                   # Entidades, enums, excepciones y puertos (Protocol)
├── application/services/     # Casos de uso (reglas de negocio y transiciones de estado)
├── infrastructure/
│   ├── db/models.py          # Modelos SQLAlchemy
│   ├── db/repositories/      # Implementaciones de los puertos
│   └── db/session.py         # Engine, sesiones y manejo de SSL para Neon
└── interfaces/api/           # Routers, schemas (Pydantic) y dependencias
alembic/                      # Migraciones
seed.py                       # Datos de demo (idempotente)
```

Las excepciones de dominio se traducen a códigos HTTP en `app/main.py`
(404 no encontrado, 409 conflicto/stock/transición inválida, 422 solicitud inválida).

## Endpoints

Todos bajo el prefijo `/api/v1` (salvo el chequeo de salud `GET /`).

| Módulo | Rutas |
|---|---|
| Dashboard | `GET /dashboard` |
| Catálogo | `/categorias`, `/productos` |
| Contactos | `/clientes`, `/clientes/ciudades`, `/proveedores`, `/proveedor-productos` |
| Pedidos de cliente | `/pedidos-cliente` — `procesar`, `solicitar-todos`, `comparacion`, `mercaderia-recibida`, `cancelar` |
| Solicitudes de presupuesto | `/solicitudes-presupuesto` — `ver`, `cotizar`, `sin-stock`, `aceptar`, `rechazar` |
| Órdenes de compra | `/ordenes-compra` — `enviar`, `confirmar`, `en-transito`, `recibir` (ingresa stock), `cancelar` |
| Órdenes de envío | `/ordenes-envio` — `lista-despachar`, `despachar` (descuenta stock), `entregar`, `devolver`, `cancelar` |
| Inventario | `/inventario/stock`, `/inventario/movimientos`, `/inventario/kardex/{producto_id}` |

El detalle de cada ruta, con sus schemas, está en `/docs` (Swagger) y `/redoc`.

## Desarrollo local

Requiere Python **3.12** (es la versión de Render; ver [Problemas conocidos](#problemas-conocidos)) y un Postgres.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # y completar DATABASE_URL
alembic upgrade head               # crea el esquema
python seed.py                     # carga datos de demo
uvicorn app.main:app --reload      # http://127.0.0.1:8000/docs
```

### Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | Conexión a Postgres con driver `pg8000` | `postgresql+pg8000://user:pass@host/db?sslmode=require` |
| `CORS_ORIGINS` | Orígenes del frontend, separados por coma | `https://dynamic-sherbet-5e7a15.netlify.app` |
| `APP_NAME` | Nombre que devuelve `GET /` | `ANKOR API` |
| `ENVIRONMENT` | `development` / `production` | `production` |

**URL de Neon:** copiar el *Connection string* del dashboard de Neon y cambiar el prefijo
`postgresql://` por `postgresql+pg8000://`. Los parámetros de SSL se aceptan tal como
vienen (`sslmode=require`, `channel_binding=require`) o como `ssl_context=true`:
`app/infrastructure/db/session.py` los convierte en un `ssl.SSLContext`, que es lo que
espera pg8000. Usar el host con `-pooler` para la app.

## Base de datos

- **Esquema:** lo manejan las migraciones de Alembic (`alembic/versions/`).
  Para un cambio de modelo: `alembic revision --autogenerate -m "descripcion"` y revisar el archivo generado.
- **Datos de demo:** `python seed.py` crea el usuario demo, 3 categorías, 8 productos,
  2 clientes, 2 proveedores con su catálogo y un pedido avanzado en el flujo.
  Solo inserta si las tablas están vacías, así que se puede correr varias veces.
- `python seed.py --reset` **borra todo el esquema** y lo vuelve a crear. No usar contra producción.

## Despliegue en Render

El servicio se define en `render.yaml` (Blueprint). En cada arranque corre:

```
alembic upgrade head && python seed.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Así la base queda migrada y con datos sin necesitar shell (el plan Free no la tiene).
Ambos pasos son idempotentes.

- `DATABASE_URL` y `CORS_ORIGINS` están como `sync: false`: se cargan a mano en
  *Environment* del servicio y no se commitean.
- El Blueprint está conectado por URL pública del repo, así que **un push no redeploya solo**:
  hay que usar *Manual Deploy → Deploy latest commit* en el servicio (o *Manual sync* en el
  Blueprint si cambió `render.yaml`).
- El plan Free duerme el servicio tras 15 min sin tráfico; el primer request posterior
  tarda ~30–50 s.

Verificación rápida:

```bash
curl https://ankor-backend-mqk4.onrender.com/                 # {"status":"ok","app":"ANKOR API"}
curl https://ankor-backend-mqk4.onrender.com/api/v1/dashboard
```

## Problemas conocidos

- **`'str' object has no attribute 'wrap_socket'`** — a pg8000 le llegó el flag SSL como texto.
  No crear el engine con la URL cruda: usar `engine_args()` de `session.py` (la app y Alembic ya lo hacen).
- **`TypeError: 'function' object is not subscriptable` al arrancar** — un repositorio define un
  método `list()` y usa `list[...]` en anotaciones. En Python 3.14 funciona por la evaluación diferida
  de anotaciones, pero en 3.12 no. Los módulos con un método `list` llevan `from __future__ import annotations`.
