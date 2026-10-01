# Backend Ferretería — sistema de gestión para ferreterías

API REST de un sistema de gestión pensado para que **cualquier ferretería** lo instale
y lo use con sus propios datos: caja de mostrador, ciclo comercial
**pedido de cliente → solicitud de presupuesto → orden de compra → orden de envío**,
catálogo, contactos, inventario (kardex y ajustes de stock), reportes de ventas y
administración del personal con roles.

Cada instalación (una base de datos + un backend) corresponde a **una empresa**.
La primera vez que se abre, el sistema pide los datos de la ferretería y crea su
usuario administrador; a partir de ahí todo requiere iniciar sesión.

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

## Puesta en marcha para una ferretería nueva

1. Desplegar backend y frontend con una base de datos **vacía** y `SEED_DEMO=false`.
2. Abrir el frontend: al no haber usuarios, muestra la pantalla **Configuración inicial**
   (`POST /configuracion-inicial`), donde se cargan nombre, RUC, dirección, moneda,
   IVA, margen de ganancia por defecto y pie del ticket, y se crea el usuario **administrador**.
   Este paso queda bloqueado en cuanto existe un usuario.
3. Con el admin: dar de alta al personal en **Usuarios**, cargar categorías y productos
   (con código de barras si lo tienen) y el **stock inicial** desde *Inventario → Ajustar stock*.
4. Abrir caja y empezar a vender.

> Hacer el paso 2 apenas se despliega: mientras no haya usuarios, cualquiera que abra
> la URL puede completar la configuración inicial.

## Usuarios, roles y permisos

Sesión con token JWT (`POST /auth/login` → `Authorization: Bearer <token>`, 12 h por defecto).
El token solo lleva el id del usuario: rol y estado se leen de la base en cada request,
así que desactivar a alguien le corta el acceso al instante. Tras 5 contraseñas
incorrectas seguidas, ese email queda bloqueado 5 minutos.

Todo el personal puede **consultar** todos los módulos; **crear, modificar o cambiar de estado**
depende del rol (`app/application/permisos.py`):

| Módulo | Admin | Encargado | Vendedor | Depósito |
|---|:-:|:-:|:-:|:-:|
| Caja (ventas de mostrador) | ✔ | ✔ | ✔ | |
| Pedidos de cliente, clientes | ✔ | ✔ | ✔ | |
| Proveedores, cotizaciones | ✔ | ✔ | | |
| Productos, órdenes de compra y envío, ajustes de stock | ✔ | ✔ | | ✔ |
| Reportes (incluye lectura) | ✔ | ✔ | | |
| Usuarios y datos de la empresa (incluye lectura de usuarios) | ✔ | | | |

Reglas de seguridad: nadie puede quitarse a sí mismo el rol de admin ni desactivarse, y
siempre queda al menos un administrador activo. Los proveedores tienen cuenta (para un
futuro portal) pero no pueden entrar al sistema interno.

## Endpoints

Todos bajo el prefijo `/api/v1` (salvo el chequeo de salud `GET /`).

| Módulo | Rutas |
|---|---|
| Sesión | `POST /auth/login`, `GET /auth/me`, `POST /auth/cambiar-password` |
| Empresa | `GET /empresa` (público), `PUT /empresa`, `GET`/`POST /configuracion-inicial` |
| Usuarios | `/usuarios`, `PUT /usuarios/{id}`, `POST /usuarios/{id}/restablecer-password` |
| Reportes | `GET /reportes/ventas?desde=&hasta=` — totales, medios de pago, ventas por día, productos más vendidos con utilidad estimada |
| Caja | `/caja/turno-abierto`, `/caja/turnos` — `abrir`, `movimientos`, `cerrar`; `/caja/ventas` |
| Dashboard | `GET /dashboard` |
| Catálogo | `/categorias`, `/productos` |
| Contactos | `/clientes`, `/clientes/ciudades`, `/proveedores`, `/proveedor-productos` |
| Pedidos de cliente | `/pedidos-cliente` — `procesar`, `solicitar-todos`, `comparacion`, `mercaderia-recibida`, `cancelar` |
| Solicitudes de presupuesto | `/solicitudes-presupuesto` — `ver`, `cotizar`, `sin-stock`, `aceptar`, `rechazar` |
| Órdenes de compra | `/ordenes-compra` — `enviar`, `confirmar`, `en-transito`, `recibir` (ingresa stock), `cancelar` |
| Órdenes de envío | `/ordenes-envio` — `lista-despachar`, `despachar` (descuenta stock), `entregar`, `devolver`, `cancelar` |
| Inventario | `/inventario/stock`, `/inventario/movimientos`, `/inventario/kardex/{producto_id}`, `POST /inventario/ajustes` (inventario inicial / conteo físico) |

El detalle de cada ruta, con sus schemas, está en `/docs` (Swagger) y `/redoc`.

## Desarrollo local

Requiere Python **3.12** (es la versión de Render; ver [Problemas conocidos](#problemas-conocidos)) y un Postgres.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # y completar DATABASE_URL
alembic upgrade head               # crea el esquema
python seed.py --demo              # opcional: carga una ferretería de ejemplo
uvicorn app.main:app --reload      # http://127.0.0.1:8000/docs
```

Sin `--demo`, el frontend arranca en la pantalla de configuración inicial.

### Tests

Tests de integración contra un Postgres descartable (cada test lo vacía y lo recrea):

```bash
pip install pytest httpx
TEST_DATABASE_URL=postgresql+pg8000://user:pass@localhost:5432/ferreteria_test pytest
```

### Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | Conexión a Postgres con driver `pg8000` | `postgresql+pg8000://user:pass@host/db?sslmode=require` |
| `CORS_ORIGINS` | Orígenes del frontend, separados por coma | `https://dynamic-sherbet-5e7a15.netlify.app` |
| `SECRET_KEY` | Firma de las sesiones. **Obligatoria en producción** (la app no arranca sin ella) | salida de `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_MINUTES` | Duración de la sesión | `720` |
| `SEED_DEMO` | `true` carga la ferretería de ejemplo al arrancar; `false` para una empresa real | `false` |
| `APP_NAME` | Nombre que devuelve `GET /` | `Ferretería API` |
| `ENVIRONMENT` | `development` / `production` | `production` |

**URL de Neon:** copiar el *Connection string* del dashboard de Neon y cambiar el prefijo
`postgresql://` por `postgresql+pg8000://`. Los parámetros de SSL se aceptan tal como
vienen (`sslmode=require`, `channel_binding=require`) o como `ssl_context=true`:
`app/infrastructure/db/session.py` los convierte en un `ssl.SSLContext`, que es lo que
espera pg8000. Usar el host con `-pooler` para la app.

## Base de datos

- **Esquema:** lo manejan las migraciones de Alembic (`alembic/versions/`).
  Para un cambio de modelo: `alembic revision --autogenerate -m "descripcion"` y revisar el archivo generado.
- **Datos de demo:** `python seed.py --demo` (o `SEED_DEMO=true`) crea la empresa "Ferretería Demo",
  un usuario por rol (`demo@`, `encargado@`, `vendedor@`, `deposito@ferreteria.local`, contraseña
  `demo12345`), 3 categorías, 8 productos con stock inicial, 2 clientes, 2 proveedores con su
  catálogo y un pedido avanzado en el flujo. Solo inserta lo que falta, así que se puede correr varias veces.
  **No usar en la base de una empresa real**: los usuarios demo tienen contraseña conocida.
- `python seed.py --demo --reset` **borra todo el esquema** y lo vuelve a crear. No usar contra producción.

## Despliegue en Render

El servicio se define en `render.yaml` (Blueprint). En cada arranque corre:

```
alembic upgrade head && python seed.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Así la base queda migrada y con datos sin necesitar shell (el plan Free no la tiene).
Ambos pasos son idempotentes.

- `DATABASE_URL` y `CORS_ORIGINS` están como `sync: false`: se cargan a mano en
  *Environment* del servicio y no se commitean. `SECRET_KEY` la genera Render al sincronizar
  el Blueprint; en un servicio ya creado hay que agregarla a mano **antes** del deploy.
- `seed.py` corre en cada arranque pero no hace nada mientras `SEED_DEMO` sea `false`.
- El Blueprint está conectado por URL pública del repo, así que **un push no redeploya solo**:
  hay que usar *Manual Deploy → Deploy latest commit* en el servicio (o *Manual sync* en el
  Blueprint si cambió `render.yaml`).
- El plan Free duerme el servicio tras 15 min sin tráfico; el primer request posterior
  tarda ~30–50 s.

Verificación rápida:

```bash
curl https://ankor-backend-mqk4.onrender.com/                 # {"status":"ok",...}
curl https://ankor-backend-mqk4.onrender.com/api/v1/empresa   # datos públicos de la empresa
```

## Problemas conocidos

- **`'str' object has no attribute 'wrap_socket'`** — a pg8000 le llegó el flag SSL como texto.
  No crear el engine con la URL cruda: usar `engine_args()` de `session.py` (la app y Alembic ya lo hacen).
- **`TypeError: 'function' object is not subscriptable` al arrancar** — un repositorio define un
  método `list()` y usa `list[...]` en anotaciones. En Python 3.14 funciona por la evaluación diferida
  de anotaciones, pero en 3.12 no. Los módulos con un método `list` llevan `from __future__ import annotations`.
