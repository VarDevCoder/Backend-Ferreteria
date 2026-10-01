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
| Hosting | Vercel (plan Hobby) — función serverless en `api/index.py` |
| Frontend | [Frontend-Ferreteria](https://github.com/VarDevCoder/Frontend-Ferreteria) en Netlify |

**Producción:** https://ankor-backend.vercel.app — documentación interactiva en
[`/docs`](https://ankor-backend.vercel.app/docs).

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

Requiere Python **3.12** (es la versión de Vercel, fijada en `.python-version`; ver [Problemas conocidos](#problemas-conocidos)) y un Postgres.

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

## Despliegue en Vercel

Proyecto `ankor-backend` en la cuenta `vardevcoder`. La app corre como una función
serverless de Python:

- `api/index.py` importa `app.main:app`; Vercel sirve los archivos de `api/` como funciones.
- `vercel.json` reescribe todas las rutas (`/(.*)`) hacia `/api/index`, así `/`, `/docs` y
  `/api/v1/...` llegan a FastAPI.
- `.python-version` fija Python 3.12. El *Framework Preset* del proyecto es **Other**.

El proyecto **no está conectado a GitHub**: un push no despliega. Se despliega desde la raíz
del repo con Vercel CLI:

```bash
vercel link --yes --project ankor-backend   # una sola vez; crea .vercel/ (ignorado)
vercel --prod
```

- `DATABASE_URL`, `CORS_ORIGINS`, `ENVIRONMENT` y **`SECRET_KEY`** se cargan en
  *Settings → Environment Variables* (o `vercel env add NOMBRE production --value "..."`) y no se
  commitean. Sin `SECRET_KEY` la app **no arranca** en producción.
  `DATABASE_URL` usa el host **`-pooler`** de Neon: cada request serverless puede abrir su conexión.
- **Migraciones y seed no corren en el deploy.** Tras un cambio de esquema, correrlos desde una
  máquina local contra la URL **directa** de Neon (sin `-pooler`) **antes** de desplegar el código nuevo:
  `alembic upgrade head`. Los datos de ejemplo son opcionales: `python seed.py --demo`
  (nunca en la base de un cliente real).
- En el plan Hobby, Vercel **bloquea** (estado `BLOCKED`) un deploy si el autor del commit en
  `HEAD` no es el dueño de la cuenta. Desplegar con un commit propio en la punta de la rama.

Verificación rápida:

```bash
curl https://ankor-backend.vercel.app/                 # {"status":"ok",...}
curl https://ankor-backend.vercel.app/api/v1/empresa   # datos públicos de la empresa
```

## Problemas conocidos

- **`'str' object has no attribute 'wrap_socket'`** — a pg8000 le llegó el flag SSL como texto.
  No crear el engine con la URL cruda: usar `engine_args()` de `session.py` (la app y Alembic ya lo hacen).
- **`TypeError: 'function' object is not subscriptable` al arrancar** — un repositorio define un
  método `list()` y usa `list[...]` en anotaciones. En Python 3.14 funciona por la evaluación diferida
  de anotaciones, pero en 3.12 no. Los módulos con un método `list` llevan `from __future__ import annotations`.
- **Stock negativo en venta de mostrador** — `CajaService.registrar_venta` valida el stock línea por
  línea. Si el mismo producto va en dos líneas, cada una pasa el control y el stock puede quedar negativo.
  *Pendiente de corregir* (Fase 0 del plan).
- **Precio de venta sin control** — `POST /caja/ventas` acepta el `precio_unitario` que manda el
  frontend sin validarlo. *Pendiente* (se resuelve con las listas de precios, Fase 1).

## Análisis y hoja de ruta

El análisis completo está en [`docs/analisis-requerimientos.md`](docs/analisis-requerimientos.md).
Compara el sistema con cómo trabaja una ferretería real y cita sus fuentes: Odoo, ERPNext,
Epicor Eagle, POS latinoamericanos, reseñas de Capterra y G2, una tesis universitaria y el
APQC PCF Retail.

**Hallazgo principal:** el núcleo del sistema es el flujo de **encargos**
(pedido → cotización a proveedores → OC → envío), heredado de ANKOR (distribuidor). En una
ferretería eso es la excepción. El día a día es la **venta de mostrador**, que hoy funciona
pero es lenta:
- el producto se elige de un desplegable con todo el catálogo;
- no hay código de barras;
- no se ve el total en vivo ni hay ticket.

**Qué ya está bien cubierto:**
- caja con apertura, ingresos y retiros, y cierre con arqueo;
- alerta de stock mínimo;
- kardex;
- órdenes de compra con recepción parcial;
- precios por proveedor;
- flujo de encargos completo.

**Brechas principales:**
- búsqueda rápida y código de barras en caja;
- ticket;
- listas de precios (minorista, mayorista, contratista);
- devoluciones de mostrador;
- ajuste de inventario;
- compra sugerida por stock mín/máx;
- unidad de compra distinta de la de venta (caja → unidad);
- presupuesto al cliente;
- cuenta corriente;
- reportes (más vendidos, margen, sin movimiento);
- login y roles;
- IVA y factura electrónica.

Además: no hay tests automáticos, y `OrdenCompra` no guarda `proveedor_id`.

**Plan por fases** (una funcionalidad a la vez, cada una en su rama, con migración nueva y tests):

| Fase | Contenido |
|---|---|
| 0. Base | Tests con pytest y corrección del stock negativo |
| 1. Vender más rápido | Caja rápida (código de barras, buscador, total y vuelto, ticket) · ajuste de inventario · devoluciones · listas de precios |
| 2. Stock y compras | OC con `proveedor_id` y costo al recibir · unidades de compra y venta · compra sugerida |
| 3. Clientes | Presupuesto a cliente → venta · cuenta corriente |
| 4. Gestión | Reportes · usuarios y roles · IVA y factura electrónica (preparada) |

**Estado:** propuesta. Faltan definiciones de negocio antes de implementar: el país (por la
moneda y el RUC, probablemente Paraguay), las listas de precios, la política de crédito, los
equipos (lector e impresora) y si hay varias cajas atendiendo a la vez. Ver la sección 7 del
documento.
