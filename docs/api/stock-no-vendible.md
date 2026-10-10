# Contrato de API: stock no vendible y reclamos al proveedor

Para el equipo de Frontend. Describe los endpoints, qué mandar, qué devuelven, los estados y
las reglas. Todo va bajo `/api/v1` con `Authorization: Bearer <token>`. Los errores vienen
siempre como `{"detail": "mensaje en español"}`, listo para mostrar en un toast.

## En simple

- Un producto puede tener unidades que **existen pero no se pueden vender**: averiadas,
  abolladas, vencidas, con defecto de fábrica u otro motivo (con nota).
- Al **marcarlas**, el stock vendible baja y el no vendible sube. El total físico no cambia.
- La **caja, los pedidos y los envíos solo ven el stock vendible** (`stock_actual`). El
  **inventario muestra los dos**.
- Las unidades no vendibles se **resuelven** de tres maneras:
  1. **Reparadas**: vuelven a vendibles.
  2. **Descartadas**: se dan de baja con pérdida.
  3. **Reclamadas al proveedor**: se agrupan en un **reclamo** (número `RCL-AAAA-NNNN`); si el
     proveedor lo acepta, cada ítem se resuelve con **reposición** (se lleva lo dañado y trae
     mercadería nueva), **nota de crédito** (se lleva lo dañado y descuenta un monto) o
     **rechazado** (las unidades siguen no vendibles y se pueden reparar, descartar o volver a
     reclamar).
- Todo queda en el **kardex** con quién lo hizo y cuándo.
- SAIL **no genera documentos fiscales**: solo guarda el número de la **nota de crédito** que
  emite el proveedor y de la **nota de remisión** si la mercadería viaja.

## Permisos

Módulo **inventario** (`"inventario"` en `permisos` de `GET /auth/me`):

| Acción | Admin | Encargado | Depósito | Vendedor |
|---|:-:|:-:|:-:|:-:|
| Consultar (todos los `GET`) | sí | sí | sí | sí |
| Marcar, reparar, descartar, reclamos (todo lo demás) | sí | sí | sí | no (403) |

Ocultá los botones de acción si `permisos` no incluye `"inventario"`.

## Códigos de respuesta

| Código | Cuándo |
|---|---|
| 200 / 201 | OK (201 al crear) |
| 401 | Sin sesión o token vencido |
| 403 | El rol no puede modificar inventario |
| 404 | No existe el producto, proveedor, registro, reclamo, ítem u orden de compra |
| 409 | No alcanza el stock (`Stock insuficiente ...`) o la acción no corresponde al estado (resolver dos veces, editar un reclamo enviado...) |
| 422 | Datos inválidos (cantidad 0, motivo desconocido, `OTRO` sin nota, nota de crédito sin monto, unidades de otro proveedor, más unidades de las que quedan para reclamar...) |

---

## 1. Cambios en endpoints existentes

### Productos e inventario

`GET /productos`, `GET /productos/{id}`, `GET /productos/buscar` y `GET /inventario/stock`
devuelven dos campos nuevos:

```json
{
  "id": 2, "codigo": "PROD-00002", "nombre": "Taladro percutor 1/2\"",
  "stock_actual": 8.0,
  "stock_no_vendible": 1.0,
  "stock_total": 9.0,
  "stock_minimo": 3.0, "stock_bajo": false
}
```

- `stock_actual`: **stock vendible** (igual que antes; es lo que usa la caja).
- `stock_no_vendible`: unidades no vendibles sin resolver.
- `stock_total`: `stock_actual + stock_no_vendible` (unidades físicas).
- `stock_bajo` se calcula con el stock vendible.
- El ajuste manual (`POST /inventario/ajustes`, conteo físico) **fija el stock vendible**; el no
  vendible solo cambia con los endpoints de este documento.

### Kardex

`GET /inventario/kardex/{producto_id}` y `GET /inventario/movimientos` (más recientes primero):

- Tipos nuevos en `tipo`: `TRASPASO` (entre vendible y no vendible; el total no cambia) y
  `BAJA` (descarte con pérdida). Siguen `ENTRADA`, `SALIDA` y `AJUSTE`.
- Referencias nuevas en `referencia_tipo`: `STOCK_NO_VENDIBLE` (`referencia_id` = id del
  registro) y `RECLAMO_PROVEEDOR` (`referencia_id` = id del reclamo).
- Campos nuevos `no_vendible_anterior` y `no_vendible_nuevo`: `null` en movimientos que no tocan
  lo no vendible. `stock_anterior` / `stock_nuevo` son **siempre del stock vendible**.

| Operación | `tipo` | `cantidad` | Vendible | No vendible |
|---|---|---|---|---|
| Marcar no vendible | `TRASPASO` | negativa (`-5`) | baja | sube |
| Reparar | `TRASPASO` | positiva | sube | baja |
| Descartar | `BAJA` | positiva | igual | baja |
| Reclamo: nota de crédito | `SALIDA` | positiva | igual | baja |
| Reclamo: reposición | `SALIDA` + `ENTRADA` (dos filas) | positiva | sube (en la `ENTRADA`) | baja (en la `SALIDA`) |

```json
{
  "id": 794, "producto_id": 2, "tipo": "TRASPASO", "cantidad": -1.0,
  "stock_anterior": 9.0, "stock_nuevo": 8.0,
  "no_vendible_anterior": 0.0, "no_vendible_nuevo": 1.0,
  "referencia_tipo": "STOCK_NO_VENDIBLE", "referencia_id": 1, "usuario_id": 4,
  "observaciones": "Pasa a no vendible (defecto de fábrica): No enciende; está en garantía",
  "created_at": "2026-10-10T12:59:33.673608"
}
```

Sugerencia de etiquetas: `TRASPASO` "Traspaso", `BAJA` "Baja"; `STOCK_NO_VENDIBLE` "Stock no
vendible", `RECLAMO_PROVEEDOR` "Reclamo al proveedor".

---

## 2. Stock no vendible

Cada **registro** son unidades de un producto marcadas juntas por un mismo motivo.

### Motivos (`motivo`)

| Valor | Etiqueta |
|---|---|
| `AVERIADO` | Averiado |
| `ABOLLADO` | Abollado |
| `VENCIDO` | Vencido |
| `DEFECTO_FABRICA` | Defecto de fábrica |
| `OTRO` | Otro (la `nota` es obligatoria) |

### Estados del registro (`estado`, lo calcula el backend)

| Valor | Significado |
|---|---|
| `PENDIENTE` | Hay unidades sin resolver que no están en un reclamo abierto |
| `EN_RECLAMO` | Todas las unidades sin resolver están en un reclamo abierto (borrador, enviado o aceptado) |
| `RESUELTO` | Ya no quedan unidades sin resolver |

### Cantidades de un registro

- `cantidad`: las que se marcaron.
- `cantidad_pendiente`: las que todavía no se resolvieron (siguen en `stock_no_vendible`).
- `cantidad_en_reclamo`: de las pendientes, las reservadas en reclamos abiertos.
- `cantidad_libre` = pendiente − en reclamo: **las únicas que se pueden reparar, descartar o
  sumar a otro reclamo**.
- `costo_unitario`: precio de compra del producto al marcarlas. `valor_pendiente` =
  pendiente × costo.

### `GET /stock-no-vendible`

Filtros opcionales: `estado`, `producto_id`, `proveedor_id`, `motivo`. Más recientes primero. No
incluye `resoluciones` (viene `null`).

```json
[
  {
    "id": 6, "producto_id": 23, "producto_codigo": "PROD-00023", "producto_nombre": "Foco LED 12W",
    "unidad_medida": "pz",
    "cantidad": 5.0, "cantidad_pendiente": 3.0, "cantidad_en_reclamo": 0.0, "cantidad_libre": 3.0,
    "motivo": "AVERIADO", "nota": "Vidrio roto",
    "proveedor_id": null, "proveedor_nombre": null, "orden_compra_id": null,
    "costo_unitario": 9500, "valor_pendiente": 28500,
    "estado": "PENDIENTE",
    "usuario_id": 4, "usuario_nombre": "Depósito Demo",
    "created_at": "2026-10-10T12:59:33.673608", "updated_at": "2026-10-10T12:59:33.673608",
    "resoluciones": null
  }
]
```

### `GET /stock-no-vendible/{id}`

Igual que un elemento del listado, más el historial de resoluciones:

```json
"resoluciones": [
  {
    "id": 1, "tipo": "DESCARTADO", "cantidad": 2.0, "monto": 19000, "reclamo_id": null,
    "nota": "Sin arreglo posible", "usuario_id": 4, "usuario_nombre": "Depósito Demo",
    "created_at": "2026-10-10T12:59:33.673608"
  }
]
```

Tipos de resolución: `REPARADO`, `DESCARTADO` (`monto` = pérdida), `REPUESTO_PROVEEDOR`,
`NOTA_CREDITO_PROVEEDOR` (`monto` = importe de la nota de crédito). Las dos últimas traen el
`reclamo_id`.

### `POST /stock-no-vendible` — marcar unidades como no vendibles

```json
{
  "producto_id": 2,
  "cantidad": 1,
  "motivo": "DEFECTO_FABRICA",
  "nota": "No enciende; está en garantía",
  "proveedor_id": 1,
  "orden_compra_id": null
}
```

- `nota`, `proveedor_id` y `orden_compra_id` son opcionales (`nota` obligatoria con `OTRO`).
  Cargar el proveedor ayuda a armar el reclamo después.
- Responde **201** con el registro (con `resoluciones: []`).
- **409** si `cantidad` es mayor que el stock vendible:
  `"Stock insuficiente para Taladro. Disponible: 8, requerido: 9"`.

### `POST /stock-no-vendible/{id}/reparar` — vuelven a vendibles

### `POST /stock-no-vendible/{id}/descartar` — baja con pérdida

Mismo cuerpo para las dos:

```json
{ "cantidad": 2, "nota": "Se enderezó la tapa" }
```

- Sin `cantidad` (o `{}`) se resuelven **todas las unidades libres**.
- Responden **200** con el registro actualizado (con `resoluciones`).
- **409** si el registro ya está `RESUELTO`, si todas sus unidades están en un reclamo abierto, o
  si `cantidad` supera `cantidad_libre`.

---

## 3. Reclamos al proveedor

### Estados (`estado`)

```
BORRADOR ──enviar──► ENVIADO ──aceptar──► ACEPTADO ──(se resuelve el último ítem)──► RESUELTO
   │                    │
 eliminar            rechazar ──► RECHAZADO
```

| Estado | Qué se puede hacer |
|---|---|
| `BORRADOR` | Editar ítems y notas (`PUT`), eliminar (`DELETE`), enviar |
| `ENVIADO` | Aceptar o rechazar (respuesta del proveedor) |
| `ACEPTADO` | Resolver cada ítem |
| `RECHAZADO` | Nada (final). Las unidades vuelven a quedar libres |
| `RESUELTO` | Nada (final) |

En cualquier estado se pueden registrar los números de documentos
(`PATCH /reclamos-proveedor/{id}/documentos`).

### Resolución de cada ítem (`resolucion`)

| Valor | Efecto en el stock | Datos |
|---|---|---|
| `REPOSICION` | No vendible −cantidad y vendible +cantidad | — |
| `NOTA_CREDITO` | No vendible −cantidad | `monto_nota_credito` obligatorio (> 0) |
| `RECHAZADO` | Ninguno: las unidades siguen no vendibles y quedan libres | — |
| `null` | Ítem sin resolver | — |

### Reglas al armar un reclamo

- Al menos un ítem; cada registro una sola vez.
- Cada ítem es un **registro** de stock no vendible y una `cantidad` (sin `cantidad` = todas sus
  unidades libres).
- El registro no puede estar `RESUELTO` ni ser **de otro proveedor**. Si no tenía proveedor,
  queda asociado al del reclamo.
- No se pueden reclamar más unidades que las libres (las reservadas en otros reclamos abiertos no
  cuentan): `"De Foco LED 12W (registro 6) quedan 3 unidades para reclamar; pediste 4"`.
- El número `RCL-AAAA-NNNN` se asigna al crear el borrador (correlativo por año). Si se elimina
  el último borrador, su número se vuelve a usar.
- Los datos del proveedor (razón social, RUC, teléfono, email, dirección) se copian al reclamo:
  el documento no cambia si después se edita el proveedor.

### `GET /reclamos-proveedor`

Filtros opcionales: `estado`, `proveedor_id`. Más recientes primero. Cada elemento es un reclamo
completo (ver abajo).

### `GET /reclamos-proveedor/{id}`

```json
{
  "id": 1,
  "numero": "RCL-2026-0001",
  "estado": "ENVIADO",
  "proveedor": {
    "id": 1, "razon_social": "Distribuidora Central Ferretera", "ruc": "80011111-1",
    "telefono": "0985111111", "email": "ventas@central-ferretera.com.py",
    "direccion": "Zona Industrial 1, Luque"
  },
  "usuario_id": 4, "usuario_nombre": "Depósito Demo",
  "notas": "Unidades con defecto de fábrica de la última compra",
  "respuesta_proveedor": null,
  "motivo_rechazo": null,
  "numero_nota_credito": null,
  "numero_nota_remision": "001-001-0000457",
  "fecha_envio": "2026-10-10T12:59:33.673608",
  "fecha_respuesta": null,
  "fecha_resolucion": null,
  "created_at": "2026-10-10T12:59:33.673608",
  "cantidad_items": 2,
  "items_pendientes": 2,
  "total_reclamado": 470000,
  "total_nota_credito": 0,
  "items": [
    {
      "id": 1, "registro_id": 1, "producto_id": 2, "producto_codigo": "PROD-00002",
      "producto_nombre": "Taladro percutor 1/2\"", "unidad_medida": "pz",
      "motivo": "DEFECTO_FABRICA", "nota_registro": "No enciende; está en garantía",
      "cantidad": 1.0, "costo_unitario": 380000, "subtotal": 380000,
      "resolucion": null, "monto_nota_credito": 0, "nota_resolucion": null,
      "resuelto_por": null, "resuelto_at": null
    }
  ]
}
```

- `total_reclamado` = suma de `cantidad × costo_unitario` (valor al costo).
- `total_nota_credito` = suma de los montos de nota de crédito de los ítems.
- `items_pendientes` = ítems con `resolucion: null`.

### `GET /reclamos-proveedor/{id}/documento` — para imprimir o enviar

Devuelve todo lo que necesita la hoja del reclamo (la pantalla la arma Frontend, como el ticket):

```json
{
  "titulo": "Reclamo al proveedor N° RCL-2026-0001",
  "leyenda": "Documento interno de reclamo — no válido como comprobante fiscal",
  "empresa": {
    "nombre_comercial": "Ferretería Demo", "razon_social": "Ferretería Demo S.A.", "ruc": "80000000-0",
    "direccion": "Av. Principal 123", "ciudad": "Asunción", "telefono": "021 000 000", "email": null,
    "moneda_simbolo": "Gs.", "locale": "es-PY"
  },
  "reclamo": { "...": "igual que GET /reclamos-proveedor/{id}" }
}
```

Sugerencia para la hoja: encabezado con la empresa, datos del proveedor, número y fecha de envío,
tabla de ítems (código, producto, motivo y nota, cantidad, costo, subtotal), total reclamado,
números de nota de remisión y de nota de crédito si los hay, notas y la `leyenda` al pie.

### `POST /reclamos-proveedor` — crear borrador

```json
{
  "proveedor_id": 1,
  "notas": "Mercadería de la última entrega",
  "items": [
    { "registro_id": 1 },
    { "registro_id": 6, "cantidad": 2 }
  ]
}
```

Responde **201** con el reclamo en `BORRADOR`.

### `PUT /reclamos-proveedor/{id}` — editar borrador

Mismo cuerpo sin `proveedor_id` (los ítems se **reemplazan** por los que se mandan). **409** si
no está en `BORRADOR`.

### `DELETE /reclamos-proveedor/{id}` — eliminar borrador

`{"mensaje": "Reclamo eliminado; las unidades vuelven a estar disponibles para resolver"}`.
**409** si no está en `BORRADOR`.

### `POST /reclamos-proveedor/{id}/enviar`

```json
{ "numero_nota_remision": "001-001-0000457" }
```

`numero_nota_remision` es opcional (solo si la mercadería viaja al proveedor). Guarda
`fecha_envio`. **409** si no está en `BORRADOR`.

### `POST /reclamos-proveedor/{id}/aceptar`

```json
{ "respuesta_proveedor": "Aceptan revisar las unidades" }
```

Opcional. Pasa a `ACEPTADO` y guarda `fecha_respuesta`. **409** si no está `ENVIADO`.

### `POST /reclamos-proveedor/{id}/rechazar`

```json
{ "motivo": "Fuera de garantía" }
```

Obligatorio. Pasa a `RECHAZADO`: todos los ítems quedan con `resolucion: "RECHAZADO"`, el stock
no cambia y las unidades quedan libres para reparar, descartar o reclamar de nuevo. **409** si no
está `ENVIADO`.

### `POST /reclamos-proveedor/{id}/items/{item_id}/resolver`

```json
{
  "resolucion": "NOTA_CREDITO",
  "monto_nota_credito": 65000,
  "numero_nota_credito": "001-002-0000456",
  "nota": "Acreditado en la próxima factura"
}
```

- `resolucion`: `REPOSICION`, `NOTA_CREDITO` o `RECHAZADO`.
- `monto_nota_credito`: obligatorio con `NOTA_CREDITO` (se ignora en las demás).
- `numero_nota_credito`: opcional; si viene, se guarda en el reclamo.
- Responde **200** con el reclamo. Al resolver el último ítem pasa solo a `RESUELTO`
  (`fecha_resolucion`).
- **409** si el ítem **ya fue resuelto** (`"Este ítem ya fue resuelto (REPOSICION)"`) o si el
  reclamo no está `ACEPTADO`. **404** si el ítem no es de ese reclamo.

### `PATCH /reclamos-proveedor/{id}/documentos`

```json
{ "numero_nota_credito": "001-002-0000456", "numero_nota_remision": "001-001-0000457" }
```

Solo cambia los campos que se mandan; un texto vacío (`""`) borra el número.

---

## 4. Flujo sugerido para las pantallas

1. **Inventario**: columnas "Vendible", "No vendible" y "Total"; acción "Marcar no vendible" en el
   menú ⋯ del producto (diálogo con cantidad, motivo, nota, proveedor opcional).
2. **Stock no vendible** (pantalla nueva o pestaña de Inventario): tabla de registros con filtro
   por estado/motivo/proveedor; acciones "Reparar", "Descartar" (con cantidad, por defecto
   `cantidad_libre`) y "Reclamar al proveedor" (selección múltiple de registros del mismo
   proveedor → `POST /reclamos-proveedor`). Detalle con el historial de `resoluciones`.
3. **Reclamos**: lista por estado; detalle con botones según el estado (tabla de arriba), un
   diálogo por ítem para resolver y "Imprimir" con `GET .../documento`.
4. **Kardex**: mostrar `no_vendible_nuevo` cuando no es `null` y las etiquetas nuevas de tipo y
   referencia.
