# SAIL — Backlog de mejoras (relevamiento de octubre de 2026)

Lista priorizada de lo que conviene hacer para que SAIL **se pueda vender** como servicio mensual (SaaS) y
como licencia instalada en Windows a ferreterías de Paraguay. Está escrita para los líderes **Backend**,
**Frontend** y **QA**, y para el dueño: cada punto dice el problema en palabras simples, la propuesta
(simple y técnica), por qué ayuda a vender, cuánto cuesta hacerlo y de dónde sale.

> **Cómo se armó.**
> 1. **Uso del sistema:** se levantó la rama `claude/intelligent-ramanujan-l97zgv` (backend `7c7fdd0`,
>    frontend `985654f`) con la demo y se recorrieron los flujos del día con los 4 roles (admin, encargado,
>    vendedor, depósito), en escritorio (1440×900) y celular (390×844): abrir caja, vender, cobrar con
>    varios medios, vender a cuenta, cobrar deudas, ajustar stock, cargar productos, ver pedidos y envíos,
>    cerrar caja y ver reportes. También se probaron reglas contra la API y el rendimiento con un catálogo
>    de tamaño real (12.000 productos y 2.000 clientes). Capturas en `/tmp/claude-0/shots/relevamiento/`
>    (máquina compartida del equipo).
> 2. **Normativa de Paraguay** (DNIT/SIFEN, IVA, nota de remisión, medios de pago, dólares, datos personales),
>    con enlaces en la [sección 7](#7-fuentes).
> 3. **Competencia** en Paraguay y la región.
> 4. **Pedidos del dueño y sus asesores** (los de `docs/ESTADO-DEL-PROYECTO.md`, secciones 3.5 y 4).
>
> **No repite** los errores que ya corrige QA (`ESTADO-DEL-PROYECTO.md` 3.1-A a N); cuando un punto se
> apoya en uno de ellos, lo nombra ("depende de 3.1-K"). Los errores **nuevos** están aparte, en la
> [sección 5](#5-errores-nuevos-para-qa).

**Escalas.** Esfuerzo: **S** ≈ 1 día · **M** ≈ 2–4 días · **L** ≈ 1–2 semanas (**L+** = varias semanas).
Prioridad: **P1** = hace falta para vender o es un pedido central del dueño · **P2** = suma mucho, después
de P1 · **P3** = más adelante o cuando haya demanda.

---

## 1. Resumen: las 10 mejoras más importantes (y por qué)

| # | Mejora | Por qué va primero |
|---|---|---|
| 1 | **[REL-01] Factura electrónica SIFEN** | La DNIT está obligando por grupos (RG 52/2026: grupos que arrancan entre el 1/6/2026 y el 1/9/2027) y a esos contribuyentes **se les vencen los timbrados de facturas en papel**. Toda la competencia paraguaya vende "POS con SIFEN". Un sistema que solo imprime "comprobante interno" no entra en la mayoría de las ferreterías formales. |
| 2 | **[REL-02] IVA por producto (10 %, 5 %, exento)** | Es requisito de la factura (va el IVA por ítem) y del libro de ventas. Hoy hay un solo IVA para toda la empresa. |
| 3 | **[REL-03] Aguantar un catálogo real** | Con 12.000 productos, **Productos tarda ~12 s y Inventario ~25 s** en quedar usable (en escritorio; en celular no responden). Una ferretería mediana tiene miles de artículos: la primera demo con datos reales fallaría. |
| 4 | **[REL-04] Importar desde Excel y aumentar precios en lote** | Nadie va a cargar 5.000 productos a mano. Sin importación, cada alta de cliente cuesta días de trabajo nuestro. Y los precios cambian seguido (proveedor, dólar). |
| 5 | **[REL-05] Devoluciones, cambios y anulaciones con nota de crédito** | Pasa todos los días en una ferretería y hoy **no se puede anular ni devolver una venta**: se "arregla" con un ajuste de stock y un retiro de caja, sin rastro. Con factura electrónica, la única forma legal es la nota de crédito. |
| 6 | **[REL-06] Búsqueda tolerante en la caja** | Buscar "bulon" o "latex" (sin tilde) **no encuentra nada**; "tornilo" tampoco. El cajero pierde la venta o el tiempo. Es barato de arreglar y se nota en la primera demo. |
| 7 | **[REL-07] Listas de precios por tipo de cliente** | Pedido del dueño. Mayorista, contratista y público pagan distinto; hoy el vendedor no puede cambiar el precio (bien) pero tampoco hay forma de aplicar el precio correcto. |
| 8 | **[REL-08] Medios de pago de Paraguay** | El QR ya es el **55 % de los pagos electrónicos** (Bancard). Hoy QR, transferencia y cheque se suman juntos en la caja y no se pueden conciliar por medio. |
| 9 | **[REL-09] + [REL-10] Varias cajas, turno por cajero y arqueo ciego** | Pedido del dueño. Hoy hay **una sola caja para toda la empresa**, cualquiera la cierra y el cajero ve en pantalla cuánto "debería haber", así que el arqueo no controla nada. |
| 10 | **[REL-11] + [REL-12] Cobro de pedidos y logística de envíos** | Pedido del dueño ("Pagado a retirar", "Pagado a entregar"). Hoy un pedido entregado **no se cobra por el sistema** y el envío no tiene cliente, teléfono, estado de pago ni nota de remisión (la DNIT controla el traslado de mercadería). |

Justo detrás: cliente en caja con RUC válido (REL-13), unidades y fraccionamiento (REL-14), stock no
vendible (REL-15, ya en curso), código de barras y etiquetas (REL-16), guaraníes y dólares (REL-18) y SaaS
multiempresa (REL-19).

### Orden sugerido de trabajo

1. **Ya (quick wins, 1–2 semanas):** REL-06 búsqueda, REL-10 arqueo ciego y cierre imprimible, REL-03
   paginación, REL-13 cliente en caja, REL-02 IVA por producto, más los errores nuevos de QA (sección 5).
2. **Para vender (1–2 meses):** REL-04 importación, REL-05 devoluciones, REL-07 listas, REL-08 medios de
   pago, REL-14 unidades, REL-11/12 pedidos y logística, REL-09 varias cajas (después de 3.1-K).
3. **En paralelo, la pieza grande:** REL-01 SIFEN (decidir primero si se integra vía un proveedor
   habilitado o firma propia; ver preguntas al dueño).
4. **Después:** P2 (código de barras, dólares, SaaS multiempresa, presupuestos, reportes...) y P3.

---

## 2. Tabla general

| ID | Título | Prioridad | Esfuerzo | Líder sugerido | Fuente principal |
|---|---|:-:|:-:|---|---|
| REL-01 | Factura electrónica SIFEN | P1 | L+ | Backend | Normativa, competencia |
| REL-02 | IVA por producto y desglose | P1 | M | Backend | Normativa, dueño |
| REL-03 | Catálogo grande: paginación y búsqueda en el servidor | P1 | M | Backend + Frontend | Prueba propia |
| REL-04 | Importar desde Excel y actualizar precios en lote | P1 | M | Backend | Competencia, prueba propia |
| REL-05 | Devoluciones, cambios y anulaciones con nota de crédito | P1 | L | Backend | Dueño, normativa |
| REL-06 | Búsqueda tolerante en la caja | P1 | S | Backend | Prueba propia |
| REL-07 | Listas de precios por tipo de cliente (y redondeo) | P1 | M | Backend | Dueño, competencia |
| REL-08 | Medios de pago de Paraguay y cierre por medio | P1 | M | Backend | Normativa/mercado, prueba propia |
| REL-09 | Varias cajas y turno por cajero | P1 | L | Backend | Dueño |
| REL-10 | Arqueo ciego y reporte de cierre de caja | P1 | S | Frontend | Prueba propia |
| REL-11 | Cobrar pedidos y encargos (seña, saldo, contra entrega) | P1 | M | Backend | Dueño, prueba propia |
| REL-12 | Logística de envíos y nota de remisión | P1 | L | Backend | Dueño, normativa |
| REL-13 | Cliente en la caja: buscador, alta rápida y RUC válido | P1 | S | Frontend | Prueba propia, normativa |
| REL-14 | Unidades de medida y fraccionamiento | P1 | M | Backend | Prueba propia, competencia |
| REL-15 | Stock no vendible y reclamos (en curso) | P1 | M | Backend (en curso) | Dueño |
| REL-16 | Código de barras propio, etiquetas y balanza | P2 | M | Backend | Dueño, competencia |
| REL-17 | Conteo físico con lector | P2 | M | Frontend | Dueño |
| REL-18 | Guaraníes y dólares | P2 | L | Backend | Dueño, normativa |
| REL-19 | SaaS multiempresa | P2 | L+ | Backend | Dueño |
| REL-20 | Presupuestos a clientes | P2 | M | Backend | Competencia |
| REL-21 | Compra sugerida por mínimo y máximo | P2 | M | Backend | Competencia |
| REL-22 | Cuenta corriente completa (recibo, vencimientos, aviso) | P2 | M | Backend | Prueba propia |
| REL-23 | Reportes para el dueño y el contador | P2 | M | Backend | Normativa, prueba propia |
| REL-24 | Caja más rápida (atajos, venta en espera, ticket automático) | P2 | S | Frontend | Prueba propia |
| REL-25 | Caja y listas usables en celular y tablet | P2 | S | Frontend | Prueba propia |
| REL-26 | Consignación | P2 | L | Backend | Dueño |
| REL-27 | Auditoría de acciones sensibles | P2 | M | Backend | Prueba propia |
| REL-28 | Control de margen (precio bajo costo) | P2 | S | Backend | Prueba propia |
| REL-29 | Versión instalada en Windows con licencia perpetua | P3 | L+ | Backend | Dueño |
| REL-30 | Varias sucursales y depósitos | P3 | L | Backend | Competencia |
| REL-31 | App para el celular (PWA): preventa y consulta de stock | P3 | M | Frontend | Competencia |
| REL-32 | Integración con POS y QR de Bancard | P3 | L | Backend | Mercado |
| REL-33 | Menú y pantallas según lo que el rol puede hacer | P3 | S | Frontend | Prueba propia |
| REL-34 | Protección de datos personales (Ley 7593/2025) | P3 | S | Backend | Normativa |

---

## 3. Backlog detallado

### P1 — necesario para vender

#### REL-01 · Factura electrónica SIFEN (e-Kuatia)

- **Problema:** el ticket dice "Comprobante interno — no válido como factura". La ferretería tiene que
  facturar aparte (talonario o el facturador de la DNIT), cargando todo dos veces. A los contribuyentes
  que la DNIT designa como facturadores electrónicos **se les vencen los timbrados en papel** desde que
  empieza su grupo.
- **Propuesta (simple):** al cobrar, SAIL emite la **factura electrónica** con un clic, imprime el KuDE
  (la versión impresa, con el código QR para verificarla) en la impresora térmica o lo manda por WhatsApp
  o email. Con lo mismo se emiten la **nota de crédito** (devoluciones, REL-05) y la **nota de remisión**
  (envíos, REL-12).
- **Propuesta (técnica):**
  - Datos fiscales del emisor en `empresa`: RUC con DV, razón social, actividad económica, timbrado
    (número y vigencia), establecimiento y punto de expedición, CSC; certificado digital (archivo y clave
    guardados cifrados). Numeración correlativa por tipo de documento/establecimiento/punto
    (`001-001-0000001`) con **secuencia en la base** (no `count(*)+1`, ver 3.1-K).
  - Entidad `DocumentoElectronico` (tipo: FE=1, NCE, NDE, NRE=7, AFE; CDC de 44 dígitos; estado:
    pendiente, aprobado, rechazado, cancelado, inutilizado; XML firmado; respuesta del SIFEN; venta o
    devolución de origen). Puerto `EmisorComprobantes` en el dominio con dos implementaciones posibles:
    **(a) vía un proveedor habilitado** (API tipo FacturaSend/FactPy: ellos firman y transmiten) o
    **(b) firma y envío propios** (XML según el Manual Técnico v150, firma XMLDSig, WS de recepción por
    lote, consulta de lote, consulta de RUC y eventos). Recomendación: arrancar con (a) para salir rápido y
    dejar (b) para cuando haya volumen.
  - Cola de envío con reintentos (la transmisión tiene plazo; ver fuentes) y pantalla "Documentos
    pendientes/rechazados". Eventos: **cancelación** (FE hasta 48 h desde la aprobación; otros DTE hasta
    168 h) e **inutilización** de numeración.
  - Condición de la operación (contado/crédito) tomada del medio de pago: una venta "a cuenta" es factura
    **crédito**; los cobros posteriores van en recibo (REL-22).
  - KuDE en formato ticket (58/80 mm) y A4, con QR.
- **Impacto para vender:** muy alto. Es lo primero que pregunta un comercio formal y lo que ofrecen todos
  los competidores locales (FactPy, Facturazzi, Alysoft, eVENDÉ, YoFacturo). Sin esto SAIL compite solo
  contra el cuaderno.
- **Esfuerzo:** L+ (vía proveedor: L; firma propia: varias semanas más) · **Prioridad:** P1 ·
  **Líder:** Backend (Frontend: KuDE, pantalla de documentos; QA: pruebas contra el ambiente de test del
  SIFEN).
- **Dependencias:** REL-02 (IVA por ítem), REL-13 (datos del receptor), 3.1-K (numeración sin
  duplicados), REL-05 (nota de crédito), REL-12 (nota de remisión). Decisión del dueño: proveedor o
  firma propia, y costo por documento.
- **Fuente:** normativa — [RG DNIT 52/2026](https://impuestospy.com/impuestos/resolucion-general-dnit-n-52-2026/),
  [DNIT: nuevos facturadores electrónicos](https://www.dnit.gov.py/web/portal-institucional/w/dnit-designa-nuevos-facturadores-electr%C3%B3nicos),
  [DNIT: proveedores del Estado (RG 41/2025)](https://www.dnit.gov.py/web/portal-institucional/w/dnit-establece-obligatoriedad-de-adhesi%C3%B3n-al-sifen-para-proveedores-del-estado),
  [preguntas frecuentes e-Kuatia (cancelación)](https://www.dnit.gov.py/web/e-kuatia/preguntas-frecuentes/-/categories/367812),
  [Manual Técnico v150](https://tdn.totvs.com.br/download/attachments/502840885/MT_E_Kuatia_V150_24_06_2019.pdf?api=v2);
  competencia — ver sección 6; prueba propia — `06-ticket.png`.

#### REL-02 · IVA por producto (10 %, 5 %, exento) y desglose

- **Problema:** hay un IVA único para toda la empresa (`empresa.iva_porcentaje`) y el ticket calcula
  "IVA incluido" sobre el total. En Paraguay conviven 10 %, 5 % y exento; la factura y el libro de ventas
  piden el IVA separado por tasa.
- **Propuesta (simple):** cada producto tiene su tasa (por defecto 10 %). El ticket y la factura muestran
  cuánto es gravado 10 %, gravado 5 %, exento y el IVA de cada uno. Los reportes también.
- **Propuesta (técnica):** `productos.iva_tipo` (enum `GRAVADO_10`, `GRAVADO_5`, `EXENTO`; migración
  con valor por defecto según `empresa.iva_porcentaje`). Guardar en `venta_mostrador_items` la tasa y el
  IVA **congelados** al vender (`iva_tipo`, `base_imponible`, `iva_monto`), con el descuento global
  prorrateado por línea (resuelve también 3.1-I). Totales por tasa en `ventas_mostrador`. Precios con IVA
  incluido (práctica habitual en mostrador); IVA = `precio × tasa / (100 + tasa)` redondeado por línea.
  Categoría con tasa sugerida para cargar rápido.
- **Impacto para vender:** alto; requisito de REL-01 y del contador.
- **Esfuerzo:** M · **Prioridad:** P1 · **Líder:** Backend (Frontend: campo en producto, ticket).
- **Dependencias:** ninguna; habilita REL-01 y REL-23.
- **Fuente:** pedido del dueño ("IVA por producto"); normativa — Ley 6380/2019 art. 90 y Decreto
  3107/2019 ([Yo Facturo: IVA 10 % y 5 %](https://yo-facturo.com/blog/iva-paraguay-10-5-como-calcular/),
  [La Nación, jul/2026](https://www.lanacion.com.py/negocios/2026/07/17/iva-en-paraguay-el-impuesto-que-esta-presente-en-casi-todas-las-compras/));
  prueba propia — `06-ticket.png` ("IVA incluido (10%)" global).

#### REL-03 · Catálogo grande: paginación y búsqueda en el servidor

- **Problema:** con la demo (26 productos) todo vuela, pero una ferretería real tiene miles de artículos.
  Con **12.000 productos y 2.000 clientes** cargados en la base de prueba:
  - **Productos** tarda **~12 s** en quedar usable y **Inventario ~25 s** (escritorio); con el celular
    simulado (CPU 4× más lenta) Inventario tarda ~21 s solo en cargar y Productos no respondió a un toque
    en 30 s.
  - `GET /productos` y `GET /inventario/stock` devuelven **3,3 MB** cada uno (todo el catálogo).
  - Clientes tarda ~3 s; la caja carga **todos los clientes** en un desplegable.
  - La caja en sí anda bien (busca en el servidor).
- **Propuesta (simple):** las listas muestran de a 50 filas, con buscador y filtros que consultan al
  servidor; la pantalla abre al instante aunque haya 50.000 productos.
- **Propuesta (técnica):** `limit`/`offset` (o cursor) y `total` en `GET /productos`,
  `/inventario/stock`, `/clientes`, `/inventario/movimientos`, `/caja/ventas`; filtros y orden en el
  servidor (`buscar`, `categoria_id`, `solo_bajo_stock`, `orden`). En `componentes/tabla.js`, modo
  "paginado en servidor" (o scroll virtual). Índices: trigram sobre `productos.nombre` (va con REL-06),
  `clientes.nombre/ruc`. Que `ticket.js` no pida `/productos` entero para reimprimir (la venta ya trae lo
  necesario o se pide por ids). Agregar una demo "grande" opcional (`seed.py --demo-grande`) para que QA
  mida.
- **Impacto para vender:** muy alto: es lo primero que se rompe con datos reales.
- **Esfuerzo:** M · **Prioridad:** P1 · **Líder:** Backend (API) + Frontend (tabla).
- **Dependencias:** ninguna. Ayuda a REL-04 (importaciones grandes) y REL-19 (SaaS).
- **Fuente:** prueba propia — script de carga masiva y mediciones (ver QA-N5); captura
  `p-demo-esc-inventario.png` (la página mide 7.500 px de alto con solo 26 productos: stock y kardex sin
  paginar).

#### REL-04 · Importar desde Excel/CSV y actualizar precios en lote

- **Problema:** para empezar a usar SAIL hay que cargar productos, precios, stock inicial y clientes **uno
  por uno** (el stock, además, producto por producto desde "Ajustar stock"). Y cuando el proveedor sube
  los precios (o se mueve el dólar), hay que editar cada producto.
- **Propuesta (simple):** "Importar desde Excel": se baja una planilla modelo, se completa, se sube, el
  sistema muestra qué va a crear o cambiar y los errores fila por fila, y recién ahí se confirma. Y
  "Actualizar precios": subir X % a una categoría, a un proveedor o a una selección, con vista previa y
  redondeo (REL-07).
- **Propuesta (técnica):** endpoints `POST /importaciones/{productos|clientes|stock|proveedor-precios}`
  en dos pasos (`?validar=true` devuelve el diff y errores; después confirmar), CSV y XLSX (`openpyxl`),
  clave por `codigo` (actualiza si existe), todo en una transacción; el stock entra como movimientos de
  ajuste en el kardex (motivo "Inventario inicial"). `POST /productos/actualizar-precios` con filtro
  (categoría, proveedor, ids), % o monto, sobre costo o sobre venta, recálculo con margen. Registro de la
  importación (quién, cuándo, cuántas filas). Exportar a Excel desde las mismas pantallas.
- **Impacto para vender:** muy alto: baja el costo de alta de cada cliente (nuestro y suyo) de días a
  minutos. Todos los competidores lo ofrecen.
- **Esfuerzo:** M · **Prioridad:** P1 · **Líder:** Backend (Frontend: asistente de importación).
- **Dependencias:** REL-03 (listas grandes). Conviene tener REL-02 y REL-14 para incluir IVA y unidad en
  la planilla.
- **Fuente:** competencia (importar precios desde Excel en POS de ferretería, citado en
  `docs/analisis-requerimientos.md` [L2]; listas de precios que cambian por proveedor —
  [Alegra](https://blog.alegra.com/republica-dominicana/sistema-para-ferreteria/)); prueba propia —
  `33-nuevo-producto.png`, `32-ajuste-stock-modal.png`.

#### REL-05 · Devoluciones, cambios y anulaciones con nota de crédito

- **Problema:** si el cliente devuelve una mercadería, la cambia por otra, o el cajero se equivocó, **no
  hay cómo anular ni devolver una venta**. Hoy se corrige con un ajuste de stock y un retiro de caja, sin
  vínculo con la venta original ni control de quién lo hizo.
- **Propuesta (simple):** desde la venta (buscándola por número, por cliente o escaneando el ticket) se
  elige qué vuelve y cuánto. El sistema reingresa el stock (al disponible o al **no vendible** si vino
  fallado), y devuelve el dinero por el mismo medio, deja **saldo a favor** en la cuenta del cliente o
  hace un **cambio** por otro producto cobrando o devolviendo la diferencia. Si la venta tenía factura
  electrónica, emite la **nota de crédito**. Anular una venta del mismo turno (error de carga) es el caso
  "devolver todo". Pide autorización de encargado según el monto.
- **Propuesta (técnica):** entidades `DevolucionVenta` + `DevolucionVentaItem` (referencia a
  `venta_mostrador_items`, no más de lo vendido menos lo ya devuelto, precio neto con el descuento
  prorrateado), número `DEV-AAAA-NNNN`, motivo, usuario y autorizante. Efectos: movimiento de inventario
  `ENTRADA` con `referencia_tipo = DEVOLUCION_VENTA` (al depósito/estado elegido, ver REL-15), egreso en
  la caja abierta por medio (`MovimientoCaja` de tipo `DEVOLUCION`) o abono en
  `movimientos_cuenta_corriente`. Cambio = devolución + venta nueva enlazadas. Con REL-01: NCE asociada a
  la FE (y si la FE está dentro de las 48 h, ofrecer **cancelarla** en lugar de NC). Reportes netos de
  devoluciones.
- **Impacto para vender:** alto; es diaria en ferretería y es la pregunta típica del encargado.
- **Esfuerzo:** L · **Prioridad:** P1 · **Líder:** Backend (Frontend: pantalla y botón en "Ventas de este
  turno"; QA: casos de devolución parcial y doble devolución).
- **Dependencias:** REL-15 (destino "no vendible"), REL-01 (parte fiscal), REL-22 (saldo a favor);
  decisión del contador sobre plazos y quién autoriza.
- **Fuente:** pedido del dueño (cambios y devoluciones con nota de crédito); `ESTADO-DEL-PROYECTO.md` 3.3
  ("Ventas: no se pueden anular ni devolver"); normativa — [DNIT, cancelación vs. nota de
  crédito](https://www.dnit.gov.py/web/e-kuatia/preguntas-frecuentes/-/categories/367812); competencia
  — Odoo (devolución desde la orden original, [O3] en `analisis-requerimientos.md`).

#### REL-06 · Búsqueda tolerante en la caja

- **Problema:** la búsqueda distingue tildes. Probado en la caja y contra la API:
  `bulon` → 0 resultados (el producto es "Bulón"), `BULON` → 0, `latex` → 0 ("látex"), `tornilo` → 0,
  `pintura blanca` → 0 (el producto dice "blanco"). El cajero escribe rápido y sin tildes.
- **Propuesta (simple):** encontrar el producto aunque se escriba sin tilde, con un error de tipeo, en
  plural/singular o con un nombre común ("teflón" / "cinta de sellar"), y ordenar primero lo que más se
  vende.
- **Propuesta (técnica):** extensiones `unaccent` y `pg_trgm` en Postgres; columna normalizada
  (`nombre_busqueda`) o índice funcional `unaccent(lower(nombre))`; cada palabra con `ILIKE` sobre el
  texto normalizado y, si no hay resultados, similitud trigram (`%` / `similarity`). Campo
  `productos.alias` (sinónimos, códigos del proveedor). Orden: código exacto → empieza con → contiene →
  similares, desempate por ventas de los últimos 90 días. Test con los ejemplos de arriba.
- **Impacto para vender:** alto y visible en la primera demo; esfuerzo chico.
- **Esfuerzo:** S · **Prioridad:** P1 · **Líder:** Backend.
- **Dependencias:** ninguna (la migración debe crear las extensiones; en Neon están disponibles).
- **Fuente:** prueba propia — `03-caja-busqueda-tornillo.png`, script `recorrido1.py`/`api1.py`;
  competencia — queja típica "hay que tener la descripción exacta" ([C1] en
  `analisis-requerimientos.md`).

#### REL-07 · Listas de precios por tipo de cliente (y redondeo)

- **Problema:** un producto tiene un solo precio. Al contratista o a otra ferretería se le hace precio a
  ojo; el vendedor no puede cambiarlo (correcto), así que tiene que llamar al encargado o usar el
  descuento global.
- **Propuesta (simple):** listas "Público", "Mayorista", "Contratista" (las que el dueño quiera). Cada
  cliente tiene su lista; al elegirlo en la caja o en el pedido, los precios cambian solos. Opcional:
  precio por cantidad ("desde 10 unidades"). Los precios se **redondean** a lo que se usa en el mostrador
  (por ejemplo a 50 o 100 Gs; hoy salen precios como Gs. 3.125 u 11.875).
- **Propuesta (técnica):** tablas `listas_precio` (nombre, regla: % sobre costo o % sobre la lista
  base, redondeo) y `lista_precio_items` (precio fijo opcional por producto; escalas por cantidad);
  `clientes.lista_precio_id`. Servicio `PrecioService.precio(producto, cliente, cantidad)` usado por caja,
  pedidos y presupuestos: el backend fija el precio (el `precio_unitario` del cliente solo se acepta si
  el rol puede cambiar precios, como hoy). Regla de redondeo en `empresa` (múltiplo y hacia arriba).
  Mostrar en la caja qué lista se aplicó.
- **Impacto para vender:** alto; pedido del dueño y estándar en POS de ferretería.
- **Esfuerzo:** M · **Prioridad:** P1 · **Líder:** Backend (Frontend: ABM de listas, columna en
  clientes).
- **Dependencias:** REL-13 (elegir cliente rápido en caja); se apoya en el control de precio en pedidos
  (3.1-H, lo corrige QA).
- **Fuente:** pedido del dueño ("listas de precios según el tamaño del cliente"); competencia —
  [Alegra: listas mayorista, minorista, crédito, contado](https://blog.alegra.com/republica-dominicana/sistema-para-ferreteria/),
  Odoo ([O1]); prueba propia — `p-demo-esc-productos.png` (precios sin redondear).

#### REL-08 · Medios de pago de Paraguay y cierre por medio

- **Problema:** la caja ofrece Efectivo, Débito, Crédito, Transferencia, QR, A cuenta y Varios medios,
  pero el turno suma **QR, transferencia y cheque en un mismo total** ("Transferencia, QR y otros") y
  débito con crédito en otro. Al cerrar no se puede controlar cada medio contra su resumen (Bancard,
  banco, billetera). No se distingue QR de billetera (Tigo Money, Billetera Personal, Zimple, ueno), ni
  procesadora, ni cheque al día de cheque diferido.
- **Propuesta (simple):** medios configurables por la empresa (por ejemplo "QR Bancard", "Tigo Money",
  "Transferencia SIP Itaú", "Tarjeta crédito Bancard", "Cheque diferido"), cada uno con su grupo
  (efectivo, tarjeta, QR/billetera, transferencia, cheque, a cuenta) y si pide referencia. El cierre
  muestra el total por medio para compararlo con el resumen de cada red, y el cheque diferido guarda la
  fecha de cobro.
- **Propuesta (técnica):** tabla `medios_pago` (nombre, grupo = enum actual `MetodoPago`, activo,
  `requiere_referencia`, recargo % opcional, cuenta destino); `venta_pagos.medio_pago_id`; totales del
  turno por medio en una tabla hija `caja_turno_totales` (en lugar de columnas fijas), con `FOR UPDATE`
  (3.1-K). Cheques: número, banco, fecha de cobro. Reporte "Cobros por medio" diario. Mantener el enum
  como grupo para no romper reportes existentes.
- **Impacto para vender:** alto: el QR ya es mayoría de los pagos electrónicos y el dueño de ferretería
  concilia a diario.
- **Esfuerzo:** M · **Prioridad:** P1 · **Líder:** Backend (Frontend: botones de la caja según la
  configuración).
- **Dependencias:** 3.1-K (concurrencia en totales del turno); se integra con REL-09 y REL-10.
- **Fuente:** prueba propia — `p-deposito-esc-caja.png` (totales agrupados), `07-caja-pago-mixto.png`;
  mercado — [Última Hora: el QR es el 55 % de los pagos electrónicos](https://www.ultimahora.com/el-metodo-qr-avanza-y-acapara-el-55-de-los-pagos-electronicos),
  [La Nación: 7 de cada 10 pagos con el celular](https://www.lanacion.com.py/negocios/2025/12/22/en-paraguay-7-de-cada-10-pagos-se-realizan-con-el-celular/),
  [BCP: SIPAP eleva a Gs. 10 millones las transferencias instantáneas](https://www.bcp.gov.py/web/institucional/w/bcp-actualiza-el-reglamento-del-sipap-y-eleva-el-limite-de-las-transferencias-instantaneas-a-g-10-millones),
  [ABC: SIPAP pasa a llamarse SIP](https://www.abc.com.py/negocios/2026/04/27/bcp-rebautiza-sipap-que-ahora-se-llama-sip-en-que-afecta-a-los-usuarios/),
  [Tigo Money y Bancard (QR)](https://infonegocios.com.py/y-ademas/el-futuro-es-qr-tigo-money-y-bancard-se-unen-para-revolucionar-el-mercado-paraguayo).

#### REL-09 · Varias cajas y turno por cajero

- **Problema:** hay **un solo turno abierto para toda la empresa**: todos venden en la misma caja,
  cualquiera la cierra (se probó: el vendedor cerró el turno que abrió otro usuario) y la diferencia de
  arqueo no se puede atribuir a nadie. Una ferretería con dos mostradores no puede usar SAIL.
- **Propuesta (simple):** se definen las cajas físicas ("Caja 1", "Caja 2", "Caja depósito"). Cada cajero
  abre su turno en una caja, vende y cobra en esa caja y la cierra él (o un encargado). Opcional: modo
  **preventa**, en el que el vendedor arma el pedido en el salón y el cajero solo cobra.
- **Propuesta (técnica):** tabla `cajas` (nombre, punto de expedición asociado para SIFEN, activa);
  `caja_turnos.caja_id`, `usuario_cierre_id`; índice único parcial "un turno abierto por caja"; la venta
  toma el turno de la caja del usuario (en el token o elegido al entrar). Permiso de cierre: el dueño del
  turno o encargado/admin. Dashboard y reportes por caja y por cajero. Preventa: `VentaMostrador` en
  estado `PENDIENTE_COBRO` que la caja trae por número.
- **Impacto para vender:** alto para ferreterías medianas (el cliente objetivo del SaaS); pedido del
  dueño.
- **Esfuerzo:** L · **Prioridad:** P1 · **Líder:** Backend (Frontend: elegir caja al abrir, cola de
  preventas).
- **Dependencias:** **3.1-K** (bloqueos y numeración) antes de habilitar dos cajas; REL-10; REL-01
  (cada caja suele ser un punto de expedición).
- **Fuente:** pedido del dueño ("varias cajas"); prueba propia — `22-cierre-caja-modal.png`,
  `23-caja-cerrada.png`; `ESTADO-DEL-PROYECTO.md` 3.3 (fila "Cajas").

#### REL-10 · Arqueo ciego y reporte de cierre de caja

- **Problema:** la pantalla de caja muestra todo el tiempo el **"Saldo esperado en caja"** al cajero, y
  el diálogo de cierre también lo muestra arriba del campo de conteo (con la aclaración "contá antes de
  mirar esta cifra"). Así el arqueo no controla: el cajero puede "cuadrar". Al cerrar solo aparece un
  aviso que se va ("Caja cerrada con diferencia de Gs. 88.731 (faltante)"); **no queda un reporte de
  cierre** para imprimir y firmar, ni una pantalla con los cierres anteriores.
- **Propuesta (simple):** el cajero declara cuánto contó (con calculadora de billetes y monedas) **sin ver
  lo esperado**; recién después el sistema muestra la diferencia. Al cerrar se imprime el **reporte de
  cierre** (ventas por medio, ingresos y retiros, cobros de cuentas, devoluciones, esperado, contado,
  diferencia, quién abrió y quién cerró). Pantalla "Cierres de caja" para el encargado y el dueño.
- **Propuesta (técnica):** ocultar `saldo_esperado` y los totales a quien no tenga permiso nuevo
  `ver_arqueo` (que `GET /caja/turno-abierto` no lo devuelva para el vendedor); formulario de conteo por
  denominación (`conteo_detalle` JSON); `GET /caja/turnos/{id}/reporte` (ya existe `GET /caja/turnos`,
  falta la pantalla); impresión con `ticket.js`. Umbral de diferencia que exige nota y aviso al
  encargado.
- **Impacto para vender:** alto: el control de caja es el motivo n.º 1 por el que un dueño compra un
  sistema; esfuerzo chico.
- **Esfuerzo:** S · **Prioridad:** P1 · **Líder:** Frontend (Backend: permiso y reporte).
- **Dependencias:** ninguna; se completa con REL-09.
- **Fuente:** prueba propia — `04-caja-carrito.png` (tarjeta "Saldo esperado en caja" visible para el
  vendedor), `22-cierre-caja-modal.png`, `23-caja-cerrada.png`; competencia — Odoo cash control
  (calculadora de billetes, cierre diario) ([O5] en `analisis-requerimientos.md`).

#### REL-11 · Cobrar pedidos y encargos (seña, saldo, contra entrega)

- **Problema:** un pedido de cliente (encargo) se prepara, se compra, se envía y se entrega, pero **nunca
  se cobra por el sistema**: no genera venta, ni ingreso de caja, ni cargo en cuenta corriente. El reporte
  lo cuenta como "pedido entregado" sin que haya entrado plata. Tampoco se puede registrar una **seña**.
- **Propuesta (simple):** el pedido muestra "Total / Pagado / Saldo". Se puede cobrar una seña al
  pedirlo, el total antes de retirar ("Pagado a retirar") o al entregar (contra entrega), en caja o a
  cuenta. Al entregarse, el pedido queda como venta (y factura, con REL-01).
- **Propuesta (técnica):** `pedido_cliente_pagos` (o reutilizar `venta_pagos` con una `VentaMostrador`
  de origen `PEDIDO`); campo `estado_pago` (`PENDIENTE`, `SEÑADO`, `PAGADO`, `A_CUENTA`); los cobros en
  efectivo entran al turno abierto; la entrega convierte el pedido en venta con precios congelados
  (descuenta el stock una sola vez: hoy lo descuenta el despacho del envío, hay que definir cuál manda).
  Reporte de ventas que incluya pedidos cobrados por **fecha de cobro** (hoy filtra por `fecha_pedido`).
- **Impacto para vender:** alto: sin esto el módulo de encargos no cierra el círculo del dinero.
- **Esfuerzo:** M · **Prioridad:** P1 · **Líder:** Backend.
- **Dependencias:** errores de envíos 3.1-C, D, E (QA); base de REL-12.
- **Fuente:** pedido del dueño (logística); `ESTADO-DEL-PROYECTO.md` 3.3 (fila "Pedidos"); prueba propia
  — `p-demo-esc-pedidos.png`, `35-pedido-detalle.png`.

#### REL-12 · Logística de envíos y nota de remisión

- **Problema:** la orden de envío solo tiene dirección, ítems y un estado (Preparando → Lista → En tránsito
  → Entregado). **No muestra el cliente ni su teléfono**, ni si está pagado, ni quién lleva, ni el horario;
  no imprime nada para el chofer. La DNIT exige que la mercadería viaje con **nota de remisión** y está
  intensificando los controles en ruta.
- **Propuesta (simple):** estados que hablan el idioma del negocio, separando **pago** y **entrega**:
  - Pago: "A cobrar en la entrega", "Pagado a retirar" (pagó, viene a buscar), "Pagado a entregar"
    (pagó, se le lleva), "A cuenta".
  - Entrega: Preparando → Listo → En camino → Entregado / No entregado (reprogramar) / Devuelto.
  - Datos de entrega: cliente, contacto, teléfono, dirección y referencia, fecha y franja horaria, costo
    de envío, chofer y vehículo.
  - **Nota de remisión** imprimible (y electrónica con REL-01), **hoja de ruta** del día por chofer y
    confirmación de entrega (nombre de quien recibe, foto opcional desde el celular). Aviso por WhatsApp
    al cliente ("tu pedido salió").
- **Propuesta (técnica):** separar `estado_pago` (de REL-11) del `EstadoOrdenEnvio`; agregar
  `NO_ENTREGADO` (vuelve a `LISTA` sin perder stock); campos `cliente_id` (hoy se llega solo por el
  pedido), `contacto`, `telefono`, `referencia`, `fecha_programada`, `franja`, `costo_envio`, `chofer_id`
  (usuario con rol nuevo `reparto` o texto), `vehiculo`, `recibido_por`; numeración de remisión con
  timbrado; documento NRE (tipo 7) con motivo de traslado (venta, consignación, entre locales,
  devolución) y datos del transporte. Cobro contra entrega: el chofer rinde al volver (ingreso a caja con
  referencia al envío).
- **Impacto para vender:** alto en ferreterías que reparten materiales de construcción (cemento,
  varillas, caños); pedido del dueño.
- **Esfuerzo:** L · **Prioridad:** P1 · **Líder:** Backend (Frontend: migrar envíos a Fluent con estas
  vistas, etapa 3c).
- **Dependencias:** REL-11; errores 3.1-C, D, E (QA); REL-01 para la NRE; REL-26 usa la misma remisión.
- **Fuente:** pedido del dueño ("Pagado a retirar" / "Pagado a entregar", contra entrega, nota de
  remisión); prueba propia — `36-envio-detalle.png`, `p-demo-esc-ordenes-envio.png`; normativa —
  [ABC: requisitos de la DNIT para trasladar mercaderías](https://www.abc.com.py/economia/2025/02/28/estos-son-los-requisitos-de-la-dnit-para-trasladar-mercaderias-dentro-del-territorio/),
  [DNIT refuerza controles](https://www.dnit.gov.py/web/portal-institucional/w/dnit-refuerza-controles-para-disminuir-evasion-e-informalidad),
  [Yo Facturo: nota de remisión y motivos de traslado](https://yo-facturo.com/blog/nota-de-remision-paraguay/).

#### REL-13 · Cliente en la caja: buscador, alta rápida y RUC válido

- **Problema:** en la caja el cliente se elige de un **desplegable con todos los clientes** (con 2.000
  clientes es inmanejable, y en celular peor). No se puede dar de alta un cliente sin salir de la caja. El
  RUC no se valida: se aceptó un cliente con RUC "abc" y otro sin ningún dato fiscal. Para facturar hacen
  falta RUC con dígito verificador (o cédula) y razón social correctos.
- **Propuesta (simple):** campo "Cliente" que busca por RUC, cédula o nombre mientras se escribe; si no
  existe, "Nuevo cliente" en un diálogo corto (RUC/CI, nombre, teléfono). "Consumidor final" con un
  atajo. Si se escribe un RUC, el sistema avisa si el dígito verificador está mal y (con REL-01) trae la
  razón social desde la consulta de RUC del SIFEN.
- **Propuesta (técnica):** `GET /clientes/buscar?q=` (máx. 20, por RUC exacto o palabras);
  validación del DV del RUC (módulo 11: pesos 2 a 11 desde la derecha; resto > 1 → 11 − resto; si no,
  0) en el dominio, con `tipo_documento` (RUC, CI, pasaporte, extranjero) porque no todo receptor tiene
  RUC; componente buscador reutilizable (el del producto) en caja y pedidos; `POST /clientes` desde la
  caja.
- **Impacto para vender:** alto para la velocidad de la caja y requisito de REL-01; esfuerzo chico.
- **Esfuerzo:** S · **Prioridad:** P1 · **Líder:** Frontend (Backend: búsqueda y validación).
- **Dependencias:** REL-03 (clientes paginados). Se complementa con REL-07.
- **Fuente:** prueba propia — `09-caja-a-cuenta.png`, `api1.py` (RUC "abc" aceptado); normativa —
  [Yo Facturo: validador de RUC (módulo 11)](https://yo-facturo.com/herramientas/validador-ruc-paraguay/).

#### REL-14 · Unidades de medida y fraccionamiento

- **Problema:** la unidad es texto libre ("pz", "rollo", "metro", lo que se escriba). El cable se carga
  como "rollo 100 m" y **no se puede vender por metro**; los tornillos son "caja 100" y no se venden
  sueltos. Al revés, un producto por pieza **acepta media unidad** (ver QA-N1).
- **Propuesta (simple):** cada producto tiene su unidad de venta de una lista (unidad, metro, kilo,
  litro, caja...) que dice si admite decimales, y opcionalmente una **unidad de compra** con su
  equivalencia (rollo = 100 m, caja = 100 unidades). Se compra por rollo y se vende por metro; el stock se
  lleva en la unidad de venta.
- **Propuesta (técnica):** usar el enum `UnidadMedida` existente (hoy sin uso) ampliado (`m`, `kg`, `lt`,
  `m2`, `unidad`, `caja`, `bolsa`, `rollo`...) con `admite_decimales`; `productos.unidad_compra` y
  `factor_conversion`; la OC se carga en unidad de compra y la recepción suma `cantidad × factor`;
  precio de compra por unidad de venta = costo / factor. Validación en caja, pedidos y ajustes. Migración
  que mapee los textos actuales al enum. Mostrar "1,5 m" con la unidad en ticket y factura.
- **Impacto para vender:** alto: el fraccionamiento es parte del día en ferretería (cable, cadena,
  clavos por kilo, manguera).
- **Esfuerzo:** M · **Prioridad:** P1 · **Líder:** Backend.
- **Dependencias:** QA-N1 (arreglo rápido mientras tanto); REL-16 (balanza) y REL-21 (compra sugerida)
  usan el factor.
- **Fuente:** prueba propia — `12-caja-medio-alicate.png`, `33-nuevo-producto.png`; competencia — Odoo
  unidades de compra/venta ([O6]), POS de ferretería latinoamericanos ([L1][L2] en
  `analisis-requerimientos.md`), [Alegra: unidades variables](https://blog.alegra.com/republica-dominicana/sistema-para-ferreteria/).

#### REL-15 · Stock no vendible y reclamos al proveedor (en curso)

- **Estado:** lo está haciendo el **líder Backend**. Acá solo se agregan criterios para que encaje con el
  resto del backlog.
- **Problema:** lo averiado, abollado o vencido se mezcla con lo vendible; la caja lo ofrece y el stock
  "bueno" queda inflado.
- **Criterios sugeridos:**
  - El buscador de caja y la disponibilidad de pedidos usan **solo** el stock vendible.
  - Una devolución de cliente (REL-05) puede entrar directo a "no vendible".
  - El reclamo al proveedor queda vinculado a la OC/recepción y termina en reposición, nota de crédito
    del proveedor o baja (con motivo en el kardex).
  - El valor del stock no vendible aparece en un reporte (REL-23).
  - La recepción por lector (REL-16) permite marcar unidades dañadas al recibir.
- **Esfuerzo:** M · **Prioridad:** P1 · **Líder:** Backend (en curso); QA: casos de traspaso y de venta
  bloqueada.
- **Dependencias:** 3.1-A/B (recepción de OC, QA).
- **Fuente:** pedido del dueño y sus asesores (`ESTADO-DEL-PROYECTO.md` 3.5).

### P2 — suma mucho, después de P1

#### REL-16 · Código de barras propio, etiquetas y balanza

- **Problema:** el código del producto hace de código de barras (un solo código por producto, y no se
  puede cambiar después de crearlo). La recepción de compras y los conteos no usan el lector. No se
  imprimen etiquetas de precio, así que los productos sin código de fábrica no se pueden escanear.
- **Propuesta (simple):** cada producto puede tener **varios códigos de barras** (el de fábrica, el del
  proveedor, uno interno). El sistema **genera códigos internos** e **imprime etiquetas** (producto y
  góndola, con precio) en impresora de etiquetas o en hoja A4. Al recibir mercadería se escanea y se va
  sumando. Para lo que se vende pesado (clavos por kilo), lee la etiqueta de la **balanza** que trae el
  peso o el precio.
- **Propuesta (técnica):** tabla `producto_codigos` (código único, tipo EAN-13/EAN-8/interno, factor:
  una caja puede tener su propio código que suma 12 unidades); búsqueda exacta en caja sobre esa tabla;
  generador EAN-13 con prefijo interno (20–29, rango reservado por GS1 para uso interno) y dígito de
  control; plantilla de etiquetas (HTML imprimible, y ZPL para Zebra si el dueño lo confirma); en la
  recepción de OC (pantalla `orden-compra-detalle`) un campo de escaneo que suma a la línea; parser de
  código de balanza configurable (prefijo, largo del PLU, si trae peso o precio).
- **Impacto para vender:** medio-alto; pedido del dueño, acelera recepción y caja.
- **Esfuerzo:** M · **Prioridad:** P2 · **Líder:** Backend (Frontend: etiquetas y escaneo en recepción).
- **Dependencias:** REL-14 (factor), 3.1-A (recepción de OC, QA).
- **Fuente:** pedido del dueño (código de barras para recepción y etiquetas); competencia — Odoo (escáner,
  precio y peso en código, [O1]); [GS1: códigos de peso variable](https://gs1.se/en/guides/how-to-guides/barcode-label-items-of-varying-weight/),
  [Yo Facturo: códigos de balanza](https://yo-facturo.com/herramientas/codigo-de-balanza-peso-variable/);
  prueba propia — `33-nuevo-producto.png` ("Código / código de barras" en un solo campo).

#### REL-17 · Conteo físico con lector

- **Problema:** para un inventario hay que ajustar producto por producto escribiendo el stock nuevo.
  No hay un "conteo" que junte varias líneas, muestre diferencias y se apruebe.
- **Propuesta (simple):** "Nuevo conteo" (todo el depósito, una categoría o una estantería). Se escanea o
  busca cada producto y se carga lo contado, desde la PC o el celular. Al terminar, el sistema muestra las
  diferencias (en unidades y en guaraníes) y el encargado aprueba: recién ahí se ajusta el stock.
- **Propuesta (técnica):** `conteos_inventario` (estado `ABIERTO`/`EN_REVISION`/`APLICADO`, alcance) y
  `conteo_items` (stock del sistema al momento, contado, diferencia); aplicar = un movimiento `AJUSTE`
  por línea con referencia al conteo; tolerar ventas durante el conteo (diferencia contra el stock al
  momento de contar).
- **Impacto para vender:** medio; muy valorado por el dueño (pérdidas y robos).
- **Esfuerzo:** M · **Prioridad:** P2 · **Líder:** Frontend (Backend: entidades y aplicación).
- **Dependencias:** REL-16 (lector), REL-03, REL-25 (celular).
- **Fuente:** pedido del dueño (código de barras en conteos); competencia — conteo cíclico en Odoo y
  Eagle; prueba propia — `31-inventario.png`.

#### REL-18 · Guaraníes y dólares

- **Problema:** todo está en una sola moneda (enteros en Gs.). Algunos productos (herramientas
  importadas) se compran y a veces se venden en dólares, y hay clientes que pagan con dólares, sobre todo
  en zonas de frontera.
- **Propuesta (simple):** cotización del día cargada por el encargado (con la referencia del BCP a la
  vista). Productos con precio en USD que se muestran en Gs. al tipo del día. En la caja se puede cobrar
  una parte en dólares y dar el vuelto en guaraníes. El arqueo cuenta el efectivo de cada moneda por
  separado. Facturar en dólares solo si el dueño lo necesita.
- **Propuesta (técnica):** `monedas` y `cotizaciones` (fecha, compra, venta, fuente); `productos.moneda`
  y `precio_venta_moneda`; precio en Gs. calculado por `PrecioService` (REL-07) con redondeo; pagos con
  `moneda`, `monto_moneda` y `tipo_cambio` (el `monto` sigue en Gs. para que los totales no cambien); turno
  con fondo y conteo por moneda; con REL-01, documento en una moneda con el tipo de cambio y el total en
  Gs. (validar con el contador). Ojo: si el importe en USD lleva centavos, guardar en centavos.
- **Impacto para vender:** medio en general, alto en frontera (Ciudad del Este, Encarnación, Pedro Juan
  Caballero). El guaraní se apreció más de 10 % frente al dólar en 2026, así que conviene que el precio en
  Gs. de lo importado se actualice con la cotización.
- **Esfuerzo:** L · **Prioridad:** P2 (P1 si los clientes objetivo están en frontera) · **Líder:**
  Backend.
- **Dependencias:** REL-07, REL-08, REL-10 (arqueo por moneda).
- **Fuente:** pedido del dueño ("guaraníes y dólares"); normativa/mercado —
  [Yo Facturo: dólar a guaraní y facturas en moneda extranjera](https://yo-facturo.com/blog/dolar-a-guarani-como-convertir/),
  [Infobae/EFE: el guaraní se aprecia más de 10 % en 2026](https://www.infobae.com/america/agencias/2026/08/03/la-moneda-paraguaya-se-aprecia-mas-de-un-10-frente-al-dolar-en-lo-que-va-de-2026/).
  La norma exacta de qué cotización usar en un comprobante en moneda extranjera **no se encontró**: hay
  que confirmarla con el contador.

#### REL-19 · SaaS multiempresa

- **Problema:** cada ferretería necesita su propio backend y su propia base (`empresa` tiene una sola
  fila, no hay `empresa_id`). Vender por mes así significa desplegar y mantener una instalación por
  cliente, y la configuración inicial queda abierta a cualquiera hasta que se completa.
- **Propuesta (simple):** una sola plataforma donde cada ferretería se registra (o la damos de alta),
  elige un plan, entra con su propio subdominio y ve solo sus datos. Copia de seguridad diaria por
  empresa y exportación de sus datos si se va.
- **Propuesta (técnica):** fase 0 (ya, P1 operativo): script de alta por cliente sobre el modelo actual
  (base nueva, variables de Vercel, dominio) y backup diario. Fase 1: `empresa_id` en todas las tablas de
  negocio + **Row Level Security** de Postgres con `SET app.empresa_id` por request (o esquema por
  empresa; RLS es más simple de operar en Neon), `usuarios` asociados a una empresa, unicidades por
  empresa (`codigo`, `ruc`, numeraciones), alta de empresas, planes y límites (usuarios, cajas,
  documentos SIFEN por mes), suspensión por falta de pago, panel de super-admin; tests de aislamiento
  (un usuario nunca ve datos de otra empresa). Certificados SIFEN por empresa, cifrados.
- **Impacto para vender:** es el modelo de negocio. Se pone en P2 porque la fase 0 permite vender ya con
  una instalación por cliente, y porque la fase 1 exige antes 3.1-K.
- **Esfuerzo:** L+ · **Prioridad:** P2 · **Líder:** Backend (QA: pruebas de aislamiento).
- **Dependencias:** 3.1-K y 3.1-N (QA), REL-03, REL-34.
- **Fuente:** pedido del dueño; `ESTADO-DEL-PROYECTO.md` 3.3 y 4 (punto 21).

#### REL-20 · Presupuestos a clientes

- **Problema:** el contratista pide precio por una lista de materiales. Hoy solo hay "cotizaciones de
  proveedores" (compra). Se le pasa el precio por WhatsApp a mano y si acepta hay que cargar todo de nuevo.
- **Propuesta (simple):** "Presupuesto" con validez (por ejemplo 7 días), que se imprime o se manda por
  WhatsApp/PDF. Si el cliente acepta, con un clic pasa a la caja como venta o a un pedido con entrega.
- **Propuesta (técnica):** `presupuestos_cliente` + ítems, estados `BORRADOR` → `ENVIADO` →
  `ACEPTADO`/`RECHAZADO`/`VENCIDO` → `CONVERTIDO`; precios de `PrecioService` (REL-07) congelados;
  `convertir_en_venta` y `convertir_en_pedido` validando stock en ese momento; numeración `PRE-`.
  Renombrar en pantalla "Cotizaciones de proveedores" para que no se confunda.
- **Impacto para vender:** medio-alto con contratistas y constructoras.
- **Esfuerzo:** M · **Prioridad:** P2 · **Líder:** Backend.
- **Dependencias:** REL-07, REL-11.
- **Fuente:** competencia — ERPNext (Quotation → Sales Order, [N1]), Odoo POS presupuestos ([O1]);
  `analisis-requerimientos.md` #12.

#### REL-21 · Compra sugerida por mínimo y máximo

- **Problema:** el sistema avisa "stock bajo", pero no dice cuánto comprar ni a quién. El encargado arma
  los pedidos al proveedor a mano.
- **Propuesta (simple):** pantalla "Qué comprar": lo que está bajo el mínimo, cuánto pedir para llegar al
  máximo (descontando lo que ya está pedido), agrupado por proveedor con su mejor precio, y un botón que
  genera las órdenes de compra en borrador.
- **Propuesta (técnica):** `productos.stock_maximo` y `proveedor_preferido_id`; `ReposicionService`:
  `max − (stock + pendiente en OC abiertas)`, redondeado al `factor_conversion` (REL-14); OC en
  `BORRADOR` por proveedor (requiere `proveedor_id` en la OC, sugerido en 3.1-M); sugerencia opcional por
  ventas de los últimos N días.
- **Impacto para vender:** medio; el dueño lo nota en plata (menos faltantes y menos sobrestock).
- **Esfuerzo:** M · **Prioridad:** P2 · **Líder:** Backend.
- **Dependencias:** 3.1-A y 3.1-M (QA), REL-14.
- **Fuente:** competencia — Odoo reglas mín/máx ([O2]); `analisis-requerimientos.md` #10.

#### REL-22 · Cuenta corriente completa

- **Problema:** se puede vender a cuenta y cobrar, pero al cobrar **no se emite recibo**, no hay estado de
  cuenta para imprimir o mandar, no hay plazo ni vencimiento por cliente (solo antigüedad), un cobro
  equivocado no se puede anular y los cobros no aparecen en ningún reporte. Los cobros con cheque o
  transferencia no pasan por la caja.
- **Propuesta (simple):** recibo numerado e imprimible en cada cobro; estado de cuenta en PDF/WhatsApp;
  plazo por cliente (30, 60 días) con lista de vencidos; anular un cobro (con motivo y permiso);
  recordatorio de deuda por WhatsApp; "saldo a favor" (de devoluciones, REL-05) que se usa en la próxima
  compra.
- **Propuesta (técnica):** `recibos` (número `REC-`, cliente, medios, imputación a ventas: FIFO
  automático o manual); `clientes.plazo_dias`; tipo `ANULACION` en `movimientos_cuenta_corriente`;
  reporte de cobranzas por período y medio; enlace `wa.me` con texto armado; todos los cobros quedan
  vinculados al turno (aunque no sean efectivo) para el cierre por medio (REL-08). Con REL-01: la venta a
  cuenta es factura crédito.
- **Impacto para vender:** medio-alto; el fiado es central en ferreterías de barrio y con contratistas.
- **Esfuerzo:** M · **Prioridad:** P2 · **Líder:** Backend (Frontend: recibo y estado de cuenta).
- **Dependencias:** REL-08.
- **Fuente:** prueba propia — `20-cuenta-corriente-modal.png`, `21-cobro-registrado.png`;
  `ESTADO-DEL-PROYECTO.md` 3.3 (fila "Cuenta corriente").

#### REL-23 · Reportes para el dueño y el contador

- **Problema:** hay un solo reporte (ventas de mostrador del período). Faltan: ventas por vendedor, por
  caja, por categoría; margen real (hoy usa el costo actual, no el del momento de la venta); productos sin
  movimiento; valor del inventario; cobranzas; devoluciones; y lo que pide el contador (ventas por tasa de
  IVA, registro de comprobantes). No se puede exportar a Excel.
- **Propuesta (simple):** un tablero del dueño (hoy / semana / mes) y reportes con filtros y botón
  "Exportar a Excel". Para el contador: "Libro de ventas" con totales por tasa de IVA y el archivo para el
  registro mensual de comprobantes.
- **Propuesta (técnica):** guardar `costo_unitario` en `venta_mostrador_items` al vender (último costo o
  promedio ponderado actualizado en la recepción); `ReporteService` con consultas agregadas
  (vendedor, caja, categoría, sin movimiento > 90 días, valorización, cobranzas); exportación XLSX/CSV
  común; exportación del registro de comprobantes según el formato de Marangatu (RG 90/2021) cuando el
  contador confirme el formato.
- **Impacto para vender:** medio-alto; el dueño compra "saber cuánto gana".
- **Esfuerzo:** M · **Prioridad:** P2 · **Líder:** Backend (Frontend: migrar reportes a Fluent, etapa 3d).
- **Dependencias:** REL-02, REL-09; 3.1-I y 3.1-L (QA).
- **Fuente:** normativa — [RG 90/2021 (registro de comprobantes en Marangatu)](https://www.dnit.gov.py/web/portal-institucional/w/resolucion-general-n-90-21);
  prueba propia — `p-demo-esc-reportes.png`; `ESTADO-DEL-PROYECTO.md` 3.3 (fila "Reportes").

#### REL-24 · Caja más rápida

- **Problema:** la venta básica es ágil (escaneo, Enter, F9), pero hay fricciones medidas en el
  recorrido:
  - Para vender 12 bulones hay que agregar uno y después salir del buscador e ir al campo cantidad.
  - Después de cada venta aparece un diálogo para imprimir o cerrar (un paso más por venta).
  - No se puede dejar una venta "en espera" para atender a otro cliente.
  - El descuento es solo un % global (no por línea ni en monto).
  - El efectivo no se redondea: aparecen totales como Gs. 18.731 o Gs. 6.015.719.
  - El ticket no muestra "Paga con" ni el vuelto.
  - El error de stock insuficiente aparece abajo a la derecha, lejos de la línea.
- **Propuesta (simple):** escribir `12*` antes del código para la cantidad; opción "imprimir ticket
  siempre / nunca / preguntar"; botón "Poner en espera" con lista de ventas en espera; descuento por línea
  y en Gs. (con el tope por rol que agrega QA en 3.1-G); redondeo del total en efectivo a 50/100 Gs.
  (configurable); "Paga con" y vuelto en el ticket; marcar la línea sin stock en el carrito.
- **Propuesta (técnica):** parser del buscador (`/^(\d+(?:[.,]\d+)?)\*(.+)$/`); preferencia de impresión
  por usuario o caja; ventas en espera en `localStorage` o como `VentaMostrador` en `BORRADOR` (mejor en
  el servidor si hay preventa, REL-09); `descuento_monto` por ítem en el schema; regla de redondeo en
  `empresa` aplicada en el backend con línea "Redondeo".
- **Impacto para vender:** medio; se nota en cada venta.
- **Esfuerzo:** S (cada punto) · **Prioridad:** P2 · **Líder:** Frontend (Backend: descuento por línea y
  redondeo).
- **Dependencias:** 3.1-G (tope de descuento, QA).
- **Fuente:** prueba propia — `04-caja-carrito.png`, `05-caja-venta-registrada.png`, `06-ticket.png`,
  `11-caja-sin-stock.png`; mercado — [Yo Facturo: montos en guaraníes sin decimales](https://yo-facturo.com/blog/sistema-de-ventas-punto-de-venta-paraguay/).

#### REL-25 · Caja y listas usables en celular y tablet

- **Problema:** en el celular (390 px) la caja mide 2.400 px de alto: el botón **Cobrar queda en la
  posición 1.082 px**, fuera de la pantalla, debajo del carrito, del cliente y de los medios de pago. En
  el carrito se corta la columna de precio y el nombre del producto se parte en 4 líneas. Las pantallas
  viejas (pedidos, envíos, compras) cortan columnas (no se ve el estado ni el total). Las 6 tarjetas de
  totales del turno ocupan casi una pantalla entera.
- **Propuesta (simple):** en celular y tablet, la caja muestra arriba el buscador, el carrito en
  tarjetas y una **barra fija abajo con el total y el botón Cobrar**; el cobro se abre en un panel. Los
  totales del turno se ocultan para el vendedor (ver REL-10). Las tablas se muestran como tarjetas.
- **Propuesta (técnica):** media queries en `punto-venta.js`/`styles.css` con tokens de Fluent; barra
  `position: sticky; bottom: 0`; `tabla.js` con modo tarjeta bajo 600 px; migrar a Fluent las pantallas de
  la etapa 3c.
- **Impacto para vender:** medio; muchas ferreterías chicas usan tablet o celular en el mostrador, y es
  lo primero que se prueba en una demo en el teléfono del dueño.
- **Esfuerzo:** S · **Prioridad:** P2 · **Líder:** Frontend.
- **Dependencias:** etapa 3c de Fluent.
- **Fuente:** prueba propia — `13-caja-celular.png`, `p-demo-cel-caja.png`, `p-demo-cel-pedidos.png`.

#### REL-26 · Consignación

- **Problema:** otra tienda vende mercadería de la ferretería y paga lo vendido quedándose un porcentaje.
  Hoy no hay forma de saber qué stock está en poder de cada consignatario, cuánto vendió ni cuánto debe.
- **Propuesta (simple):** "Enviar en consignación" a un consignatario (con nota de remisión con motivo
  consignación); su stock se ve aparte. Cada mes (o cuando informe) se carga la **liquidación**: lo vendido
  se factura al consignatario menos su comisión, lo devuelto vuelve al depósito y lo que queda sigue allá.
  Cuenta corriente del consignatario.
- **Propuesta (técnica):** consignatario = cliente con `es_consignatario` y `% comision` (por defecto,
  con excepción por producto); ubicación de stock por consignatario (sale gratis si se hace REL-30
  "depósitos"; si no, tabla `stock_consignacion`); documentos `ENVIO_CONSIGNACION` (remisión, motivo
  consignación) y `LIQUIDACION_CONSIGNACION` (vendido → venta/factura al consignatario; devuelto →
  reingreso); kardex con esos tipos; reporte de stock en consignación y antigüedad.
- **Impacto para vender:** medio; diferencial frente a sistemas genéricos, pedido del dueño.
- **Esfuerzo:** L · **Prioridad:** P2 · **Líder:** Backend.
- **Dependencias:** REL-12 (remisión), REL-30 (depósitos) o tabla propia, REL-22, REL-01. Validar con el
  contador cómo se factura (la comisión del consignatario lleva IVA según un dictamen de la DNIT).
- **Fuente:** pedido del dueño; normativa — [DNIT: dictamen sobre comisiones y logística](https://www.dnit.gov.py/web/portal-institucional/w/alcance-de-disposiciones-tributarias-respecto-a-operaciones-comerciales-y-servicios-de-logistica-),
  [Yo Facturo: motivos de traslado de la nota de remisión (incluye consignación)](https://yo-facturo.com/blog/nota-de-remision-paraguay/).

#### REL-27 · Auditoría de acciones sensibles

- **Problema:** no queda registro de quién cambió un precio, quién dio un descuento, quién anuló o
  devolvió, quién cambió el límite de crédito o quién cerró la caja con faltante. Para el dueño es tan
  importante como el arqueo.
- **Propuesta (simple):** "Historial de cambios" donde el dueño ve, por fecha y usuario, los cambios de
  precio, descuentos sobre un %, devoluciones, ajustes de stock, cambios de crédito y cierres con
  diferencia.
- **Propuesta (técnica):** tabla `auditoria` (usuario, acción, entidad, id, antes/después en JSON, IP,
  fecha) escrita por los servicios (no por triggers, para tener el usuario); filtro y exportación; alertas
  configurables (descuento > X %, diferencia de caja > Y).
- **Impacto para vender:** medio; argumento fuerte con dueños que no están todo el día.
- **Esfuerzo:** M · **Prioridad:** P2 · **Líder:** Backend.
- **Dependencias:** 3.1-G (tope de descuento, QA).
- **Fuente:** prueba propia (no hay registro de cambios de precio de producto ni de cierres); buena
  práctica de POS.

#### REL-28 · Control de margen (precio bajo costo)

- **Problema:** se pudo crear un producto con costo Gs. 10.000 y precio de venta Gs. 5.000 (margen −50 %)
  sin ningún aviso.
- **Propuesta (simple):** avisar al guardar un precio menor al costo o con margen menor al mínimo de la
  empresa, y marcarlo en la lista de productos.
- **Propuesta (técnica):** `empresa.margen_minimo`; validación con advertencia (requiere confirmación) en
  `ProductoService` y en la actualización masiva (REL-04); filtro "margen bajo" en productos.
- **Impacto para vender:** bajo-medio; evita pérdidas silenciosas.
- **Esfuerzo:** S · **Prioridad:** P2 · **Líder:** Backend.
- **Dependencias:** ninguna.
- **Fuente:** prueba propia — `api1.py` ("Prueba bajo costo", margen −50 % aceptado).

### P3 — más adelante o cuando haya demanda

#### REL-29 · Versión instalada en Windows con licencia perpetua

- **Problema:** hay ferreterías con mala conexión o que prefieren pagar una vez. Hoy SAIL solo corre en
  la nube (Vercel + Neon).
- **Propuesta (simple):** instalador para Windows que deja todo listo en la PC del local (base de datos,
  servidor y acceso desde el navegador de las otras PCs de la red), con copias de seguridad automáticas,
  licencia perpetua y actualizaciones opcionales pagas.
- **Propuesta (técnica):** como dice el roadmap: Inno Setup, Python embebido, PostgreSQL local, servicios
  con WinSW, backup programado (`pg_dump` rotativo, a disco externo o nube), **licencia firmada**
  (Ed25519, verificación sin conexión, ligada al RUC y a la cantidad de cajas), canal de actualizaciones
  con migraciones automáticas. Importante: **SIFEN necesita internet** para transmitir; definir la cola
  offline con reenvío y verificar con la DNIT los plazos y la modalidad de contingencia.
- **Impacto para vender:** medio; abre otro segmento, pero duplica el soporte.
- **Esfuerzo:** L+ · **Prioridad:** P3 · **Líder:** Backend (QA: pruebas de instalación y actualización).
- **Dependencias:** REL-01 (cola offline), 3.1-N (migraciones confiables).
- **Fuente:** pedido del dueño; `ESTADO-DEL-PROYECTO.md` 4 (punto 22).

#### REL-30 · Varias sucursales y depósitos

- **Problema:** un solo stock por producto. Una ferretería con depósito aparte o con dos locales no puede
  saber dónde está cada cosa ni transferir.
- **Propuesta (simple):** sucursales y depósitos; stock por ubicación; transferencias con nota de
  remisión; cada caja pertenece a una sucursal.
- **Propuesta (técnica):** `sucursales`, `depositos`, `stock_por_deposito` (el `stock_actual` pasa a ser
  la suma o se reemplaza), movimientos con depósito origen/destino, transferencias `TRF-` con remisión
  (motivo "traslado entre locales"), establecimiento SIFEN por sucursal.
- **Impacto para vender:** medio con cadenas chicas; base de REL-15 y REL-26 si se hace antes.
- **Esfuerzo:** L · **Prioridad:** P3 · **Líder:** Backend.
- **Dependencias:** REL-09, 3.1-K.
- **Fuente:** competencia (multibodega en Bsale, transferencias en Loyverse inventario avanzado, Odoo);
  `analisis-requerimientos.md` #26.

#### REL-31 · App para el celular (PWA): preventa y consulta de stock

- **Problema:** el vendedor en el salón o el dueño fuera del local no tienen una app; la web en el celular
  es incómoda (REL-25).
- **Propuesta (simple):** "instalar" SAIL en el celular desde el navegador: consultar precio y stock
  escaneando con la cámara, armar una preventa que el cajero cobra, y ver las ventas del día.
- **Propuesta (técnica):** `manifest.webmanifest` + service worker (sin build), lector de códigos con la
  cámara (`BarcodeDetector` donde exista, o una librería), vista móvil de preventa contra el endpoint de
  REL-09.
- **Impacto para vender:** medio; "tiene app" es un argumento de venta frecuente.
- **Esfuerzo:** M · **Prioridad:** P3 · **Líder:** Frontend.
- **Dependencias:** REL-25, REL-09 (preventa).
- **Fuente:** competencia (apps móviles de Loyverse y Odoo).

#### REL-32 · Integración con POS y QR de Bancard

- **Problema:** el cajero tipea el monto en el POS de la tarjeta o muestra un QR estático y después lo
  vuelve a cargar en SAIL: doble carga y errores.
- **Propuesta (simple):** al elegir "QR" o "Tarjeta", SAIL manda el monto al POS o genera el QR con el
  monto, y la venta se confirma sola cuando se aprueba el pago.
- **Propuesta (técnica):** investigar las APIs de Bancard (y Dinelco) para comercios y el **QR Hub del
  BCP** (en pruebas en 2026); webhook de confirmación; referencia automática en `venta_pagos`.
- **Impacto para vender:** medio; diferencial, pero depende de acuerdos comerciales con las redes.
- **Esfuerzo:** L · **Prioridad:** P3 · **Líder:** Backend.
- **Dependencias:** REL-08.
- **Fuente:** mercado — [ABC: Paraguay prueba el QR Hub](https://www.abc.com.py/negocios/2026/08/06/paraguay-ultimo-en-facturar-bueno-en-pagar-con-qr-y-ya-prueba-el-qr-hub/),
  [BCP: nueva identidad del Sistema de Pagos](https://www.bcp.gov.py/es/web/institucional/w/el-banco-central-del-paraguay-impulsa-la-innovacion-con-una-nueva-identidad-del-sistema-de-pagos-del-paraguay-1).

#### REL-33 · Menú y pantallas según lo que el rol puede hacer

- **Problema:** el usuario de **depósito** ve en el menú "Caja", "Pedidos de clientes", "Clientes" y
  "Cuentas por cobrar", entra a la caja y ve el punto de venta completo con los totales del turno (aunque
  el backend le rechaza la venta: 403). Confunde y muestra información de caja a quien no la maneja.
- **Propuesta (simple):** cada rol ve en el menú lo que usa en su trabajo; lo de solo consulta queda en
  un grupo aparte o se oculta.
- **Propuesta (técnica):** en `layout.js`, filtrar por permiso de escritura además de lectura para los
  módulos operativos; en `caja.html`, sin permiso de caja mostrar solo el estado.
- **Impacto para vender:** bajo; mejora la primera impresión.
- **Esfuerzo:** S · **Prioridad:** P3 · **Líder:** Frontend.
- **Dependencias:** ninguna.
- **Fuente:** prueba propia — `p-deposito-esc-caja.png`, `30-inicio-deposito.png`.

#### REL-34 · Protección de datos personales (Ley 7593/2025)

- **Problema:** SAIL guarda datos de clientes (nombre, cédula/RUC, teléfono, dirección, deudas). La Ley
  7593/2025 fue promulgada en noviembre de 2025 y entraría en vigor tras su reglamentación (prevista para
  2027). Como SaaS, seremos **encargados del tratamiento** de los datos de los clientes de cada
  ferretería.
- **Propuesta (simple):** poder exportar y borrar (o anonimizar) los datos de un cliente que lo pida,
  registrar quién accede a datos sensibles y tener un contrato/política de privacidad para el SaaS.
- **Propuesta (técnica):** endpoint de exportación por cliente; anonimización que respete lo que la ley
  tributaria obliga a conservar (facturas); auditoría (REL-27); cifrado de backups; texto de términos y
  privacidad.
- **Impacto para vender:** bajo hoy, necesario antes de 2027 para clientes medianos.
- **Esfuerzo:** S · **Prioridad:** P3 · **Líder:** Backend.
- **Dependencias:** REL-19, REL-27.
- **Fuente:** normativa — [Ferrere: Paraguay adopta su ley de protección de datos](https://ferrere.com/es/novedades/paraguay-adopta-su-ley-de-proteccion-de-datos-personales/),
  [IAPP](https://iapp.org/news/a/paraguay-da-un-paso-hacia-un-marco-moderno-de-protecci-n-de-la-privacidad).

---

## 4. Lo que funcionó bien en el recorrido (para no romperlo)

- **Caja con lector:** escanear el mismo código dos veces suma la cantidad; Enter agrega; F9 cobra; total
  y vuelto en vivo. La venta completa en efectivo se hizo sin mouse.
- **Pago mixto** claro ("Resta cobrar") y **venta a cuenta** con mensajes buenos: "Juan Benítez supera su
  límite de crédito: le quedan Gs. 1.154.250 disponibles".
- El vendedor **no puede cambiar el precio** (campo de solo lectura con explicación) ni el límite de
  crédito (403 con mensaje claro).
- **Cuentas por cobrar** con antigüedad de deuda y cobro en un clic ("Cobro registrado. Todavía debe
  Gs. 245.750").
- Pantallas Fluent rápidas con la demo (todas cargan en ~0,6 s en local) y **sin scroll horizontal** en
  celular en ninguna pantalla; sin errores de JavaScript en el recorrido.

---

## 5. Errores nuevos para QA

No están en `ESTADO-DEL-PROYECTO.md` 3.1. Reproducidos contra la rama de integración (`7c7fdd0` /
`985654f`) con la demo cargada (`SEED_DEMO=true`). En la API, `TOKEN_*` = token de `POST /auth/login`
del usuario indicado.

### QA-N1 · Se vende media unidad de un producto que se vende por pieza (Media)

- **Qué pasa:** la caja y la API aceptan cantidades con decimales en productos por pieza. El stock queda
  fraccionado ("Alicate universal 8": 7,5 pz) y el reporte muestra "24.5" alicates vendidos.
- **Pasos (pantalla):** entrar como `vendedor@sail.local` → Caja → escanear `PROD-00019` (alicate,
  unidad `pz`) → en Cantidad escribir `0.5` → Cobrar. Se registra la venta.
- **Pasos (API):** `POST /api/v1/caja/ventas` con `{"items":[{"producto_id":1,"cantidad":0.333,"precio_unitario":56250}],"pagos":[{"metodo":"EFECTIVO","monto":18731}],"metodo_pago":"EFECTIVO"}` → 201.
- **Esperado:** 422 "Este producto se vende por unidad entera" cuando la unidad no admite decimales.
- **Arreglo sugerido:** mientras se hace REL-14, rechazar decimales si `unidad_medida` ∈ {pz, unidad,
  caja, bolsa, lata, balde, rollo} en caja, pedidos y envíos; en el frontend, `step="1"` para esas
  unidades. Captura: `12-caja-medio-alicate.png`.

### QA-N2 · Ids de referencia que no existen devuelven error 500 (Media)

- **Qué pasa:** al mandar un id inexistente en un campo que referencia a otra tabla, la base rechaza la
  clave foránea y la API responde **500** (sin CORS, el navegador lo muestra como "No se pudo conectar
  con el servidor").
- **Pasos (API, todos dan 500):**
  - `POST /caja/ventas` con `"cliente_id": 9999` (TOKEN_vendedor).
  - `POST /pedidos-cliente` con `"cliente_id": 9999`.
  - `POST /productos` con `"categoria_id": 9999` (TOKEN_deposito).
  - `POST /proveedor-productos` con `"proveedor_id": 9999` (TOKEN_admin).
- **Esperado:** 404 "Cliente no encontrado" (o 422).
- **Relación:** misma raíz que **3.1-F** (no se captura `IntegrityError`), pero es otro caso (clave
  foránea, no duplicado). Verificar que el arreglo de 3.1-F lo cubra y validar la existencia en los
  servicios.

### QA-N3 · Un producto desactivado se puede seguir vendiendo y pidiendo (Baja)

- **Qué pasa:** el buscador de la caja oculta los productos inactivos, pero el backend no lo controla:
  una venta o un pedido por id lo aceptan.
- **Pasos (API):** `PUT /productos/{id}` con `"activo": false` (TOKEN_admin) → `GET
  /productos/buscar?q=<codigo>` no lo devuelve (bien) → `POST /caja/ventas` con ese `producto_id` → **201**;
  `POST /pedidos-cliente` con ese producto → **201**.
- **Esperado:** 409/422 "El producto está desactivado".
- **Arreglo sugerido:** validar `producto.activo` en `CajaService.registrar_venta` y en
  `PedidoClienteService.crear/actualizar`.

### QA-N4 · El mensaje de stock insuficiente mezcla formatos de número (Baja)

- **Qué pasa:** al cobrar más de lo que hay, el aviso dice **"Disponible: 18.000, requerido: 50.0"**. En
  Paraguay "18.000" se lee dieciocho mil; además una cantidad lleva punto de miles y la otra punto decimal.
- **Pasos:** Caja → `PROD-00018` (destornillador, stock 18) → cantidad `50` → Cobrar. Captura
  `11-caja-sin-stock.png`.
- **Esperado:** "Stock insuficiente para Destornillador Phillips PH2: hay 18 pz y se pidieron 50 pz."
- **Arreglo sugerido:** formatear las cantidades del mensaje en el backend sin ceros decimales y con la
  unidad (o devolver los números en campos aparte y que el frontend los formatee con `formatoCantidad`).

### QA-N5 · Productos e Inventario se congelan con un catálogo de tamaño real (Alta para la venta)

- **Qué pasa:** con 12.000 productos y 2.000 clientes, Productos tarda ~12 s y Inventario ~25 s en quedar
  usables en escritorio; con la CPU del celular simulada (4× más lenta) la pantalla no responde un clic en
  30 s. `GET /productos` y `GET /inventario/stock` devuelven 3,3 MB.
- **Pasos:** sobre una base de prueba con la demo, cargar datos masivos:
  ```sql
  INSERT INTO productos (categoria_id,codigo,nombre,precio_compra,precio_venta,stock_actual,stock_minimo,unidad_medida,activo)
  SELECT 1+(g%6),'MASIVO-'||g,'Artículo de prueba '||g,1000+g,1250+g,10,2,'pz',true FROM generate_series(1,12000) g;
  INSERT INTO clientes (nombre,activo,limite_credito) SELECT 'Cliente prueba '||g,true,0 FROM generate_series(1,2000) g;
  ```
  Entrar como admin y abrir `productos.html` e `inventario.html`.
- **Esperado:** pantalla usable en menos de 2 s.
- **Arreglo:** es el ítem **REL-03** del backlog (paginación en el servidor). Se lista también acá para
  que QA lo convierta en una prueba de rendimiento que no se vuelva a romper.

---

## 6. Competencia y estándar del rubro

### En Paraguay

| Sistema | Qué ofrece (según su web o notas) | Precio publicado |
|---|---|---|
| [FactPy](https://factpy.com/) | POS web con caja, stock y facturación SIFEN integrada; API de facturación para desarrolladores. | No encontrado |
| [Facturazzi](https://facturazzi.com.py/) | Emisión automática de factura electrónica integrada con DNIT/Marangatu, gestión financiera; testimonio de una ferretería de Asunción. | No encontrado |
| [Alysoft](https://www.alysoft.net/) | ERP paraguayo que nombra ferreterías: inventario, cajas, facturación electrónica. | Planes mensuales en Gs. (no se pudo leer el monto) |
| [eVENDÉ](https://www.evende.com.py/) | "100 % paraguayo": stock, caja y bancos, libros IVA. | Planes por comercio (no se pudo leer el monto) |
| [Yo Facturo](https://yo-facturo.com/py/) | Gestión, stock y punto de venta con SIFEN: FE, autofactura, NC, ND y nota de remisión electrónicas con KuDE y QR; usa el certificado del contribuyente. Habilitando los primeros clientes (oct/2026). | "Un mes gratis"; montos no publicados en lo indexado |
| [TPV](https://tpv.com.py/), [Digitalpy](http://www.d-py.com/Sistema-software-Informatico-de-Facturacion-y-control-de-stock-Paraguay.html) | Facturación y control de stock y caja (páginas con varios años). | No encontrado |
| [e-Kuatia'i (DNIT)](https://www.dnit.gov.py/web/e-kuatia) | **Facturador gratuito** de la DNIT para pequeños contribuyentes con un establecimiento y un punto de expedición (RG 06/2024). No tiene stock ni caja. | Gratis |
| Odoo + [localización PY](https://apps.odoo.com/apps/modules/18.0/l10n_xma_einvoice_py) | ERP completo con módulo de factura electrónica paraguaya de terceros. | Ver abajo |

**Lectura:** en Paraguay **todos los competidores venden "facturación electrónica + stock + caja"**; el
SIFEN es la entrada al mercado. Ninguno muestra (en lo encontrado) funciones específicas de ferretería
como fraccionamiento con conversión, listas por tipo de cliente, consignación o logística con estados de
pago: ahí está el espacio de SAIL. Los precios no son públicos: conviene que el dueño consiga cotizaciones
(ver preguntas).

### En la región (referencia de funciones y precios)

| Sistema | Funciones relevantes | Precio de referencia |
|---|---|---|
| Odoo (POS + Inventario) | Escáner con precio/peso en el código, listas de precios por cliente, presupuestos, devoluciones con referencia, mín/máx, unidades de compra/venta, multi-depósito. | Standard ~US$ 25–31 por usuario/mes; Custom ~US$ 49–61 ([ERP Research](https://www.erpresearch.com/pricing/odoo), [Swell](https://www.swell.is/content/odoo-pricing)); implementación aparte. |
| Loyverse | POS gratis; inventario avanzado (órdenes de compra, transferencias entre tiendas, valorización) y gestión de empleados como agregados. | Inventario avanzado ~US$ 25/mes; empleados ~US$ 5/mes ([TechnologyAdvice](https://technologyadvice.com/products/loyverse-pos-reviews/), [xpay](https://www.xpay.sh/saas-pricing/loyverse-pos/)). |
| Alegra POS | Varias listas de precios (mayorista, minorista, crédito, contado), IVA por referencia, unidades variables (metro, rollo, caja). | Desde ~US$ 29,99 ([Capterra](https://www.capterra.es/software/1024697/alegra-pos)). |
| Bsale (Chile) | Multibodega/multisucursal, listas de precios, boletas y notas de crédito. | Conector Shopify US$ 20–60/mes ([Shopify App Store](https://apps.shopify.com/bsale?locale=es)); POS por cotización. |
| Shopify POS | Multi-sucursal. | ~US$ 89/mes por sucursal adicional ([Shopify](https://shopify.com/co/pos/precios)). |
| Epicor Eagle (EE. UU.) | Referente de ferretería: velocidad de mostrador, encargos especiales, cuentas de contratistas. | Por cotización ([E1] en `analisis-requerimientos.md`). |

**Estándar del rubro que SAIL todavía no cubre:** listas de precios (REL-07), unidades con conversión y
fraccionamiento (REL-14), códigos de barras múltiples, balanza y etiquetas (REL-16), presupuestos
(REL-20), devoluciones (REL-05), compra sugerida (REL-21), multi-sucursal (REL-30), app móvil (REL-31),
importación desde Excel (REL-04) y, en Paraguay, SIFEN (REL-01).

---

## 7. Fuentes

### Normativa y mercado de Paraguay

- DNIT — [Designa nuevos facturadores electrónicos (RG 52/2026)](https://www.dnit.gov.py/web/portal-institucional/w/dnit-designa-nuevos-facturadores-electr%C3%B3nicos) ·
  [texto de la RG 52/2026 (impuestospy)](https://impuestospy.com/impuestos/resolucion-general-dnit-n-52-2026/):
  calendario por grupos (I: 1/6/2026 · II: 1/9/2026 · III: 1/12/2026 · IV: 2/3/2027 · V: 1/6/2027 ·
  VI: 1/9/2027), ~3.000 contribuyentes, vencimiento de timbrados preimpresos/autoimpresos, aviso por
  buzón Marandu. Confirmar en el anexo el grupo de cada cliente.
- DNIT — [Obligatoriedad para proveedores del Estado (RG 41/2025, desde 2/1/2026)](https://www.dnit.gov.py/web/portal-institucional/w/dnit-establece-obligatoriedad-de-adhesi%C3%B3n-al-sifen-para-proveedores-del-estado).
- DNIT — [Paraguay supera los 50.000 facturadores electrónicos](https://www.dnit.gov.py/web/e-kuatia/w/paraguay-supera-los-50.000-facturadores-electr%C3%B3nicos-y-avanza-en-la-digitalizaci%C3%B3n-tributaria) ·
  [portal e-Kuatia](https://www.dnit.gov.py/web/e-kuatia) · [noticias e-Kuatia (e-Kuatia'i gratuito, RG 06/2024)](https://www.dnit.gov.py/web/e-kuatia/listado-de-noticias).
- DNIT — [Preguntas frecuentes e-Kuatia: cancelación 48 h (FE) / 168 h (otros DTE)](https://www.dnit.gov.py/web/e-kuatia/preguntas-frecuentes/-/categories/367812) ·
  [web services del SIFEN](https://www.dnit.gov.py/web/e-kuatia/preguntas-frecuentes/-/categories/400201).
- SET — [Manual Técnico SIFEN v150](https://tdn.totvs.com.br/download/attachments/502840885/MT_E_Kuatia_V150_24_06_2019.pdf?api=v2) (versión vigente según la DNIT).
- Yo Facturo (proveedor privado; verificar con la DNIT) — [Guía SIFEN: CDC de 44 dígitos, KuDE con QR, transmisión en 72 h](https://yo-facturo.com/blog/facturacion-electronica-paraguay-sifen/) ·
  [Nota de remisión y motivos de traslado](https://yo-facturo.com/blog/nota-de-remision-paraguay/) ·
  [IVA 10 % y 5 %](https://yo-facturo.com/blog/iva-paraguay-10-5-como-calcular/) ·
  [Validador de RUC (módulo 11)](https://yo-facturo.com/herramientas/validador-ruc-paraguay/) ·
  [Qué debe tener un POS en Paraguay](https://yo-facturo.com/blog/sistema-de-ventas-punto-de-venta-paraguay/).
- IVA — [La Nación (jul/2026): IVA en Paraguay](https://www.lanacion.com.py/negocios/2026/07/17/iva-en-paraguay-el-impuesto-que-esta-presente-en-casi-todas-las-compras/) ·
  [PwC: reforma tributaria Ley 6380/2019](https://periscopiofiscalylegal.pwc.es/paraguay-reforma-tributaria-para-el-ano-2020/).
- Registro de comprobantes — [RG 90/2021](https://www.dnit.gov.py/web/portal-institucional/w/resolucion-general-n-90-21) ·
  [RG 132/2023](https://www.dnit.gov.py/web/portal-institucional/w/resolucion-general-n-132/23).
- Traslado de mercaderías — [ABC (feb/2025)](https://www.abc.com.py/economia/2025/02/28/estos-son-los-requisitos-de-la-dnit-para-trasladar-mercaderias-dentro-del-territorio/) ·
  [DNIT refuerza controles](https://www.dnit.gov.py/web/portal-institucional/w/dnit-refuerza-controles-para-disminuir-evasion-e-informalidad).
- Consignación — [DNIT: dictamen sobre comisiones y logística](https://www.dnit.gov.py/web/portal-institucional/w/alcance-de-disposiciones-tributarias-respecto-a-operaciones-comerciales-y-servicios-de-logistica-).
- Pagos — [Última Hora (jul/2026): QR 55 % de los pagos electrónicos](https://www.ultimahora.com/el-metodo-qr-avanza-y-acapara-el-55-de-los-pagos-electronicos) ·
  [La Nación: 7 de cada 10 pagos con el celular](https://www.lanacion.com.py/negocios/2025/12/22/en-paraguay-7-de-cada-10-pagos-se-realizan-con-el-celular/) ·
  [BCP: límite de transferencias instantáneas Gs. 10 millones](https://www.bcp.gov.py/web/institucional/w/bcp-actualiza-el-reglamento-del-sipap-y-eleva-el-limite-de-las-transferencias-instantaneas-a-g-10-millones) ·
  [ABC: SIPAP pasa a llamarse SIP](https://www.abc.com.py/negocios/2026/04/27/bcp-rebautiza-sipap-que-ahora-se-llama-sip-en-que-afecta-a-los-usuarios/) ·
  [ABC: QR Hub en pruebas](https://www.abc.com.py/negocios/2026/08/06/paraguay-ultimo-en-facturar-bueno-en-pagar-con-qr-y-ya-prueba-el-qr-hub/) ·
  [Infonegocios: Tigo Money y Bancard](https://infonegocios.com.py/y-ademas/el-futuro-es-qr-tigo-money-y-bancard-se-unen-para-revolucionar-el-mercado-paraguayo) ·
  [La Nación: Dinelco y Tigo Money](https://www.lanacion.com.py/negocios_edicion_impresa/2023/12/08/dinelco-y-tigo-money-se-unen-para-revolucionar-los-pagos-en-paraguay/) ·
  [Yo Facturo: Tigo Money para negocios](https://yo-facturo.com/blog/tigo-money-para-negocios/).
- Dólares — [Yo Facturo: dólar a guaraní y facturas en moneda extranjera](https://yo-facturo.com/blog/dolar-a-guarani-como-convertir/) ·
  [Infobae/EFE (ago/2026): el guaraní se aprecia más de 10 %](https://www.infobae.com/america/agencias/2026/08/03/la-moneda-paraguaya-se-aprecia-mas-de-un-10-frente-al-dolar-en-lo-que-va-de-2026/).
- Datos personales — [Ferrere: Ley 7593/2025](https://ferrere.com/es/novedades/paraguay-adopta-su-ley-de-proteccion-de-datos-personales/) ·
  [IAPP](https://iapp.org/news/a/paraguay-da-un-paso-hacia-un-marco-moderno-de-protecci-n-de-la-privacidad).
- Códigos de balanza — [GS1](https://gs1.se/en/guides/how-to-guides/barcode-label-items-of-varying-weight/).

**Lo que no se pudo confirmar en fuentes oficiales** (preguntar al contador): qué cotización usar en
comprobantes en moneda extranjera; si existe un monto a partir del cual hay que identificar al
"consumidor final" en la factura electrónica; plazos y requisitos de la emisión en contingencia (sin
internet); tratamiento fiscal exacto de la consignación. Los sitios de la DNIT y de los competidores no se
pudieron abrir directamente desde el entorno (bloqueo de red); los datos vienen de las búsquedas y de
publicaciones citadas.

### Pruebas propias

- Capturas en `/tmp/claude-0/shots/relevamiento/` (máquina compartida del equipo):
  `01`–`13` caja como vendedor (venta rápida, pago mixto, a cuenta, sin stock, fracción, celular),
  `20`–`23` cuenta corriente y cierre de caja, `30`–`36` depósito, productos, compras, pedido y envío,
  `p-<rol>-<esc|cel>-<pantalla>.png` todas las pantallas por rol en escritorio y celular.
- Scripts del recorrido (Playwright y API) en el scratchpad del líder de relevamiento: `recorrido1.py`
  (caja), `recorrido2.py` (todas las pantallas por rol), `recorrido3/4.py` (cobro y cierre),
  `recorrido5.py` (inventario, productos, envíos), `recorrido6/7.py` (rendimiento con 12.000 productos),
  `api1.py`/`api2.py` (reglas contra la API).

---

## 8. Preguntas para el dueño

**Facturación**
1. ¿Sus clientes objetivo **facturan electrónicamente hoy**? ¿Con qué (facturador gratuito e-Kuatia'i,
   otro sistema, talonario preimpreso)? ¿Saben si están en algún grupo de la RG 52/2026?
2. ¿Preferís integrar el SIFEN **a través de un proveedor habilitado** (pagando por documento, más rápido)
   o **firmar y enviar nosotros** (más trabajo, sin costo por documento)? ¿Hay un proveedor con el que ya
   tengas relación?
3. ¿Quién es el contador de referencia para validar: nota de crédito y plazos de devolución, factura en
   dólares, consignación y formato del registro de comprobantes?

**Cobros y caja**
4. ¿Qué **medios de cobro** usan más sus clientes (efectivo, QR Bancard, tarjetas, transferencias SIP,
   Tigo Money / Billetera Personal, cheques diferidos)? ¿Con qué procesadora trabajan?
5. ¿Cuántas **cajas** y **sucursales** tiene la ferretería típica que queremos venderle? ¿El que vende es el
   mismo que cobra, o hay preventa (vendedor arma y cajero cobra)?
6. ¿Redondean el efectivo? ¿A cuánto (50, 100, 500 Gs.)?
7. ¿Quién puede hacer descuentos y hasta qué %? ¿Las devoluciones necesitan autorización del encargado?
   ¿Devuelven plata o solo cambian / dan vale?

**Catálogo y precios**
8. ¿Cuántos **productos** y **clientes** tiene una ferretería típica de las que apuntamos? ¿Tienen hoy la
   lista en Excel u otro sistema del que haya que migrar?
9. ¿Qué **listas de precios** usan y cómo se calculan (% sobre costo, % de descuento sobre el precio de
   público, precio por cantidad)? ¿Cuántos tipos de cliente?
10. ¿Venden **por metro, kilo o suelto**? ¿Usan **balanza**? ¿Tienen lector de código de barras, impresora
    térmica (58 u 80 mm) e impresora de etiquetas?
11. **Dólares:** ¿venden con precio en USD o solo aceptan dólares como pago? ¿Qué cotización usan (BCP, la
    de una casa de cambio, la propia)? ¿Los clientes objetivo están en zona de frontera?

**Logística y consignación**
12. ¿Hacen **reparto propio** o con terceros? ¿Cobran el envío? En contra entrega, ¿cobra el chofer?
    ¿"Pagado a retirar" es "pagó en caja y retira en el depósito"?
13. **Consignación:** ¿quiénes son los consignatarios (otras ferreterías, obras)? ¿Liquidan por mes? ¿El %
    es fijo por consignatario o por producto? ¿El consignatario usaría SAIL?

**Modelo de negocio**
14. **SaaS:** ¿precio mensual objetivo y qué incluye (cantidad de usuarios, cajas, facturas)? ¿Quién hace
    la carga inicial de datos y el soporte? ¿Mientras tanto vendemos con una instalación por cliente
    (fase 0 de REL-19)?
15. **Windows con licencia perpetua:** ¿precio, qué incluye la actualización, y la ferretería tendrá
    internet para el SIFEN?
16. ¿Conseguís cotizaciones de 2–3 competidores locales (FactPy, Alysoft, eVENDÉ, Yo Facturo) para fijar el
    precio de SAIL?
