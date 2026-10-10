# Contrato de API: logística y cobro de pedidos

Para el equipo de Frontend. Cubre:
- cómo se entrega un pedido: **a domicilio** o **retiro en el local**;
- cómo se paga: **anticipado**, **contra entrega** o **a cuenta**;
- señas y pagos anticipados;
- la **rendición** del repartidor en caja y el listado de **cobros por rendir**;
- los datos del traslado (**nota de remisión**, transportista, conductor) y la **hoja imprimible**;
- la línea **"Ventas por pedidos"** del reporte.

Todo va bajo `/api/v1` con `Authorization: Bearer <token>`. Los errores vienen como
`{"detail": "mensaje en español"}`, listo para mostrar.

## En simple

- Cada pedido dice **cómo se entrega** (`modalidad_entrega`) y **cómo se paga** (`forma_pago`).
  Por defecto es a domicilio y contra entrega, que es como se trabajaba hasta ahora.
- **Pago anticipado**: el cliente paga antes. Mientras falte plata, el pedido **no sale del
  depósito** (no se despacha) y **no se entrega** en el local. Pagado, aparece como **"Pagado a
  retirar"** o **"Pagado a entregar"**.
- **Contra entrega**: al entregar, el pedido queda **"Cobro por rendir"** y **la caja no se mueve**.
  Después, quien cobró (repartidor o mostrador) **rinde en la caja abierta** con los medios del
  pago mixto. El efectivo entra al arqueo como ingreso. Se puede rendir en partes.
- **A cuenta**: al entregar, lo que falta se **carga a la cuenta corriente** del cliente, con su
  límite de crédito. Si no le alcanza el crédito, el pedido no sale del depósito.
- En cualquier forma se puede dejar una **seña**. Una seña se puede **anular** (devolver) antes de
  entregar; si fue en efectivo, sale de la caja.
- **Retiro en el local**: no se despacha. Se prepara, queda **"Listo para retirar"** y, cuando el
  cliente lo retira, se registra la entrega: recién ahí se descuenta el stock.
- SAIL **no emite documentos fiscales**: guarda el número de la **nota de remisión** y los datos
  del traslado, y da los datos para una **hoja interna** imprimible.

> **A confirmar con el dueño** (opciones conservadoras implementadas):
> 1. Contra entrega: al entregar no se mueve la caja. El cobro se registra después, cuando el
>    repartidor rinde en una caja abierta.
> 2. Reportes: lo cobrado por pedidos va en una línea aparte ("Ventas por pedidos"), sin sumarse al
>    total de mostrador.

## Permisos

| Acción | Módulo | Admin | Encargado | Vendedor | Depósito |
|---|---|:-:|:-:|:-:|:-:|
| Crear/editar pedido, cambiar condiciones (`PATCH .../condiciones`) | pedidos | sí | sí | sí | no |
| Envíos: crear, listo, despachar, entregar, traslado | ordenes_envio | sí | sí | no | sí |
| Señas, anular señas, rendir | caja | sí | sí | sí | no |
| Consultar (`GET`, incluida la hoja y los cobros por rendir) | — | todos | todos | todos | todos |

`permisos` de `GET /auth/me` trae `pedidos`, `ordenes_envio` y `caja`, según el rol.

## Códigos de respuesta

| Código | Cuándo |
|---|---|
| 201 / 200 | OK |
| 403 | El rol no tiene el permiso del módulo |
| 404 | No existe el pedido, el envío o el pago |
| 409 | No corresponde al estado, por ejemplo: caja cerrada; pedido sin pagar con pago anticipado; despachar un retiro; rendir un pedido sin cobros por rendir; anular dos veces; cancelar un pedido con seña; cambiar la modalidad con un envío en curso |
| 422 | Datos inválidos, por ejemplo: forma de pago desconocida; a cuenta sin cliente; cliente sin crédito o sobre su límite; pagos que superan el saldo; "a cuenta" en una seña; bajar el total por debajo de lo cobrado |

---

## 1. Valores

### `modalidad_entrega`

| Valor | Etiqueta |
|---|---|
| `ENTREGA_DOMICILIO` | Entrega a domicilio (por defecto) |
| `RETIRA_CLIENTE` | Retira en el local |

### `forma_pago`

| Valor | Etiqueta |
|---|---|
| `CONTRA_ENTREGA` | Contra entrega / paga al retirar (por defecto) |
| `ANTICIPADO` | Pago anticipado |
| `CUENTA_CORRIENTE` | A cuenta (exige `cliente_id`) |
| `null` | Pedido anterior al registro de cobros |

### `estado_pago`

Lo calcula el backend.

| Valor | Significado |
|---|---|
| `PENDIENTE` | No se cobró nada |
| `PARCIAL` | Tiene una seña o un pago parcial |
| `PAGADO` | Cobrado por completo |
| `A_CUENTA` | Cubierto, con una parte cargada a la cuenta corriente |
| `POR_RENDIR` | Entregado contra entrega y falta rendir en caja |
| `SIN_REGISTRO` | Pedido entregado o cancelado antes de esta versión (no se le registran cobros) |

### `etiqueta_cobro`

Texto listo para mostrar en listados. Algunos ejemplos: "Pagado a retirar", "Pagado a entregar",
"Contra entrega", "Contra entrega (con seña)", "Paga al retirar", "A cuenta al entregar",
"Falta el pago anticipado", "Cobro por rendir", "Entregado y pagado", "Entregado a cuenta",
"Cancelado" y "Sin registro de cobro".

### Estados nuevos

- **Pedido:** `LISTO_RETIRO` (preparado; el cliente lo retira en el local).
- **Envío:** `LISTO_RETIRO`.

```
Domicilio: PREPARANDO ─lista-despachar─► LISTO ─despachar (−stock)─► EN_TRANSITO ─entregar─► ENTREGADO
                                                                          └─devolver (+stock)─► DEVUELTO
Retiro:    PREPARANDO ─lista-despachar─► LISTO_RETIRO ─entregar (−stock)─► ENTREGADO
Cancelar:  solo en PREPARANDO, LISTO o LISTO_RETIRO (el pedido vuelve a MERCADERIA_RECIBIDA)
```

---

## 2. Pedidos: campos nuevos y condiciones

### Respuesta de un pedido

Aplica a `GET /pedidos-cliente`, `GET /pedidos-cliente/{id}` y a las respuestas de alta y edición.
Se agregan estos campos:

```json
{
  "id": 4, "numero": "PED-2026-0004", "estado": "LISTO_RETIRO", "total": 437500,
  "modalidad_entrega": "RETIRA_CLIENTE",
  "forma_pago": "ANTICIPADO",
  "estado_pago": "PAGADO",
  "monto_pagado": 437500,
  "monto_a_cuenta": 0,
  "saldo": 0,
  "etiqueta_cobro": "Pagado a retirar"
}
```

- `monto_pagado`: lo cobrado (señas, pagos anticipados y rendiciones), sin contar los anulados.
- `monto_a_cuenta`: lo cargado a la cuenta corriente.
- `saldo`: `total − monto_pagado − monto_a_cuenta`.

### `POST /pedidos-cliente`

Acepta dos campos opcionales:

```json
{ "...": "igual que antes", "modalidad_entrega": "RETIRA_CLIENTE", "forma_pago": "ANTICIPADO" }
```

Si no se mandan, el pedido queda `ENTREGA_DOMICILIO` y `CONTRA_ENTREGA`. Con `CUENTA_CORRIENTE`
hace falta `cliente_id` (si no, 422).

### `PUT /pedidos-cliente/{id}`

No cambia las condiciones (para eso está el `PATCH`). Responde **422** si el nuevo total queda por
debajo de lo ya cobrado ("Anulá la seña primero").

### `PATCH /pedidos-cliente/{id}/condiciones`

```json
{ "modalidad_entrega": "ENTREGA_DOMICILIO", "forma_pago": "CUENTA_CORRIENTE" }
```

- Solo cambia lo que se manda.
- **La modalidad** se cambia mientras el pedido no tenga un envío en curso. Si lo tiene, responde
  **409**; hay que cancelar ese envío primero.
- **La forma de pago** se cambia hasta que el pedido se entrega.
  - Pasar a `CUENTA_CORRIENTE` exige un cliente con crédito habilitado (si no, 422).
  - Si un pedido con pago anticipado no se puede despachar por falta de pago, se puede pasar a
    `CONTRA_ENTREGA`.

### Cancelar y eliminar

- `POST /pedidos-cliente/{id}/cancelar`: **409** si el pedido tiene señas vigentes; primero hay que
  anularlas.
- `DELETE /pedidos-cliente/{id}`: **409** si el pedido tiene cobros registrados, aunque estén
  anulados. En ese caso hay que cancelarlo.

---

## 3. Cobros del pedido (módulo caja)

Todos los cobros de pedidos se registran **con una caja abierta**: quedan asociados al turno, y
el efectivo entra al arqueo como `INGRESO`. Los cobros con otros medios no se suman a los totales
de ventas del turno, que son solo de mostrador.

### Medios de pago

`EFECTIVO`, `TARJETA_DEBITO`, `TARJETA_CREDITO`, `TRANSFERENCIA`, `QR` y `CHEQUE`.
`CUENTA_CORRIENTE` solo se acepta al **rendir**, para cargar a la cuenta lo que el cliente no pagó.

### Tipos de pago (`tipo`)

| Valor | Cuándo |
|---|---|
| `ANTICIPO` | Seña o pago anticipado, antes de entregar |
| `RENDICION` | Cobro contra entrega rendido en caja |
| `CARGO_CUENTA` | Saldo cargado a la cuenta corriente (al entregar un pedido a cuenta, o al rendir) |

### `GET /pedidos-cliente/{id}/pagos`

Devuelve los pagos en orden, incluidos los anulados.

```json
[
  {
    "id": 1, "tipo": "ANTICIPO", "metodo": "EFECTIVO", "monto": 5000, "referencia": null,
    "caja_turno_id": 3, "orden_envio_id": null, "usuario_id": 2, "usuario_nombre": "vendedor",
    "created_at": "2026-10-10T15:20:00", "anulado": false, "anulado_at": null, "anulado_por": null,
    "motivo_anulacion": null
  }
]
```

### `POST /pedidos-cliente/{id}/pagos`: seña o pago anticipado

```json
{ "pagos": [ { "metodo": "EFECTIVO", "monto": 5000 }, { "metodo": "TRANSFERENCIA", "monto": 7000, "referencia": "op 77" } ] }
```

- Responde **201** con `{ "pedido": {...}, "pagos": [...] }`.
- Los pagos pueden ser **menores o iguales al saldo**; si lo superan, 422.
- **409** si no hay caja abierta, si el pedido ya se entregó (corresponde rendir) o si está
  cancelado. **422** si ya está pagado.

### `POST /pedidos-cliente/{id}/pagos/{pago_id}/anular`: devolver una seña

```json
{ "motivo": "Desistió de la compra" }
```

- Solo para pagos `ANTICIPO` de un pedido **sin entregar**.
- Si fue en efectivo, se registra un `RETIRO` en la caja abierta (sin caja abierta, 409).
- Responde con `{ "pedido": {...}, "pagos": [...] }`. **409** si el pago ya estaba anulado.

### `GET /cobros-por-rendir`

Pedidos entregados contra entrega con saldo sin rendir, ordenados por fecha de entrega, de la más
antigua a la más reciente:

```json
[
  {
    "pedido_id": 8, "numero": "PED-2026-0008", "cliente_id": 2, "cliente_nombre": "Ferretería El Tornillo Feliz",
    "cliente_telefono": "0982111222", "modalidad_entrega": "ENTREGA_DOMICILIO",
    "total": 386250, "monto_pagado": 0, "por_rendir": 386250,
    "orden_envio_id": 6, "orden_envio_numero": "ENV-2026-0006", "fecha_entrega": "2026-10-10",
    "transportista": "Reparto propio", "conductor_nombre": "Carlos Duarte"
  }
]
```

### `POST /pedidos-cliente/{id}/rendir`: el repartidor rinde en caja

```json
{ "pagos": [ { "metodo": "EFECTIVO", "monto": 13000 }, { "metodo": "CUENTA_CORRIENTE", "monto": 20000 } ] }
```

- Solo para pedidos `POR_RENDIR` (si no, 409). Hace falta una caja abierta.
- Pago mixto: los pagos pueden sumar **menos** que el saldo (rendición parcial; el pedido sigue
  `POR_RENDIR`), pero no más (422).
- Una línea `CUENTA_CORRIENTE` carga ese monto a la cuenta del cliente. Hace falta que el pedido
  sea de un cliente del catálogo y que el monto entre en su límite (si no, 422).
- Cuando se cubre el total, el pedido pasa a `PAGADO`, o a `A_CUENTA` si se cargó algo a cuenta.

---

## 4. Envíos: modalidad, traslado y hoja

### Respuesta de un envío

Se agregan estos campos:

```json
{
  "modalidad": "ENTREGA_DOMICILIO",
  "numero_nota_remision": "001-001-0000100",
  "transportista_ruc": "80012345-6",
  "vehiculo": "Isuzu — chapa ABC 123",
  "conductor_nombre": "Pedro Gómez",
  "conductor_documento": "1234567"
}
```

`transportista` y `metodo_envio` ya existían.

### `POST /ordenes-envio`

- La modalidad sale del pedido.
- `direccion_entrega` es **opcional en un retiro** (queda "Retira en el local") y **obligatoria a
  domicilio** (si falta, 422).
- Acepta además `transportista`, `numero_nota_remision`, `transportista_ruc`, `vehiculo`,
  `conductor_nombre` y `conductor_documento`.

### `POST /ordenes-envio/{id}/lista-despachar`

- A domicilio pasa a `LISTO`.
- En un retiro pasa a `LISTO_RETIRO`, y el pedido también.

### `POST /ordenes-envio/{id}/despachar`

```json
{ "numero_guia": "G-1", "transportista": "Fletes Ñandutí", "vehiculo": "Isuzu ABC 123",
  "conductor_nombre": "Pedro Gómez", "conductor_documento": "1234567", "numero_nota_remision": "001-001-0000100" }
```

- Todos los campos son opcionales; solo cambia lo que se manda.
- **409** si el envío es un retiro en el local.
- **409** si el pedido es con pago anticipado y tiene saldo.
- **422** si es a cuenta y el saldo supera el crédito del cliente.

### `POST /ordenes-envio/{id}/entregar`

Igual que antes: el cuerpo es opcional, `{ "observaciones": "..." }`.

- **Domicilio:** desde `EN_TRANSITO`.
- **Retiro:** desde `LISTO_RETIRO`. Acá se descuenta el stock (en el kardex queda una `SALIDA`
  "Retiro en el local").
  - **409** si todavía está `PREPARANDO`.
  - **409** si es con pago anticipado y falta pagar.
  - **422** si es a cuenta y supera el crédito.
- **Efecto en el cobro del pedido:**
  - a cuenta: carga el saldo a la cuenta corriente (`A_CUENTA`);
  - contra entrega con saldo: `POR_RENDIR`;
  - pagado: queda `PAGADO`.
- **No mueve la caja.**

### `PATCH /ordenes-envio/{id}/traslado`

```json
{ "numero_nota_remision": "001-001-0000101", "conductor_nombre": "Carlos Duarte" }
```

Solo cambia lo que se manda; un texto vacío borra el dato. **409** si el envío está cancelado.

### `GET /ordenes-envio/{id}/hoja`: hoja interna imprimible

```json
{
  "titulo": "Hoja de entrega — ENV-2026-0004",
  "leyenda": "Documento interno — no reemplaza a la factura ni a la nota de remisión timbrada (N° 001-001-0000100)",
  "empresa": { "nombre_comercial": "Ferretería Demo", "razon_social": "Ferretería Demo S.A.", "ruc": "80000000-0",
               "direccion": "Av. Principal 123", "ciudad": "Asunción", "telefono": "021 000 000",
               "moneda_simbolo": "Gs.", "locale": "es-PY" },
  "orden": { "...": "igual que GET /ordenes-envio/{id}" },
  "pedido_numero": "PED-2026-0005",
  "cliente_nombre": "Electricista Ramón Ortiz", "cliente_ruc": "3456789-0", "cliente_telefono": "0991444333",
  "items": [ { "producto_id": 3, "codigo": "PROD-00003", "nombre": "Cable eléctrico 2.5mm (rollo 100m)", "unidad_medida": "rollo", "cantidad": 2.0 } ],
  "cobro": { "forma_pago": "ANTICIPADO", "estado_pago": "PAGADO", "etiqueta": "Pagado a entregar",
             "total": 725000, "pagado": 725000, "a_cuenta": 0, "a_cobrar_en_la_entrega": 0 }
}
```

- `a_cobrar_en_la_entrega` es lo que el repartidor (o el mostrador, en un retiro) tiene que
  cobrar. Solo tiene valor en contra entrega.
- En un retiro, el título es "Retiro en el local — ENV-...".
- Para la hoja se sugiere: empresa; datos del cliente y dirección; tabla de ítems; transportista,
  vehículo y conductor; número de nota de remisión; un recuadro "A cobrar: Gs. X"; espacio para
  firma y aclaración de quien recibe; y la leyenda al pie.

---

## 5. Reporte de ventas

`GET /reportes/ventas` agrega `ventas_por_pedidos`. Va aparte de `mostrador`, que no cambia.

```json
"ventas_por_pedidos": {
  "cantidad_pedidos": 4,
  "total": 1893750,
  "por_metodo_pago": [
    { "metodo_pago": "QR", "cantidad": 1, "total": 725000 },
    { "metodo_pago": "TRANSFERENCIA", "cantidad": 1, "total": 437500 },
    { "metodo_pago": "CUENTA_CORRIENTE", "cantidad": 1, "total": 431250 },
    { "metodo_pago": "EFECTIVO", "cantidad": 1, "total": 300000 }
  ]
}
```

- Cuenta lo **cobrado en el período**, por la fecha del cobro y en hora de Paraguay: señas, pagos
  anticipados, rendiciones y cargos a cuenta al entregar.
- No incluye los pagos anulados. `cantidad` es la cantidad de pedidos distintos.
- `pedidos_entregados` sigue igual.
- Sugerencia de pantalla: una tarjeta "Ventas por pedidos" al lado de "Mostrador", con su propio
  desglose por medio de pago.

---

## 6. Pantallas sugeridas

1. **Pedido (alta y detalle):**
   - selector "Entrega a domicilio / Retira en el local" y selector de forma de pago;
   - chip con `etiqueta_cobro`, y total, pagado, a cuenta y saldo;
   - botones "Registrar seña o pago" (con permiso `caja`), "Cambiar condiciones" e historial de
     pagos con "Anular" en cada seña.
2. **Envíos:**
   - columna "Modalidad";
   - para un retiro, botones "Listo para retirar" y "Entregar (retiró)", sin "Despachar";
   - diálogo de despacho con transportista, vehículo, conductor y número de nota de remisión;
   - "Imprimir hoja" con `GET .../hoja`.
3. **Caja → Cobros por rendir:**
   - tabla de `GET /cobros-por-rendir` con la acción "Rendir" (diálogo de pago mixto como el de la
     venta, más la opción "A cuenta");
   - aviso en Inicio si hay pendientes (opcional).
4. **Reportes:** tarjeta "Ventas por pedidos".

## Notas para la migración

- Los pedidos que ya estaban **entregados o cancelados** quedan con `forma_pago: null` y
  `estado_pago: SIN_REGISTRO`.
- Los demás pasan a `CONTRA_ENTREGA`. Por eso, **un pedido que hoy está en camino y se entregue
  después de actualizar aparece en "Cobros por rendir"**. Si ya se cobró por fuera del sistema, se
  rinde con el medio correspondiente.
