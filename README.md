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

Requiere Python **3.12** (es la versión de Vercel, fijada en `.python-version`; ver [Problemas conocidos](#problemas-conocidos)) y un Postgres.

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

- `DATABASE_URL`, `CORS_ORIGINS` y `ENVIRONMENT` se cargan en *Settings → Environment Variables*
  (o `vercel env add NOMBRE production --value "..."`) y no se commitean.
  `DATABASE_URL` usa el host **`-pooler`** de Neon: cada request serverless puede abrir su conexión.
- **Migraciones y seed no corren en el deploy.** Tras un cambio de esquema, correrlos desde una
  máquina local contra la URL **directa** de Neon (sin `-pooler`):
  `alembic upgrade head` y, si la base está vacía, `python seed.py`.
- En el plan Hobby, Vercel **bloquea** (estado `BLOCKED`) un deploy si el autor del commit en
  `HEAD` no es el dueño de la cuenta. Desplegar con un commit propio en la punta de la rama.

Verificación rápida:

```bash
curl https://ankor-backend.vercel.app/                 # {"status":"ok","app":"ANKOR API"}
curl https://ankor-backend.vercel.app/api/v1/dashboard
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
