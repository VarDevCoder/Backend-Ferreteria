# Análisis de requerimientos — SAIL para ferreterías

Qué hace una ferretería real en su día a día, qué cubre hoy el sistema y en qué orden
conviene cerrar las brechas. Cada sección tiene una explicación simple y, debajo, el
detalle técnico.

> Estado: **propuesta para aprobar**. No se implementa nada hasta que se elija qué hacer.

---

## 1. Resumen

**En simple:** hoy el sistema está pensado sobre todo para **encargos**: un cliente pide
algo, se cotiza a los proveedores, se compra y se le envía. Eso existe en una ferretería,
pero es la excepción. Lo que llena el día es **el mostrador**: el cliente pide, se busca el
producto, se cobra y se va, muchas veces por metro, kilo o suelto. Esa venta funciona, pero
es lenta: el producto se elige de una lista desplegable con todo el catálogo, sin lector de
código de barras ni total a la vista. Además no hay IVA, listas de precios (minorista,
mayorista, contratista), cuenta corriente, devoluciones de mostrador, ajuste de inventario
ni reportes.

**Técnico:** el dominio actual es el de ANKOR (distribuidor):
`PedidoCliente → SolicitudPresupuesto → OrdenCompra → OrdenEnvio`, más `CajaTurno` y
`VentaMostrador`. `Producto` tiene un solo precio (`precio_venta`, entero en Gs.), una
`unidad_medida` de texto libre, sin factor de conversión, y ningún campo de impuesto ni de
código de barras. No hay autenticación: todo se registra con el usuario `demo@ankor.local`.
No hay tests.

**Propuesta:** empezar por lo que acelera la venta diaria (búsqueda rápida y código de
barras en caja, ticket, devoluciones y listas de precios), seguir con stock y compras
(ajustes, compra sugerida, unidades de compra) y después crédito, reportes, usuarios y
factura electrónica.

---

## 2. Cómo trabaja una ferretería eficiente

Fuentes: documentación de Odoo y ERPNext, sistemas específicos para ferreterías
(Epicor Eagle, POS latinoamericanos), reseñas en Capterra y G2, una tesis universitaria y el
APQC PCF Retail. El detalle está en la [sección 8](#8-fuentes).

### 2.1 Venta de mostrador rápida

- **Simple:** el vendedor escanea el código de barras o escribe parte del nombre o del código.
  El producto entra al ticket con su precio, se ve el total, se cobra, el sistema calcula el
  vuelto y se imprime el ticket. Todo en segundos.
- **Detalle:**
  - En Odoo, un escaneo agrega el producto al carrito, y los códigos pueden incluir precio o
    peso [O1].
  - Epicor Eagle está pensado para "velocidad pura en el mostrador" y da acceso directo a
    ventas, encargos, inventario y búsqueda de clientes [E1][A1].
  - La tesis de la Ferretería Gutierrez identifica como necesidad central "saber vender en
    tiempos rápidos" [T1].
  - Una queja típica en Capterra: "hay que tener la descripción exacta para encontrar el
    producto" [C1]. La búsqueda tiene que ser parcial y tolerante.
- **Fraccionamiento:** se vende por metro, kilo, litro o unidad, y el sistema calcula el
  precio [L1][L2][R1].

### 2.2 Reposición por stock mínimo

- **Simple:** cada producto tiene un mínimo y un máximo. Cuando baja del mínimo, el sistema
  sugiere comprar lo necesario para volver al máximo, agrupado por proveedor. El encargado
  revisa la sugerencia y la convierte en orden de compra.
- **Detalle:** es la regla mín/máx de Odoo. Por ejemplo, con mínimo 5, máximo 25 y stock 4,
  se genera una compra de 21 [O2]. La cantidad puede redondearse a múltiplos (por ejemplo,
  cajas de 12) [O2]. Los POS de ferretería latinoamericanos incluyen "stock mínimo y
  sugerencias de reposición" y detectan productos sin rotación a 90 días o más [L1].

### 2.3 Presupuesto a cliente convertido en venta

- **Simple:** un cliente, a menudo un contratista, pide precio por una lista de materiales.
  Se le entrega un presupuesto con validez de unos días. Si acepta, **con un clic** se
  convierte en venta, sin volver a cargar nada.
- **Detalle:** en ERPNext el flujo es `Quotation → Sales Order → (Delivery Note) → Sales Invoice`
  y cada documento se genera desde el anterior [N1]. En el POS de Odoo, los presupuestos y
  las ventas con entrega posterior ("ship later") son funciones de retail [O1]. En Epicor
  Eagle, los **encargos especiales** (lo que hoy hace SAIL) son un proceso aparte del
  presupuesto común [E1].

### 2.4 Cuenta corriente / crédito

- **Simple:** clientes frecuentes y contratistas compran "a cuenta" y pagan a fin de mes.
  El sistema controla un límite de crédito, un plazo, el saldo, los vencimientos y los
  pagos, y emite un estado de cuenta.
- **Detalle:**
  - Las cuentas de contratista con precios diferenciados, saldo y estado de cuenta tienen que
    estar disponibles en la caja [R1][G1].
  - Eagle permite comprar "on account" [E1].
  - Los POS latinoamericanos manejan "cartera por cliente con cupo, plazo, vencimientos y
    estado de cuenta" [L1].
  - Queja frecuente: conciliar las cuentas por cobrar a mano lleva semanas [R1].

### 2.5 Devoluciones

- **Simple:** el cliente trae algo. Se busca el ticket original, se eligen los productos y
  las cantidades que devuelve, el stock vuelve a subir y se le devuelve el dinero, o queda
  a favor si es cliente con cuenta corriente.
- **Detalle:** en Odoo se busca la orden pagada, se eligen las líneas y la cantidad, y se
  genera un documento que hace referencia al original [O3]. Si ya hubo factura, la nota de
  crédito es "el único método legal" para anularla o modificarla [O4]. Las devoluciones son
  frecuentes en ferretería [G1].

### 2.6 Cierre de caja

- **Simple:** al terminar el turno se cuenta el efectivo, el sistema muestra cuánto debería
  haber y registra la diferencia. Se recomienda cerrar todos los días.
- **Detalle:** en Odoo, el control de cierre muestra la cantidad de ventas y el total, y
  tiene una calculadora de billetes y monedas. Se puede exigir que el conteo coincida o
  justificar la diferencia, y se recomienda cerrar la sesión cada día [O5].

### 2.7 Compras a proveedores

- **Simple:** se compra por caja o bulto y se vende por unidad. Al recibir la mercadería, el
  stock y el costo se actualizan en ese momento.
- **Detalle:** en Odoo la unidad de compra (por ejemplo, "caja de 6") se convierte sola a
  la unidad de stock y venta [O6]. La regla de reposición genera la solicitud al proveedor
  [O2]. "Stock, costos y órdenes de compra deben actualizarse en el momento en que se
  recibe un camión" [R1].
- **Listas de precios:** los POS de ferretería manejan varias (público, mayorista,
  contratista) [L1][L2] y permiten importar precios desde Excel [L2].

### 2.8 Lista de control de procesos (APQC PCF Retail)

El PCF Retail agrupa los procesos operativos en **2.0 Experiencia del cliente**,
**3.0 Marketing de productos**, **4.0 Mercadería (surtido, compras y reposición)** y
**5.0 Entrega de productos** [P1]. Los usé como lista de control:

- La venta, la caja y las devoluciones caen en 2.0 y 5.0.
- La reposición, las compras y las listas de precios caen en 4.0.
- 3.0 (promociones) queda fuera del MVP.

---

## 3. Qué hace hoy el sistema

### 3.1 Entidades (`app/domain/entities.py`)

| Entidad | Para qué sirve | Notas |
|---|---|---|
| `Producto` | Catálogo | `codigo` único, `precio_compra` y `precio_venta` (enteros en Gs.), `stock_actual` y `stock_minimo` (decimal, 3 decimales), `unidad_medida` de texto libre. Sin código de barras, IVA, stock máximo ni unidad de compra. |
| `Categoria` | Agrupar productos | — |
| `Cliente` | Datos de clientes | Nombre, RUC, contacto. Sin límite de crédito ni lista de precios. |
| `Proveedor` + `ProveedorProducto` | Proveedores y su precio por producto | Incluye precio y días de entrega por proveedor. |
| `PedidoCliente` | Encargo de un cliente | 9 estados, de `RECIBIDO` a `ENTREGADO`, más `CANCELADO`. |
| `SolicitudPresupuesto` | Pedir cotización **a un proveedor** | "Presupuesto" aquí es **de compra**, no para el cliente. |
| `OrdenCompra` | Compra al proveedor | Recepción parcial y kardex. Guarda el nombre del proveedor como texto, **sin `proveedor_id`**. |
| `OrdenEnvio` | Despacho al cliente | Descuenta stock al despachar. Si se devuelve, lo reingresa. |
| `MovimientoInventario` | Kardex | Tipos `ENTRADA`, `SALIDA` y `AJUSTE`. `AJUSTE` y `AJUSTE_MANUAL` existen pero **nada los usa**. |
| `CajaTurno` + `MovimientoCaja` | Turno de caja | Fondo inicial, ingresos y retiros, totales por medio de pago, conteo y diferencia. |
| `VentaMostrador` | Venta de contado | Un solo medio de pago por venta, descuento % global. |

### 3.2 Endpoints (prefijo `/api/v1`)

- **Catálogo:**
  - `/categorias`: CRUD.
  - `/productos`: CRUD. La búsqueda `ilike` por nombre o código.
- **Contactos:** `/clientes`, `/proveedores` y `/proveedor-productos`, con CRUD y activar o
  desactivar.
- **Encargos:** `/pedidos-cliente`, con `procesar`, `solicitar-todos`, `comparacion`,
  `mercaderia-recibida` y `cancelar`.
- **Cotizaciones a proveedores:** `/solicitudes-presupuesto`, con `ver`, `cotizar`,
  `sin-stock`, `aceptar` (que genera la OC) y `rechazar`.
- **Compras:** `/ordenes-compra`, con `enviar`, `confirmar`, `en-transito`, `recibir` y
  `cancelar`.
- **Envíos:** `/ordenes-envio`, con `lista-despachar`, `despachar`, `entregar`, `devolver` y
  `cancelar`.
- **Inventario:** `/inventario/stock`, `/movimientos` y `/kardex/{id}`. Solo lectura.
- **Caja:** `/caja/turno-abierto`, `/turnos` (abrir, movimientos, cerrar), `/ventas` y
  `/resumen-hoy`.
- **Dashboard:** `/dashboard`.

### 3.3 Pantallas (Frontend-Ferreteria)

- **General:** Dashboard.
- **Mostrador:** Caja.
- **Ciclo comercial:** Pedidos de cliente, Cotizaciones a proveedores, Órdenes de compra y
  Órdenes de envío, cada una con su pantalla de detalle.
- **Catálogo:** Productos y categorías, Clientes, Proveedores.
- **Logística:** Inventario y kardex.

### 3.4 Flujo actual

```
Encargo:   Pedido cliente ─► Cotización a N proveedores ─► Aceptar ─► OC ─► Recepción (+stock)
                                                                          │
                                                         Pedido "mercadería recibida"
                                                                          ▼
                                                    Orden de envío ─► Despacho (−stock) ─► Entrega

Mostrador: Abrir caja ─► Venta (−stock, suma al turno) ─► … ─► Cierre con arqueo
```

### 3.5 Hallazgos técnicos a corregir

1. **Stock negativo en caja.** `CajaService.registrar_venta` valida el stock línea por línea.
   Si el mismo producto aparece en dos líneas, cada una pasa el control por separado y el
   stock puede quedar negativo. Hay que agrupar por `producto_id` antes de validar.
2. **Precio sin control.** El frontend manda `precio_unitario` y el backend lo acepta sin
   límites. Cualquiera puede vender a cualquier precio, y no queda registro de quién lo
   cambió.
3. **OC sin proveedor.** `OrdenCompra` no guarda `proveedor_id`, así que no se pueden hacer
   reportes ni compras sugeridas por proveedor.
4. **Sin login.** Toda operación queda a nombre del usuario demo. En un cierre de caja no se
   sabe qué cajero atendió.
5. **Sin tests automáticos.**

---

## 4. Matriz de brechas

Esfuerzo estimado: **S** ≈ 1 día · **M** ≈ 2–4 días · **L** ≈ 1–2 semanas.

| # | Requerimiento | ¿Lo tiene? | Impacto para el negocio | Esfuerzo |
|---|---|---|---|---|
| 1 | Búsqueda rápida en la venta (código, parte del nombre) | **Parcial**: la API busca, la caja usa un desplegable | **Alto**: cuello de botella diario | S |
| 2 | Código de barras (campo en el producto + escaneo en caja) | **No** | **Alto** | S |
| 3 | Caja ágil: total en vivo, vuelto, atajos de teclado | **Parcial** | **Alto** | S |
| 4 | Ticket imprimible (impresora térmica de 58/80 mm) | **No** | **Alto** | S |
| 5 | Pago mixto (parte efectivo, parte tarjeta) | **No** | Medio | M |
| 6 | Listas de precios (minorista, mayorista, contratista) por cliente | **No** | **Alto** | M |
| 7 | Venta fraccionada (m, kg, lt) con cantidad decimal | **Parcial**: decimal sí, sin unidades controladas | Medio | S |
| 8 | Unidad de compra ≠ unidad de venta (caja → unidad) con conversión | **No** | **Alto** | M |
| 9 | Stock mínimo con alerta | **Sí**: `tiene_stock_bajo` y dashboard | — | — |
| 10 | Stock máximo + **compra sugerida** agrupada por proveedor → OC borrador | **No** | **Alto** | M |
| 11 | Ajuste de inventario y conteo físico (roturas, pérdidas, inventario) | **No**: el enum existe sin uso | **Alto** | S |
| 12 | Presupuesto **a cliente** con validez → convertir en venta | **No**: el "presupuesto" actual es de compra | **Alto** | M |
| 13 | Encargo especial (pedir al proveedor para un cliente) | **Sí**: flujo completo | — | — |
| 14 | Cuenta corriente: límite, plazo, venta a crédito, cobros, estado de cuenta, vencimientos | **No** | **Alto** | L |
| 15 | Devolución de venta de mostrador (reingreso de stock + reintegro en caja) | **No**: solo devolución de envío | **Alto** | M |
| 16 | Nota de crédito fiscal | **No** | **Alto**, cuando haya factura | M (con #22) |
| 17 | Cierre de caja con arqueo | **Sí** | — | — |
| 18 | Cierre: desglose de billetes, reporte de cierre imprimible, cierre por cajero | **Parcial** | Medio | S–M |
| 19 | Actualizar costo al recibir mercadería (último costo o promedio) | **No** | Medio: el margen se desvirtúa | S |
| 20 | Reportes: más vendidos, margen por producto o categoría, sin movimiento, ventas por día y medio de pago | **No**: solo margen por producto | **Alto** | M |
| 21 | Usuarios con login y roles (cajero, encargado, admin) | **No** | **Alto** para controlar la caja | M–L |
| 22 | IVA por producto (10 %, 5 %, exento) y desglose en ticket | **No** | **Alto** (legal) | M |
| 23 | Facturación electrónica | **No** | **Alto** (legal) | L: **solo se deja preparada** |
| 24 | Importar productos y precios desde Excel/CSV | **No** | Medio: carga inicial y actualización de precios | M |
| 25 | OC vinculada al proveedor (`proveedor_id`) | **No** | Medio: requisito de #10 y #20 | S |
| 26 | Varias sucursales o depósitos | **No** | Bajo en el MVP | L |

---

## 5. Candidatos típicos, en detalle

**Unidades de medida y fraccionamiento (#7, #8)**
- *Simple:* comprar "caja x 100 tornillos" y vender "1 tornillo", o comprar un rollo de 100 m
  de cable y vender por metro.
- *Técnico:* agregar a `Producto` una `unidad_venta` controlada (enum `UnidadMedida`) y, para
  la compra, `unidad_compra` y `factor_conversion` (por ejemplo, caja → 100 unidades). La OC
  se carga en unidades de compra y la recepción suma `cantidad × factor` al stock. Además,
  validar si la unidad admite decimales: pz y unidad no; m, kg y lt sí.

**Listas de precios (#6)**
- *Simple:* el mismo producto tiene precio de público, de mayorista y de contratista. Al
  elegir el cliente, la caja aplica su precio sola.
- *Técnico:* tabla `listas_precio` (nombre y regla: % sobre costo o % de descuento sobre la
  minorista) con precios por producto opcionales, y `Cliente.lista_precio_id`. El backend
  calcula el precio y el frontend solo lo muestra. Esto corrige de paso el hallazgo 3.5.2.
  **Falta definir:** ver pregunta 2.

**Stock mínimo con compra sugerida (#10, #25)**
- *Simple:* una pantalla "Qué comprar" que lista lo que está bajo el mínimo, cuánto pedir y a
  qué proveedor, con un botón "Generar órdenes de compra".
- *Técnico:*
  - Agregar `Producto.stock_maximo` y `proveedor_preferido` (o usar el mejor precio de
    `proveedor_productos`).
  - Crear un servicio `ReposicionService.sugerencias()` que calcule
    `max − (stock + pendiente en OC abiertas)` y lo redondee al `factor_conversion`.
  - `generar_ordenes()` crea una OC en `BORRADOR` por proveedor. Requiere `proveedor_id`
    en la OC.

**Búsqueda rápida y código de barras (#1, #2, #3)**
- *Simple:* un campo siempre enfocado en la caja. Se escanea o se escribe "tornillo 8" y
  aparecen coincidencias en vivo. Con Enter se agrega el producto.
- *Técnico:*
  - `Producto.codigo_barras` (único, opcional, con índice).
  - `GET /productos/buscar?q=` que primero busca coincidencia exacta de código o código de
    barras y después por palabras en el nombre (`ilike` por palabra), con límite de 20.
  - En el frontend, reemplazar el `<select>` por un buscador con resultados en vivo.
  - Los lectores de código de barras funcionan como teclado y mandan un Enter al final, así
    que no hace falta ningún driver.

**Presupuesto a cliente (#12)**
- *Simple:* "Presupuestos" nuevos para clientes, con vencimiento. Si se aceptan, se cobran en
  la caja o pasan a cuenta corriente.
- *Técnico:*
  - Entidad `PresupuestoCliente` con ítems y estados `BORRADOR` → `ENVIADO` → `ACEPTADO` →
    `CONVERTIDO`, o bien `VENCIDO` o `RECHAZADO`.
  - `convertir_en_venta()` crea una `VentaMostrador` con los mismos ítems y **precios
    congelados**, y valida el stock en ese momento.
  - No reemplaza el flujo de encargos: sugiero cambiar el nombre en pantalla a "Encargos a
    proveedor".

**Cuenta corriente (#14)**
- *Simple:* nuevo medio de pago "Cuenta corriente". Cada cliente habilitado tiene un límite y
  un plazo. Se registran sus pagos y se imprime el estado de cuenta.
- *Técnico:*
  - `Cliente.limite_credito` y `plazo_dias`.
  - Tabla `movimientos_cuenta_corriente` (cargo por venta, abono por cobro o devolución) con
    saldo calculado.
  - Nuevo `MetodoPago.CUENTA_CORRIENTE`, que no suma al efectivo del turno.
  - Validar el límite al vender y agregar un reporte de antigüedad de saldos (0–30, 31–60 y
    más de 60 días).

**Devoluciones y notas de crédito (#15, #16)**
- *Simple:* desde la venta original se eligen los productos que vuelven. El stock sube y se
  devuelve el dinero desde la caja abierta, o queda como saldo a favor.
- *Técnico:*
  - `DevolucionVenta` con referencia a `VentaMostrador`, que no permite devolver más de lo
    vendido.
  - Movimiento de inventario `ENTRADA` con referencia `DEVOLUCION_VENTA`.
  - `MovimientoCaja.RETIRO` automático, o abono en cuenta corriente.
  - La nota de crédito fiscal se engancha cuando exista la factura electrónica.

**Reportes (#20)**
- *Simple:* qué se vende más, cuánto se gana por producto y categoría, qué productos no se
  mueven hace más de 90 días, y cuánto entró por día y por medio de pago.
- *Técnico:* consultas de agregación sobre `venta_mostrador_items` y `movimientos_inventario`
  en un `ReportesService` de solo lectura, más una pantalla con filtros de fecha y exportación
  a CSV.

**Facturación electrónica (#22, #23)**: **solo se deja preparada.**
- *Simple:* dejar listos los datos que toda factura electrónica necesita, para conectar
  después con el sistema de impuestos del país.
- *Técnico:*
  - Tasa de IVA por producto y desglose de IVA en ventas y ticket.
  - Datos fiscales del emisor (RUC, razón social, timbrado, establecimiento y punto de
    expedición) y numeración correlativa.
  - Una interfaz (puerto) `EmisorComprobantes` en el dominio, sin implementación todavía.
  - La moneda (Gs.) y el uso de RUC sugieren **Paraguay**, que tiene su propio sistema de
    factura electrónica. **Hay que confirmar el país:** ver pregunta 1.

---

## 6. Plan priorizado

Cada funcionalidad se hace en su propia rama y commit, con migración de Alembic nueva, tests
con pytest y la pantalla correspondiente. Se implementa una a la vez y con tu aprobación.

### Fase 0: base técnica (se hace junto con la primera funcionalidad)
- Estructura de tests con pytest (reglas de dominio y servicios con repositorios en memoria).
- Corregir el hallazgo 3.5.1: stock negativo con productos repetidos en una venta.

### Fase 1: vender más rápido (MVP de mostrador)
1. **Caja rápida (#1, #2, #3, #4):** código de barras, buscador en vivo, total y vuelto a la
   vista, atajos de teclado y ticket imprimible. *Es lo que más tiempo ahorra en cada venta.*
2. **Ajuste de inventario y conteo físico (#11):** para que el stock que muestra la caja sea
   real.
3. **Devoluciones de mostrador (#15):** reingreso de stock y reintegro en caja.
4. **Listas de precios (#6):** el precio correcto según el cliente, calculado en el backend.

### Fase 2: stock y compras
5. **OC con `proveedor_id` (#25) y costo actualizado al recibir (#19).**
6. **Unidades de compra y venta con conversión (#7, #8).**
7. **Compra sugerida por stock mín/máx (#10):** genera OC en borrador por proveedor.

### Fase 3: clientes
8. **Presupuesto a cliente → venta (#12).**
9. **Cuenta corriente (#14):** incluye el medio de pago, cobros, estado de cuenta y
   antigüedad de saldos.

### Fase 4: control y gestión
10. **Reportes (#20).**
11. **Usuarios, login y roles (#21), cierre por cajero y reporte de cierre (#18).**
12. **IVA por producto y preparación para factura electrónica (#22, #23).** Si el país lo
    exige desde el día uno, esta funcionalidad puede adelantarse.

### Después del MVP
- Pago mixto (#5).
- Importación desde Excel (#24).
- Varias sucursales (#26).

---

## 7. Preguntas abiertas (definen el diseño)

1. **País:** ¿es Paraguay? Define la factura electrónica, las tasas de IVA (10 %, 5 % y
   exento) y si los precios se cargan con IVA incluido.
2. **Listas de precios:** ¿qué listas usan y cómo se calculan? Por ejemplo, un % sobre el
   costo para cada lista, o un % de descuento sobre el precio minorista.
3. **Crédito:** ¿venden a crédito? ¿Qué plazo y límite usan normalmente? ¿Cobran intereses
   por mora?
4. **Encargos:** ¿el flujo actual de cotizar a proveedores por pedido se sigue usando? La
   propuesta es mantenerlo con el nombre "Encargos a proveedor".
5. **Equipos:** ¿tienen lector de código de barras e impresora térmica? ¿De 58 o 80 mm?
6. **Cajas:** ¿hay varias cajas o cajeros atendiendo al mismo tiempo?

---

## 8. Fuentes

- **[O1]** Odoo — Point of Sale y hardware (escáner, precio y peso en código, clientes y listas de precios, presupuestos y "ship later"): https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale.html · https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale/pos_hardware.html · https://www.odoo.com/app/point-of-sale-features
- **[O2]** Odoo — Reordering rules (mín/máx, múltiplos, RFQ automática): https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/replenishment/reordering_rules.html
- **[O3]** Odoo — Returns and refunds / flujo de reembolso en POS: https://www.odoo.com/documentation/19.0/applications/sales/sales/products_prices/returns.html · https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale/use.html
- **[O4]** Odoo — Credit notes and refunds: https://www.odoo.com/documentation/18.0/applications/finance/accounting/customer_invoices/credit_notes.html
- **[O5]** Odoo — Cash control / cierre de sesión: https://www.odoo.com/documentation/14.0/applications/sales/point_of_sale/shop/cash_control.html
- **[O6]** Odoo — Units of measure (compra por caja, venta por unidad): https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/inventory/product_management/configure/uom.html · https://www.odoo.com/documentation/17.0/applications/inventory_and_mrp/purchase/products/uom.html
- **[N1]** ERPNext — Sales (Quotation → Sales Order → Delivery Note → Sales Invoice): https://frappe.io/erpnext/modules/sales · https://docs.frappe.io/erpnext/sales-invoice
- **[E1]** Epicor Eagle POS (velocidad de mostrador, encargos especiales, compras a cuenta): https://www.epicor.com/en-us/products/retail-management-systems-rms/eagle/point-of-sale-pos/
- **[A1]** AppIntent — Best Hardware Store POS 2026: https://www.appintent.com/software/point-of-sale/retail/hardware-store/
- **[R1]** Rundoo — Best POS for hardware stores (requisitos y problemas frecuentes): https://rundoo.ai/insights/best-pos-for-hardware-stores/
- **[G1]** G2 — Hardware Store POS Software: https://www.g2.com/software/hardware-store-pos · Software Advice: https://www.softwareadvice.com/retail/hardware-pos-software-comparison/
- **[C1]** Capterra — reseñas (Retail Pro: "must have exact product description"; AccuPOS; Shopify POS): https://www.capterra.com/p/164131/Retail-Pro-9/reviews/ · https://www.capterra.com/p/121583/AccuPOS-Point-Of-Sale-Software/reviews/ · Epicor Eagle (UI anticuada, curva de aprendizaje): https://www.trustradius.com/products/epicor-eagle/reviews?qs=pros-and-cons
- **[L1]** FeBePOS — Software para ferreterías (unidades m/kg, listas por tipo de cliente, cartera con cupo, stock mínimo, rotación): https://www.febepos.com/pos/software-para/ferreterias/
- **[L2]** Software LATAM para ferreterías (listas de precios, venta a granel, importación Excel): https://www.multicomercio.mx/sistema-de-ferreterias-punto-de-venta/ · https://www.naturalsoftware.com.ar/software-gestion-ferreterias/
- **[T1]** Changanaqui y Carreño (2024). *Implementación de un sistema de comercialización y la usabilidad del sistema web en la Ferretería Gutierrez SCRL – Huacho 2022*. Universidad Nacional José Faustino Sánchez Carrión (Perú): https://repositorio.unjfsc.edu.pe/bitstream/handle/20.500.14067/8928/TESIS.pdf
- **[P1]** APQC — Retail Process Classification Framework: https://www.apqc.org/about-apqc/news-press-release/apqc-releases-retail-process-classification-framework · https://www.apqc.org/resource-library/resource-listing/apqc-process-classification-framework-pcf-retail-pdf-version-721

**Limitaciones de la investigación:**
- No pude descargar el texto completo de la tesis de la Ferretería Coinco (Universidad del
  Bío-Bío, Chile) ni la de la UNI (Nicaragua): los servidores rechazaron la conexión.
- La tesis [T1] es genérica en requerimientos. Su aporte principal es la necesidad de vender
  rápido.
- Del APQC PCF usé la estructura de categorías publicada, no el detalle de más de 1.000
  procesos, que requiere registrarse en el sitio.
