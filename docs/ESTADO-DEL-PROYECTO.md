# SAIL — Estado del proyecto

Foto del sistema a **octubre de 2026**, para que el equipo no se olvide de nada: qué hay, qué
está sólido, qué está flojo o roto y qué sigue. Cubre los dos repositorios:

- **Backend:** [Backend-Ferreteria](https://github.com/VarDevCoder/Backend-Ferreteria) (FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL/Neon, en Vercel).
- **Frontend:** [Frontend-Ferreteria](https://github.com/VarDevCoder/Frontend-Ferreteria) (HTML/CSS/JS sin build, Fluent 2 Web Components, en Netlify).

Cada punto tiene una explicación simple y, debajo o al lado, el detalle técnico (archivo,
endpoint o tabla).

> **Cómo se armó este documento.** Se leyó el código de la rama `claude/intelligent-ramanujan-l97zgv`
> (backend `12972b0` "Renombra ANKOR a SAIL", frontend `8718173`). Se corrieron los tests del backend
> contra un Postgres local (**16 de 16 pasan**), el verificador de Fluent del frontend (**OK**) y una
> serie de pruebas a mano contra la API (con `TestClient`) para confirmar cada error que figura en la
> sección 3. Lo único que **no** se pudo comprobar desde acá es producción (Vercel y Netlify no
> estaban accesibles desde el entorno de revisión): lo que se dice de producción viene de lo que
> sabe el equipo.

---

## Resumen en 10 líneas

1. SAIL ya cubre el día a día de una ferretería: **caja rápida** con lector de código de barras,
   **pago mixto**, **venta a cuenta** con límite de crédito, **cobranzas**, **inventario con kardex**,
   **reportes**, **usuarios con 4 roles** y **configuración inicial** para una empresa nueva.
2. El flujo de **encargos** (pedido → cotización a proveedores → orden de compra → envío) existe
   completo, pero tiene **un error grave**: registrar la recepción de una orden de compra
   **devuelve error 500 siempre** (ver 3.1-A). Hoy no se puede ingresar mercadería por compras.
3. Hay otros errores concretos en envíos (stock que se pierde al cancelar, pedidos que quedan
   trabados) y varios errores 500 por datos duplicados (sección 3.1).
4. El backend está bien ordenado (capas, reglas en el dominio, permisos validados en el servidor)
   y tiene **16 tests de integración** que pasan; el frontend no tiene tests automatizados.
5. **Producción:** la demo no está cargada (falta `SEED_DEMO=true` en Vercel) y la carga de la demo
   hace **~2.230 consultas** a la base, lo que puede ser lento en Vercel (se está optimizando).
6. El **rediseño Fluent 2** va por la mitad: Inicio, Caja, Inventario, Productos, Clientes,
   Proveedores, Usuarios y Cuentas por cobrar ya están; faltan encargos, reportes, empresa y login.
7. Pendientes de los asesores: **logística** (estados de envío, contra entrega, nota de remisión),
   **stock no vendible** y reclamos, **devoluciones con nota de crédito**, **etiquetas y código de
   barras** para recepción y conteos, **consignación**.
8. Roadmap de producto: **IVA por producto**, **guaraníes + dólares**, **listas de precios**,
   **varias cajas**, **factura electrónica SIFEN**, **SaaS multiempresa** y **versión Windows instalada**.

---

## Índice

1. [Qué tenemos](#1-qué-tenemos)
2. [Lo que está bien implementado](#2-lo-que-está-bien-implementado)
3. [Lo que no está tan bien implementado, pendientes y riesgos](#3-lo-que-no-está-tan-bien-implementado-pendientes-y-riesgos)
4. [Próximos pasos (roadmap)](#4-próximos-pasos-roadmap)
5. [Cómo verlo / probarlo](#5-cómo-verlo--probarlo)

---

## 1. Qué tenemos

### 1.1 Arquitectura y despliegue

**En simple:** una página web (frontend) que habla con un servidor (backend) que guarda todo en
una base de datos. Cada ferretería tiene **su propia base y su propio backend** (todavía no es
multiempresa).

| Pieza | Tecnología | Dónde | Archivos clave |
|---|---|---|---|
| Backend (API REST) | Python 3.12, FastAPI 0.141, SQLAlchemy 2, Alembic, pg8000 | Vercel (plan Hobby), función serverless | `api/index.py`, `vercel.json`, `.python-version`, `.vercelignore` |
| Base de datos | PostgreSQL | Neon | `app/infrastructure/db/models.py`, `alembic/versions/` |
| Frontend | HTML + CSS + JS (módulos ES), **sin build** | Netlify (`git push` a `main` publica) | `netlify.toml`, `assets/js/env.js` |
| Diseño | Fluent UI Web Components v3.1.3, tokens y System Icons de Fluent, todo dentro del repo (sin CDN) | — | `assets/vendor/fluent/`, `assets/css/fluent-tokens.css`, `assets/icons/fluent-icons.svg` |

**Backend por capas** (el dominio no conoce FastAPI ni SQLAlchemy):

```
app/domain/          entidades con reglas (entities.py), enums de estados, excepciones, puertos
app/application/     casos de uso (services/*.py) y permisos por rol (permisos.py)
app/infrastructure/  modelos ORM, repositorios, sesión/SSL de Neon, hashing y JWT, migraciones
app/interfaces/api/  routers, schemas Pydantic y dependencias (deps.py)
app/main.py          arma la app y traduce excepciones de dominio a HTTP (404/409/422/401/403)
```

**Frontend:** una página HTML por pantalla que carga su script de `assets/js/pages/`. Piezas
comunes: `api.js` (único lugar que llama a `fetch`, pone el token y manda al login con 401),
`sesion.js` (token, usuario, empresa y permisos en `localStorage`), `layout.js` (menú por rol),
`ui.js` (moneda, fechas, modales, toasts, `escaparHtml`), `punto-venta.js`, `ticket.js` y
`componentes/` (`tabla.js` = DataGrid + CommandBar, `icono.js`, `tema.js`, `cuenta-corriente.js`).

Todas las rutas de la API van bajo `/api/v1` (salvo `GET /`, chequeo de salud). La documentación
interactiva está en `/docs` (Swagger) y `/redoc`.

### 1.2 Módulos

#### Caja y punto de venta

- **En simple:** se abre la caja con un fondo, se vende buscando por código o por palabras (o con
  el lector de código de barras), se ve el total y el vuelto, se cobra, se imprime el ticket, se
  registran ingresos y retiros de efectivo y al final se cierra con **arqueo** (lo contado contra
  lo que debería haber).
- **Pantalla:** `caja.html` → `assets/js/pages/caja.js` + `assets/js/punto-venta.js` (Fluent).
  Atajos **F2** buscar, **↑ ↓** elegir, **Enter** agregar, **F9** cobrar, **Esc** limpiar. El
  lector "tipea" el código y manda Enter: si coincide exacto, el producto entra solo. Lista de
  ventas del turno con reimpresión del ticket.
- **Endpoints:** `GET /caja/turno-abierto`, `GET /caja/turnos`, `GET /caja/turnos/{id}`,
  `POST /caja/turnos/abrir`, `POST /caja/turnos/{id}/movimientos` (INGRESO/RETIRO),
  `POST /caja/turnos/{id}/cerrar`, `GET`/`POST /caja/ventas`, `GET /caja/resumen-hoy`,
  `GET /productos/buscar?q=` (código exacto o todas las palabras en nombre/código, máx. 50).
- **Tablas:** `caja_turnos` (fondo, totales por medio, conteo, diferencia), `movimientos_caja`,
  `ventas_mostrador` (número `VTA-AAAA-NNNN`), `venta_mostrador_items`, `venta_pagos`.
- **Reglas:** no se vende sin caja abierta; **una sola caja abierta a la vez** para toda la
  empresa; el stock se valida sumando las líneas del mismo producto; solo admin y encargado venden a
  un precio distinto del de lista (`PUEDEN_CAMBIAR_PRECIO_DE_VENTA` en `permisos.py`); descuento %
  global de 0 a 100. Código: `app/application/services/caja_service.py`.

#### Medios de pago y pago mixto

- **En simple:** una venta se puede cobrar con efectivo, débito, crédito, transferencia, QR,
  cheque o "a cuenta", o con **varios a la vez** (por ejemplo, parte en efectivo y parte con
  tarjeta, o una entrega y el resto a cuenta). Los pagos tienen que sumar exactamente el total.
- **Técnico:** enum `MetodoPago` (`app/domain/enums.py`); `MIXTO` es solo el resumen de una venta
  con varios pagos y `TARJETA` es histórico. Cada pago es una fila de `venta_pagos` (con
  `referencia` opcional: últimos dígitos, N° de cheque u operación). Al turno se acumula por grupo
  (`SqlAlchemyCajaTurnoRepository.acumular_venta`): efectivo → `total_ventas_efectivo` (entra al
  arqueo); débito y crédito → `total_ventas_tarjeta`; transferencia, QR y cheque →
  `total_ventas_transferencia`; a cuenta → `total_ventas_a_cuenta`. Migración
  `a1b2c3d4e5f6_medios_de_pago_y_cuenta_corriente.py`.

#### Cuenta corriente y cuentas por cobrar

- **En simple:** a un cliente se le puede vender "fiado" hasta su **límite de crédito** (lo pone un
  admin o encargado). Después se le cobra todo o una parte. Hay una pantalla de **Cuentas por
  cobrar** con quién debe, cuánto, desde cuándo y la antigüedad de la deuda (0-30, 31-60, 61-90,
  +90 días).
- **Pantallas:** `cuentas-corrientes.html` (Fluent) y el panel de cuenta corriente dentro de
  Clientes (`assets/js/componentes/cuenta-corriente.js`), que muestra estado de cuenta y permite
  registrar cobros.
- **Endpoints:** `GET /clientes/{id}/cuenta-corriente`, `POST /clientes/{id}/cuenta-corriente/cobros`,
  `GET /cuentas-corrientes/deudores`. Usan el permiso del módulo **caja** (cobrar es tarea de caja).
- **Tabla:** `movimientos_cuenta_corriente` (CARGO por venta a cuenta, PAGO por cobro; saldo
  calculado) y `clientes.limite_credito`.
- **Reglas** (`cuenta_corriente_service.py`): límite 0 = no compra a cuenta; no se puede pasar
  del límite; no se cobra más que el saldo; **un cobro en efectivo exige caja abierta** y entra al
  arqueo como INGRESO; los cobros con otros medios no pasan por la caja.

#### Clientes

- **En simple:** alta, edición, búsqueda por nombre/RUC/email, filtro por ciudad, activar o
  desactivar; se muestra el saldo de cada uno. Si tiene pedidos o cuenta corriente no se borra:
  se desactiva.
- **Pantalla:** `clientes.html` (Fluent). **Endpoints:** `/clientes` (CRUD),
  `GET /clientes/ciudades`, `POST /clientes/{id}/toggle-activo`. **Tabla:** `clientes` (RUC y
  email únicos). Puede crear y editar: admin, encargado y vendedor; el límite de crédito solo
  admin y encargado.

#### Proveedores

- **En simple:** ficha del proveedor y **su catálogo con precios** y días de entrega por producto.
- **Pantalla:** `proveedores.html` (Fluent). **Endpoints:** `/proveedores` (CRUD + `toggle-activo`),
  `/proveedor-productos` (CRUD + `toggle-disponible`). **Tablas:** `proveedores` (cada uno tiene
  un usuario con rol `proveedor`, pensado para un portal futuro; no puede entrar al sistema
  interno), `proveedor_productos`. Modifican: admin y encargado.

#### Productos y categorías

- **En simple:** catálogo con código (interno o de barras), precio de compra y de venta, stock
  mínimo y unidad. Si no se carga precio de venta se calcula con el margen por defecto de la
  empresa; si no se carga código se genera uno (`PROD-00001`).
- **Pantalla:** `productos.html` (Fluent). **Endpoints:** `/categorias` (CRUD), `/productos`
  (CRUD, filtros `solo_activos`, `categoria_id`, `buscar`), `GET /productos/buscar?q=`.
  **Tablas:** `categorias`, `productos` (`codigo` único; precios enteros en la moneda; stock con 3
  decimales). Modifican: admin, encargado y depósito.
- **Ojo:** no hay campo separado de código de barras (se usa `codigo`), ni IVA por producto, ni
  stock máximo, ni unidad de compra distinta de la de venta; `unidad_medida` es texto libre.

#### Inventario y kardex

- **En simple:** stock de todos los productos, alerta de stock bajo, historial de movimientos de
  cada producto (**kardex**) y **ajustes manuales** (inventario inicial, conteo físico, roturas)
  con motivo obligatorio.
- **Pantalla:** `inventario.html` (Fluent; fue el piloto del rediseño). **Endpoints:**
  `GET /inventario/stock?solo_bajo_stock=`, `GET /inventario/movimientos`,
  `GET /inventario/kardex/{producto_id}`, `POST /inventario/ajustes`. **Tabla:**
  `movimientos_inventario` (tipo ENTRADA/SALIDA/AJUSTE, stock anterior y nuevo, documento de
  referencia: VENTA_MOSTRADOR, ORDEN_COMPRA, ORDEN_ENVIO o AJUSTE_MANUAL, usuario).
- **Regla:** todo cambio de stock pasa por un movimiento; editar un producto **no** toca el stock.

#### Encargos: pedidos de clientes → cotizaciones → órdenes de compra → órdenes de envío

**En simple:** un cliente encarga algo. Si hay stock de todo, se arma el envío directo. Si falta
algo, se pide cotización a los proveedores **solo de lo que falta**, se comparan las ofertas, se
acepta una (eso genera la orden de compra), se recibe la mercadería y se envía al cliente.

```
Pedido (PED-AAAA-NNNN) ──► ¿hay stock? ── sí ──► Orden de envío ──► despacho (−stock) ──► entrega
          │                                                            └─► devolución (+stock)
          └── no ──► cotización a cada proveedor activo ──► comparar ──► aceptar ──► Orden de compra
                                                                             └─► recepción (+stock) ──► envío
```

| Paso | Pantallas | Endpoints | Tablas |
|---|---|---|---|
| Pedido de cliente | `pedidos.html`, `pedido-detalle.html` | `/pedidos-cliente` (CRUD), `procesar`, `cancelar`, `mercaderia-recibida`, `disponibilidad`, `solicitar-todos?solo_faltantes=`, `comparacion` | `pedidos_cliente`, `pedido_cliente_items` |
| Cotización a proveedor | `solicitudes.html` | `/solicitudes-presupuesto` (alta/baja), `ver`, `cotizar`, `sin-stock`, `aceptar` (crea la OC), `rechazar` | `solicitudes_presupuesto`, `solicitud_presupuesto_items` |
| Orden de compra | `ordenes-compra.html`, `orden-compra-detalle.html` | `/ordenes-compra` (CRUD), `enviar`, `confirmar`, `en-transito`, `recibir`, `cancelar` | `ordenes_compra`, `orden_compra_items` |
| Orden de envío | `ordenes-envio.html`, `orden-envio-detalle.html` | `/ordenes-envio` (CRUD), `lista-despachar`, `despachar`, `entregar`, `devolver`, `cancelar` | `ordenes_envio`, `orden_envio_items` |

- Estados: pedido (9: RECIBIDO, EN_PROCESO, PRESUPUESTADO, ORDEN_COMPRA, MERCADERIA_RECIBIDA,
  LISTO_ENVIO, ENVIADO, ENTREGADO, CANCELADO), cotización (7), OC (7, con recepción parcial), envío
  (6). Reglas de transición en `app/domain/entities.py`.
- El proveedor **no** responde por el sistema: el personal carga la respuesta ("Cargar respuesta")
  cuando llega por teléfono, WhatsApp o email.
- Permisos: pedidos (admin, encargado, vendedor); cotizaciones (admin, encargado); OC y envíos
  (admin, encargado, depósito).
- Estas pantallas **todavía no están en Fluent** (etapa 3c).

#### Inicio (dashboard)

- **En simple:** lo vendido hoy, estado de la caja, productos para reponer, pedidos y envíos
  pendientes, total por cobrar y actividad reciente, con accesos según el rol.
- `index.html` → `pages/dashboard.js` (Fluent). Endpoints: `GET /dashboard`, `GET /caja/resumen-hoy`,
  `GET /caja/turno-abierto`, `GET /inventario/stock?solo_bajo_stock=true`.

#### Reportes

- **En simple:** ventas de un período (por defecto, el mes): total, cantidad, ticket promedio,
  por medio de pago, por día, los productos más vendidos con **utilidad estimada** y los pedidos
  entregados.
- `reportes.html` (todavía no Fluent) → `GET /reportes/ventas?desde=&hasta=` (máx. 366 días).
  Código: `reporte_service.py`, `repositories/reporte_repository.py`. Solo admin y encargado
  (ni siquiera pueden leerlo los demás).
- La utilidad usa el **precio de compra actual** del producto, no el costo del momento de la venta.

#### Usuarios, roles y permisos

- **En simple:** cada persona entra con su email y contraseña. Hay 4 roles. Todos pueden
  **consultar** casi todo; **crear, modificar o cambiar de estado** depende del rol. El menú oculta
  lo que el rol no puede usar, pero quien decide es siempre el backend.
- `usuarios.html` (Fluent). Endpoints: `POST /auth/login`, `GET /auth/me` (incluye los permisos),
  `POST /auth/cambiar-password`, `/usuarios` (alta, lista, `PUT /usuarios/{id}`,
  `POST /usuarios/{id}/restablecer-password`). Tablas: `usuarios`, `intentos_login_fallidos`.
- Mapa de permisos: `app/application/permisos.py` (`PUEDE_MODIFICAR`, `SOLO_CON_PERMISO_PARA_LEER`),
  aplicado por `requiere_modulo()` en `app/interfaces/api/deps.py` (GET = lectura, el resto = escritura).

| Módulo | Admin | Encargado | Vendedor | Depósito |
|---|:-:|:-:|:-:|:-:|
| Caja, cobros de cuenta corriente | ✔ | ✔ | ✔ | |
| Pedidos de cliente, clientes | ✔ | ✔ | ✔ | |
| Proveedores, cotizaciones | ✔ | ✔ | | |
| Productos, OC, envíos, ajustes de stock | ✔ | ✔ | | ✔ |
| Reportes (también para leer) | ✔ | ✔ | | |
| Usuarios (también para leer) y datos de la empresa | ✔ | | | |
| Vender a otro precio (`precios_venta`) / asignar crédito (`credito_clientes`) | ✔ | ✔ | | |

- Sesión: JWT HS256 de 12 h que solo lleva el id del usuario; rol y estado se releen de la base
  en cada request (desactivar a alguien corta su acceso al instante). Contraseñas con
  PBKDF2-SHA256 de 260.000 iteraciones. Tras **5 contraseñas incorrectas en 5 minutos** para un
  email, ese email queda bloqueado (registro en la base porque en Vercel cada request puede caer en
  otra instancia). Siempre queda al menos un admin activo y nadie se quita a sí mismo el rol de admin.
- En el frontend el token se guarda en `localStorage` (`ferreteria.token`).

#### Datos de la empresa y configuración inicial

- **En simple:** la primera vez que se abre el sistema (sin usuarios) aparece **Configuración
  inicial**: datos de la ferretería (nombre, razón social, RUC, dirección, moneda, IVA, margen por
  defecto, pie del ticket) y el usuario administrador. Después ese paso queda cerrado y los datos se
  cambian en **Datos de la empresa** (solo admin).
- `setup.html` y `configuracion.html` (no Fluent todavía). Endpoints: `GET /empresa` (público),
  `PUT /empresa`, `GET /configuracion-inicial`, `POST /configuracion-inicial` (devuelve la sesión
  del admin). Tabla `empresa` (una sola fila, `id=1`; moneda por defecto PYG / "Gs." / `es-PY`,
  IVA 10 %, margen 25 %).

#### Ticket

- **En simple:** cada venta ofrece imprimir un ticket (térmica o A4) con los datos de la empresa,
  ítems, descuento, medios de pago e "IVA incluido" (el vuelto se ve en pantalla, no en el ticket). Dice **"Comprobante interno — no válido
  como factura"**.
- `assets/js/ticket.js` (abre una ventana y llama a `window.print()`). El IVA se calcula sobre el
  total con el porcentaje **global** de la empresa: `total × iva / (100 + iva)`.

#### Demo / datos de ejemplo

- **En simple:** con `SEED_DEMO=true` (o `python seed.py --demo`) se carga "Ferretería Demo" con un
  usuario por rol, ~26 productos en 6 categorías, clientes, proveedores con catálogo y **6 semanas
  de operación** (turnos diarios con arqueo, ~350 ventas con todos los medios y pagos mixtos,
  clientes con deudas al día y atrasadas, pedidos en distintas etapas, la caja de hoy abierta).
- `seed.py` + `app/infrastructure/db/demo_historial.py` (inserta directo en las tablas con fechas
  pasadas, semilla fija). Es idempotente: solo agrega lo que falta. Usuarios `demo@`, `encargado@`,
  `vendedor@`, `deposito@sail.local` con contraseña `demo12345`; los de versiones anteriores
  (`@ankor.local`, `@ferreteria.local`) se **desactivan**. `--reset` borra todo el esquema.
- Medido en esta revisión contra un Postgres local vacío: **2.234 consultas** (2,7 s en local)
  la primera vez y **27** las siguientes.

#### Migraciones automáticas en Vercel

- **En simple:** al subir una versión con cambios en la base, la base se actualiza sola al
  arrancar el servidor.
- `api/index.py` llama a `aplicar_migraciones()` (`app/infrastructure/db/migraciones.py`) antes de
  importar la app; `alembic/env.py` toma un lock de Postgres (`pg_advisory_xact_lock`) para que dos
  instancias no migren a la vez; `vercel.json` incluye `alembic.ini` y `alembic/` en la función.
  Se desactiva con `AUTO_MIGRATE=false`. Con `SEED_DEMO=true`, después carga la demo (si falla,
  lo registra en el log y la API sigue levantando).
- Migraciones actuales, en orden: `4e3f668fd87f` esquema inicial → `5b4211eced37` caja y venta de
  mostrador → `7c1d2e3f4a5b` empresa y roles → `8d2e3f4a5b6c` intentos de login fallidos →
  `9e3f4a5b6c7d` numeración de pedidos → `a1b2c3d4e5f6` medios de pago y cuenta corriente.

#### Rediseño Fluent 2 (estilo Windows 11)

| Etapa | Contenido | Estado | Commit (frontend) |
|---|---|---|---|
| 0 | Base: Fluent Web Components, tokens, sprite de íconos, herramientas (`herramientas/fluent/`) | Hecha | `abf80fa` |
| 1 | Layout global (NavigationView, tema claro/oscuro), `tabla.js` (DataGrid + CommandBar), diálogos | Hecha | `abf80fa` |
| 2 | Piloto: Inventario y kardex | Hecha | `abf80fa` |
| 3a | Inicio y Caja | Hecha | `f02f5f2` |
| 3b | Productos, Clientes, Proveedores, Usuarios | Hecha | `d94c043` |
| — | Cuentas por cobrar (pantalla nueva, nació en Fluent) | Hecha | `d5b7972` |
| 3c | Pedidos, cotizaciones, órdenes de compra, envíos y sus detalles | **Pendiente** | — |
| 3d | Reportes, datos de la empresa, login y configuración inicial | **Pendiente** (login/setup usan los tokens y el logo, pero no componentes Fluent) | — |
| 4 | Limpieza de estilos viejos de `styles.css` | **Pendiente** | — |

`node herramientas/fluent/verificar.mjs` controla que `styles.css` no tenga colores a mano, que las
14 piezas migradas no usen emojis y que todos los íconos existan en el sprite (48 disponibles).

#### Marca SAIL

- El producto se llama **SAIL** (antes ANKOR: "el ancla te frena, la vela te impulsa"). Logo
  `assets/img/sail-logo.svg` (también favicon); el ticket dice "Sistema SAIL". `APP_NAME` por
  defecto `SAIL API`. Commits `12972b0` (backend) y `8718173` (frontend).
- Quedan nombres viejos a propósito: el dominio del backend `ankor-backend.vercel.app` (cambiarlo
  exige agregar el dominio nuevo en Vercel y después actualizar `API_PRODUCCION` en
  `assets/js/env.js`), el usuario/base `ankor` del entorno local y el nombre del archivo de la
  primera migración. Las claves de `localStorage` se llaman `ferreteria.*`.

### 1.3 Mapa de tablas

| Área | Tablas |
|---|---|
| Personas y acceso | `usuarios`, `intentos_login_fallidos` |
| Empresa | `empresa` |
| Catálogo | `categorias`, `productos` |
| Contactos | `clientes`, `proveedores`, `proveedor_productos` |
| Encargos | `pedidos_cliente`, `pedido_cliente_items`, `solicitudes_presupuesto`, `solicitud_presupuesto_items`, `ordenes_compra`, `orden_compra_items`, `ordenes_envio`, `orden_envio_items` |
| Stock | `movimientos_inventario` |
| Caja y ventas | `caja_turnos`, `movimientos_caja`, `ventas_mostrador`, `venta_mostrador_items`, `venta_pagos` |
| Cuenta corriente | `movimientos_cuenta_corriente` |

Más `alembic_version` (versión del esquema). Todos los importes son **enteros** en la moneda de la
empresa (sin centavos).

---

## 2. Lo que está bien implementado

Cada punto con su evidencia (archivo o test). Los tests están en `tests/` y corren contra un
Postgres real.

### 2.1 Base técnica

- **Capas limpias y reglas en un solo lugar.** Las transiciones de estado y los totales viven en
  las entidades (`app/domain/entities.py`), los casos de uso en `app/application/services/` y los
  routers no tienen `try/except`: `app/main.py` traduce cada excepción de dominio a su código HTTP.
- **Una transacción por request.** `get_db()` (`app/infrastructure/db/session.py`) comitea al
  final o revierte todo si algo falla: una venta que descontó stock de un producto y falla en el
  siguiente no deja nada a medias.
- **Conexión a Neon robusta.** `engine_args()` convierte `sslmode`/`ssl_context` de la URL en un
  `ssl.SSLContext` real e ignora `channel_binding` (errores que ya pasaron y están documentados en
  el README).
- **Migraciones automáticas con lock** (ver 1.2). El seed usa las migraciones, no `create_all`.
- **Validación de entrada** con Pydantic en todos los schemas (montos `ge=0`/`gt=0`, descuentos
  0-100, cantidades `gt=0`, listas con al menos un ítem, largos máximos).

### 2.2 Seguridad y permisos

- **Permisos validados en el servidor**, no solo ocultos en el menú (`requiere_modulo` en `deps.py`).
- **Sesión que se puede cortar al instante** (el token solo trae el id; el resto se relee).
- **`SECRET_KEY` nunca queda con el valor de desarrollo en producción**: si falta, se deriva una
  clave estable de `DATABASE_URL` y se avisa en el log (`app/core/config.py`).
- **Freno a la fuerza bruta guardado en la base** (`LimiteDeIntentos` en `usuario_service.py`).
- **Configuración inicial de un solo uso** (`EmpresaService.configurar_primer_uso`).
- **Siempre queda un admin activo** y nadie se quita a sí mismo el rol.

### 2.3 Venta, pagos y crédito

- Stock validado contra la **suma** de líneas del mismo producto (bug corregido en `d3c0f40`).
- **Precio de lista obligatorio** para vendedor y depósito; el intento devuelve 403.
- **Los pagos tienen que cerrar con el total**, con mensaje claro ("faltan Gs. …").
- **Venta a cuenta controlada**: exige cliente, cliente activo, límite asignado y saldo disponible.
- **Cobro en efectivo integrado al arqueo** (exige caja abierta).

### 2.4 Stock y encargos

- **Kardex completo**: ventas, recepciones, despachos, devoluciones y ajustes generan su movimiento
  con stock anterior y nuevo, documento de referencia y usuario.
- **Pedidos desde stock** sin pasar por compras y **cotización solo de lo faltante**.
- **Búsqueda rápida** con escape de comodines (`%`, `_`) y código exacto para el lector.

### 2.5 Tests del backend (16, todos pasan)

| Archivo | Test | Qué asegura |
|---|---|---|
| `test_empresa_y_permisos.py` | `test_configuracion_inicial_solo_una_vez` | El setup no se puede repetir |
| | `test_login_y_endpoints_protegidos` | Sin token no se entra |
| | `test_bloqueo_por_intentos_fallidos` | 5 fallos bloquean el email |
| | `test_permisos_por_rol` | Cada rol puede lo que le toca |
| | `test_usuario_desactivado_pierde_acceso` | Desactivar corta la sesión |
| | `test_no_se_puede_quedar_sin_admin` | Siempre hay un admin |
| | `test_stock_inicial_venta_y_reporte` | Ajuste → venta → stock → reporte |
| | `test_mismo_producto_en_varias_lineas_no_deja_stock_negativo` | Bug de stock negativo |
| | `test_vendedor_no_puede_cambiar_el_precio` | Control de precio |
| | `test_busqueda_rapida_por_codigo_y_palabras` | Caja rápida |
| | `test_pedidos_numerados_ped` | Numeración `PED-AAAA-NNNN` |
| | `test_pedido_con_stock_se_envia_sin_comprar` | Envío desde stock |
| | `test_pedido_sin_stock_suficiente_cotiza_solo_lo_que_falta` | Cotizar faltantes |
| `test_pagos_y_cuenta_corriente.py` | `test_pago_mixto_suma_a_cada_medio` | Pago mixto en el turno |
| | `test_pagos_deben_sumar_el_total` | Pagos = total |
| | `test_venta_a_cuenta_con_limite_y_cobro` | Límite, cargo y cobro |

### 2.6 Frontend

- **Un solo punto de red** (`api.js`): errores legibles, 401 → login y vuelta a la página.
- **Funciona sin internet para los recursos** (Fluent está dentro del repo) y **sin build**.
- **Caja rápida** cómoda y pensada para teclado y lector de código de barras.
- **Pantallas Fluent con componentes comunes** (`tabla.js`: orden por columna, selección con
  teclado, CommandBar) y **verificador de reglas** que pasa (`OK: sin colores a mano…`).
- **Tema claro/oscuro** que sigue al sistema o se fija por usuario, aplicado antes de pintar.

---

## 3. Lo que no está tan bien implementado, pendientes y riesgos

### 3.1 Errores encontrados en esta revisión (verificados con la API)

Ordenados por gravedad. Todos se reprodujeron contra la rama actual.

| # | Gravedad | Qué pasa (en simple) | Detalle técnico | Arreglo sugerido |
|---|---|---|---|---|
| A | **Crítica** | **No se puede registrar la recepción de una orden de compra**: siempre da error 500. Bloquea todo el flujo de compras (el stock no entra). | `OrdenCompraService.recibir_mercaderia` hace `item.cantidad_recibida += cantidad_recibida` con un `Decimal` (de la base) y un `float` (del JSON, `RecepcionMercaderiaInput.cantidades: dict[int, float]`) → `TypeError`. Está así desde el primer commit; ningún test ni el seed llaman a `recibir`. | Convertir con `Decimal(str(...))` (como ya hacen ajustes y envíos) y agregar un test del flujo completo pedido → cotización → OC → recepción. |
| B | Alta | Al recibir se puede ingresar **más de lo pedido** (se probó 8 sobre 5) y el **precio de compra del producto no se actualiza**. | Sin tope en `recibir_mercaderia`; no se toca `productos.precio_compra`. | Validar `cantidad_recibida ≤ solicitada` (o permitirlo con aviso) y actualizar el costo al recibir. |
| C | Alta | **Cancelar un envío ya despachado hace desaparecer stock**: se descontó al despachar y no vuelve. La pantalla ofrece el botón "Cancelar" en ese estado. | `OrdenEnvio.puede_ser_cancelada()` permite `EN_TRANSITO`; `OrdenEnvioService.cancelar` no reingresa stock. Probado: stock 10 → despacho 4 → cancelar → queda 6. | No permitir cancelar en tránsito (usar "devolver"), o reingresar el stock al cancelar. |
| D | Alta | **Un pedido con envío devuelto queda trabado** en "Enviado": no se puede reenviar ni cancelar (409). | `OrdenEnvioService.devolver` no cambia el estado del pedido, y `ENVIADO` es estado final de `PedidoCliente`. | Al devolver, pasar el pedido a un estado desde el que se pueda reenviar o cancelar. |
| E | Media | **Borrar un envío cancelado "rebobina" el pedido** a "Mercadería recibida" aunque ya se haya entregado con otro envío. | `OrdenEnvioService.eliminar` siempre llama a `_revertir_pedido_a_mercaderia_recibida`. Probado: pedido ENTREGADO → MERCADERIA_RECIBIDA. | Revertir solo si el pedido estaba en `LISTO_ENVIO` por ese mismo envío. |
| F | Media | **Datos repetidos o con historial dan error 500** y en el navegador se ve "No se pudo conectar con el servidor": cliente con RUC o email repetido, proveedor con RUC repetido, categoría con nombre repetido, borrar un producto que ya tuvo ventas. | No se captura `IntegrityError` en ningún lado (ni en servicios ni en `main.py`). La respuesta 500 sale **sin cabecera CORS**, así que `api.js` la ve como error de red. | Validar duplicados en los servicios (como ya hacen productos y usuarios) y un handler de `IntegrityError` → 409; los productos con historial se desactivan, no se borran. |
| G | Media | **Cualquier vendedor puede regalar mercadería**: el descuento llega hasta 100 % sin control por rol (venta de total 0 aceptada). | `VentaMostradorCreate.descuento` `le=100`; no hay permiso como el de precio. Ya lo menciona el README ("sin tope por rol"). | Tope de descuento por rol (por ejemplo, vendedor ≤ 10 %) y registro de quién lo autorizó. |
| H | Media | **En los pedidos el precio es libre** para cualquier rol (se aceptó un pedido a Gs. 1 hecho por un vendedor), a diferencia de la caja. | `PedidoClienteService.crear/actualizar` toma `precio_unitario` del cliente sin validar. | Mismo control que en caja (`puede_cambiar_precio_de_venta`). |
| I | Media | **El reporte de productos más vendidos ignora el descuento de la venta**: una venta de Gs. 3.000 con 50 % figura como 3.000 en el ranking y la utilidad sale inflada. | `productos_mas_vendidos` suma `venta_mostrador_items.subtotal` (antes del descuento global); el total del reporte sí usa `ventas_mostrador.total`. | Prorratear el descuento por ítem o guardar el subtotal neto por línea. |
| J | Media | **Riesgo de XSS** en las pantallas viejas: nombres de clientes, productos o proveedores se insertan en el HTML sin escapar. Como el token está en `localStorage`, un nombre malicioso cargado por un usuario podría robar sesiones. | `pedidos.js`, `ordenes-compra.js`, `orden-compra-detalle.js`, `ordenes-envio.js` y `orden-envio-detalle.js` no usan `escaparHtml`; `solicitudes.js` y `pedido-detalle.js` solo en parte. Las pantallas Fluent sí escapan. | Escapar todo al migrar en la etapa 3c (o antes, porque es seguridad). |
| K | Baja (crece con varias cajas o SaaS) | **Dos operaciones simultáneas pueden pisarse**: stock o totales del turno mal sumados, o dos ventas con el mismo número (la segunda falla con 500). | No hay `SELECT … FOR UPDATE` en ningún repositorio: el stock y los totales del turno se leen, se suman en Python y se escriben. Los números (`VTA-`, `PED-`, OC, envíos, cotizaciones) son `count(*) + 1` del año. Dos aperturas de caja simultáneas podrían dejar dos turnos abiertos. | Bloqueo de fila o `UPDATE … SET stock = stock - x`, secuencias para los números e índice único parcial para "un turno abierto". |
| L | Baja | **"Hoy" se cuenta en la hora del servidor**, no en la de Paraguay (UTC-3): con la base en UTC (lo normal en Neon), lo vendido después de las 21:00 aparece al día siguiente en Inicio y en reportes por día. | `func.current_date()`, `func.date(created_at)` y `date.today()` sin zona horaria; columnas `DateTime` sin zona. | Fijar la zona horaria de la empresa (por ejemplo en la tabla `empresa`) y usarla en las consultas. |
| M | Baja | Cotizaciones rígidas: si un proveedor no tiene **uno** de los productos, toda su cotización queda "sin stock" y no se puede aceptar; se pide cotización a **todos** los proveedores activos aunque no vendan esos productos; la OC no guarda el proveedor (solo su nombre). | `enviar_cotizacion` pone `SIN_STOCK` si algún ítem no tiene stock; `solicitar_cotizacion_todos` no mira `proveedor_productos`; `ordenes_compra` sin `proveedor_id` (pendiente del análisis). | Aceptación parcial, filtrar por catálogo del proveedor y agregar `proveedor_id`. |
| N | Baja | Los modelos y las migraciones **no coinciden del todo** y los tests no prueban las migraciones; no hay CI. | `alembic check` sobre una base migrada detecta diferencias menores (nulabilidad de `created_at`, índices únicos de `productos.codigo` y `usuarios.email`, un índice extra en `movimientos_inventario`). `tests/conftest.py` usa `create_all`. No hay `.github/workflows` en ninguno de los dos repos. | Migración de alineación, un test que corra `alembic upgrade head` y un workflow de CI con Postgres. |

### 3.2 Seguridad: lo que conviene saber

- **Token en `localStorage`**: cualquier XSS (ver J) puede leerlo. Alternativa: cookie `HttpOnly`
  con `SameSite`, o como mínimo escapar todo y agregar una política CSP en `netlify.toml`.
- **No se pueden cerrar sesiones abiertas**: cambiar o restablecer la contraseña no invalida los
  tokens que ya existen (duran 12 h). Solo se corta desactivando al usuario o cambiando `SECRET_KEY`.
- **Bloqueo de login por email, no por IP**: cualquiera que sepa el email del admin puede dejarlo
  sin entrar 5 minutos cada vez; tampoco frena a quien prueba muchos emails distintos.
- **Ventana de la configuración inicial**: mientras una base nueva no tenga usuarios, cualquiera que
  abra la URL puede crear el admin. Hay que hacer el setup apenas se despliega.
- **`/docs` público** en producción (no expone datos, pero muestra toda la API).
- **Proveedores con contraseña**: dar de alta un proveedor exige email y contraseña para un portal
  que todavía no existe.

### 3.3 Limitaciones conocidas (decisiones actuales, no errores)

| Tema | Hoy | Detalle |
|---|---|---|
| Empresas | **Una base por empresa** | `empresa` tiene una sola fila; no hay `empresa_id` en las tablas. |
| IVA | **Un IVA global** de la empresa | `empresa.iva_porcentaje`; el ticket calcula "IVA incluido" sobre el total. En Paraguay hay 10 %, 5 % y exentos. |
| Moneda | **Una sola moneda** | `empresa.moneda_codigo`; importes enteros. No hay dólares ni cotización. |
| Precios | **Un precio de venta** por producto | Sin listas por tipo de cliente. |
| Cajas | **Un solo turno abierto a la vez** | `CajaService.abrir_turno`; el cierre no registra quién cerró (solo quién abrió) y cualquier rol de caja puede cerrar. No hay pantalla de historial de turnos (existe `GET /caja/turnos`, el frontend no lo usa). |
| Comprobantes | **Ticket interno** | No es factura; no hay SIFEN, timbrado ni numeración fiscal. |
| Ventas | **No se pueden anular ni devolver** | No hay endpoint de anulación ni devolución de mostrador; hoy se corrige con un ajuste de stock y un retiro de caja. |
| Utilidad | **Estimada** | Usa el precio de compra actual (y además ignora el descuento global, ver I). |
| Cuenta corriente | Básica | **Sin anulación de cobros**, **sin recibo imprimible**, **sin intereses ni plazo/vencimiento** por cliente (la antigüedad se calcula por días desde la deuda); los cobros no aparecen en ningún reporte; los cobros que no son en efectivo no pasan por la caja. |
| Cobro en efectivo | **Exige caja abierta** | A propósito, para que entre al arqueo. |
| Pedidos | **No se cobran por el sistema** | Un pedido entregado no genera venta, ingreso de caja ni cargo en cuenta corriente; el reporte solo los cuenta (y filtra por `fecha_pedido`, no por fecha de entrega). |
| Productos | Simples | Sin campo aparte de código de barras, sin stock máximo ni compra sugerida, sin unidad de compra con conversión; `unidad_medida` es texto libre (el enum `UnidadMedida` existe pero no se usa); el código no se puede cambiar después de crearlo. |
| Reportes | Solo ventas | Sin exportar a CSV/Excel, sin productos sin movimiento, sin margen por categoría. |
| Frontend | Sin tests | Solo el verificador de reglas Fluent. |
| Documentación | Detalles viejos | El README del backend dice en "Despliegue en Vercel" que la demo no se carga en el deploy (contradice `SEED_DEMO=true`); el README del frontend dice que solo está migrado "layout + Inventario" (ya van 3a y 3b). |

### 3.4 Producción en este momento

- **La demo no está cargada**: la empresa figura como "Mi Ferretería" y no hay ventas. Falta definir
  `SEED_DEMO=true` en *Vercel → Settings → Environment Variables* y redeployar.
- **La carga de la demo es pesada**: ~2.230 consultas la primera vez. Contra Neon desde Vercel cada
  consulta cuesta un viaje de red, así que puede tardar bastante o pasarse del tiempo máximo de la
  función en el primer arranque. Se está optimizando en otra sesión. Después de la primera carga, cada
  arranque hace ~27 consultas de verificación.
- Si la base de producción **no tiene usuarios**, la configuración inicial está abierta para
  cualquiera (ver 3.2). Conviene confirmarlo con `GET /api/v1/configuracion-inicial`.
- Cuando se cargue la demo, recordar que **sus usuarios tienen contraseña conocida**: nunca activar
  `SEED_DEMO` en la base de un cliente real.

### 3.5 Pendientes pedidos por los asesores

| Pedido | En simple | Qué implica técnicamente |
|---|---|---|
| **Logística** | Estados de envío más reales: "Pagado a retirar", "Pagado a entregar", **contra entrega**, y la **nota de remisión** para el traslado. | Nuevos estados en `EstadoOrdenEnvio` (o un estado de pago aparte), vínculo del pedido con el cobro (hoy no existe, ver 3.3), documento imprimible de remisión con numeración. |
| **Stock no vendible** | Separar lo **averiado, abollado o vencido** del stock disponible y poder **reclamarlo al proveedor**. | Stock por estado (o depósitos lógicos), movimientos de traspaso en el kardex, documento de reclamo vinculado al proveedor y a la OC. |
| **Cambios y devoluciones** | El cliente devuelve o cambia algo. En Paraguay la devolución se documenta con **nota de crédito** (la nota de remisión es para traslados). **Validar con el contador.** | `DevolucionVenta` referida a la venta original (sin devolver más de lo vendido), reingreso de stock, reintegro en caja o abono en cuenta corriente; la nota de crédito fiscal depende de SIFEN. |
| **Código de barras y etiquetas** | Usar el lector también al **recibir mercadería** y en los **conteos**, e **imprimir etiquetas** con código y precio. | Escaneo en la recepción de OC y en un modo "conteo" de inventario; generación de códigos (EAN-13 internos) e impresión de etiquetas; posiblemente un campo `codigo_barras` aparte de `codigo`. |
| **Consignación** | Otra tienda vende nuestra mercadería y **liquida** lo vendido quedándose con su porcentaje. | Stock en poder de terceros (ubicación o depósito por consignatario), remitos de envío en consignación, liquidaciones periódicas con comisión y cuenta corriente del consignatario. |

### 3.6 Rediseño Fluent pendiente

- **3c**: pedidos, cotizaciones, órdenes de compra, envíos y sus pantallas de detalle (aprovechar para
  escapar el HTML, ver J).
- **3d**: reportes, datos de la empresa, login y configuración inicial.
- **4**: limpiar los estilos viejos de `assets/css/styles.css` que ya no use ninguna pantalla.
- En curso en otra sesión: **tema y tipografía configurables**.

---

## 4. Próximos pasos (roadmap)

### Ahora (antes de mostrar o vender)

1. **Arreglar la recepción de órdenes de compra** (3.1-A) con un test del flujo completo de encargos.
2. Corregir los errores de envíos (3.1-C, D, E) y el **500 por duplicados** (3.1-F).
3. **Tope de descuento por rol** y control de precio en pedidos (3.1-G, H).
4. **Escapar el HTML** en las pantallas viejas (3.1-J).
5. **Cargar la demo en producción** (`SEED_DEMO=true`) cuando el seed esté optimizado.
6. Actualizar los dos README (3.3, última fila).

### Corto plazo (lo que pidieron los asesores)

7. Devoluciones y cambios de mostrador (con el diseño preparado para la nota de crédito).
8. Logística: estados de envío, contra entrega, cobro de pedidos y nota de remisión.
9. Stock no vendible y reclamos al proveedor.
10. Código de barras en recepción y conteos; impresión de etiquetas.
11. Consignación.
12. Terminar Fluent (3c, 3d, 4) y el tema/tipografía configurables.
13. Base técnica: CI con Postgres, test de migraciones, zona horaria de la empresa, bloqueos de fila
    y numeración con secuencias.

### Mediano plazo (producto)

14. **IVA por producto** (10 %, 5 %, exento) con desglose en el ticket.
15. **Guaraníes y dólares**: precios y cobros en dos monedas con cotización del día.
16. **Listas de precios** por tipo de cliente (minorista, mayorista, contratista), calculadas en el backend.
17. **Varias cajas simultáneas** (turno por caja/cajero, cierre por cajero) — requiere antes el punto 13.
18. **Factura electrónica SIFEN**: datos fiscales del emisor, timbrado, establecimiento y punto de
    expedición, numeración correlativa, nota de crédito; hoy el ticket es solo comprobante interno.
19. Cuenta corriente completa: anulación de cobros, recibo imprimible, plazos e intereses, reporte de
    cobranzas. Reportes con exportación a Excel/CSV y costo real (último costo o promedio).
20. Compra sugerida por stock mínimo/máximo y unidades de compra con conversión.

### Largo plazo (modelo de negocio)

21. **SaaS multiempresa** (suscripción mensual): pasar de "una base por empresa" a `empresa_id` en
    las tablas (o esquema por empresa), alta de empresas, planes, aislamiento de datos y backups por
    cliente. Exige resolver antes los puntos de concurrencia (3.1-K).
22. **Versión instalada para Windows** con **licencia perpetua y actualizaciones opcionales**:
    instalador **Inno Setup**, **Python embebido**, **PostgreSQL** local, backend y base como
    **servicios de Windows con WinSW**, **backups** automáticos, **licencias firmadas** (verificación
    sin conexión) y canal de actualizaciones.

---

## 5. Cómo verlo / probarlo

### URLs

| Qué | URL |
|---|---|
| Frontend (producción) | https://dynamic-sherbet-5e7a15.netlify.app |
| Backend (producción) | https://ankor-backend.vercel.app (el dominio conserva el nombre viejo) |
| API interactiva | https://ankor-backend.vercel.app/docs |
| Salud / datos públicos | `GET /` → `{"status":"ok",...}` · `GET /api/v1/empresa` · `GET /api/v1/configuracion-inicial` |

### Usuarios demo (cuando la demo esté cargada)

Contraseña de todos: **`demo12345`**

| Email | Rol |
|---|---|
| `demo@sail.local` | Administrador |
| `encargado@sail.local` | Encargado |
| `vendedor@sail.local` | Vendedor |
| `deposito@sail.local` | Depósito |

Los usuarios `@ankor.local` y `@ferreteria.local` de versiones anteriores quedan desactivados.

### Correr todo en local

```bash
# Backend (Python 3.12 y un Postgres)
cd Backend-Ferreteria
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # completar DATABASE_URL (postgresql+pg8000://...)
alembic upgrade head
python seed.py --demo                # opcional: ferretería de ejemplo con 6 semanas de ventas
uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs

# Frontend (en otra terminal)
cd Frontend-Ferreteria
python -m http.server 5500           # http://localhost:5500 (usa el backend local solo)
```

Sin `--demo`, el frontend arranca en la **configuración inicial** (empresa nueva).

### Tests y verificaciones

```bash
# Backend: 16 tests de integración contra un Postgres DESCARTABLE (cada test borra y recrea todo)
pip install pytest httpx
TEST_DATABASE_URL=postgresql+pg8000://user:pass@localhost:5432/ferreteria_test pytest
# Sin TEST_DATABASE_URL los tests se saltean (skip), no fallan.

# Backend: ¿modelos y migraciones coinciden? (hoy marca diferencias menores, ver 3.1-N)
alembic check

# Frontend: reglas del sistema de diseño Fluent
node herramientas/fluent/verificar.mjs
```

### Recorrido sugerido para probar a mano

1. Entrar como `vendedor@sail.local`, abrir **Caja**, buscar "tornillo", agregar con Enter, cobrar
   con F9 usando **Varios medios** y luego **A cuenta** con un cliente con crédito. Imprimir el ticket.
2. Ir a **Cuentas por cobrar** y cobrar parte de una deuda en efectivo (con la caja abierta).
3. Como `deposito@sail.local`, hacer un **ajuste de stock** en Inventario y mirar el kardex.
4. Como `encargado@sail.local`, crear un **pedido** con stock y otro sin stock; en el segundo, pedir
   cotización de lo que falta, cargar la respuesta y aceptarla. *Al registrar la recepción de la OC
   aparece el error 3.1-A hasta que se corrija.*
5. Como `demo@sail.local`, ver **Reportes**, **Usuarios** y **Datos de la empresa**.
