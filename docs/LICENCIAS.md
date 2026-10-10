# Licencias de SAIL instalado (propuesta de diseño — NO implementado)

**Estado:** propuesta para decidir. Hoy el instalador de Windows **no pide licencia**: funciona
en cualquier PC. Este documento propone cómo agregarla sin internet y sin molestar al cliente
honesto.

## En simple

- Al vender, el dueño le entrega al cliente un **archivo de licencia** (o un texto para pegar)
  con el **nombre de la empresa y su RUC**, firmado con una clave que **solo tiene el dueño**.
- SAIL verifica la firma **sin internet** (con la clave pública que viene adentro del programa)
  y que el RUC de la licencia sea el mismo que el de *Datos de la empresa*.
- La licencia es **perpetua**: esa versión (y las que salgan hasta la fecha de
  "actualizaciones incluidas hasta") funciona para siempre. Para instalar versiones más nuevas
  se renueva el plan de actualizaciones y se entrega una licencia nueva.
- Como el RUC y la razón social de la licencia salen en el ticket y en la pantalla, copiar la
  licencia de otra ferretería no sirve: el sistema mostraría los datos de otro negocio.

## Qué lleva la licencia

```json
{
  "v": 1,
  "id": "LIC-2026-0007",
  "empresa": "Ferretería San José S.R.L.",
  "ruc": "80012345-6",
  "edicion": "instalada",
  "puestos": 3,
  "emitida": "2026-10-12",
  "actualizaciones_hasta": "2027-10-12",
  "kid": "sail-2026"
}
```

| Campo | Para qué |
|---|---|
| `id` | Número de licencia, para la planilla del dueño y soporte |
| `empresa`, `ruc` | A quién se vendió. El RUC se compara (normalizado: sin puntos, con guion y dígito verificador) con `empresa.ruc` |
| `edicion` | `instalada` (Windows). Deja lugar para otras ediciones |
| `puestos` | Cuántas PCs de la red pueden usarlo a la vez (opcional; ver "decisiones") |
| `actualizaciones_hasta` | Hasta qué fecha de **publicación de versión** se puede actualizar |
| `kid` | Qué clave la firmó (para poder cambiar de clave sin invalidar las viejas) |

**Formato del texto:** `SAIL1.<datos en base64url>.<firma en base64url>`, una sola línea que se
puede mandar por WhatsApp o mail, o guardar como `C:\ProgramData\SAIL\config\licencia.txt`.

## Cómo se firma y se verifica (detalle técnico)

- **Firma Ed25519** (curva moderna, firmas de 64 bytes, verificación rápida). En Python con la
  librería `cryptography` (ruedas binarias para Windows; se suma a `requirements.txt`).
- **Clave privada**: la genera y guarda **solo el dueño**, fuera del repo y fuera de cualquier
  servidor (gestor de contraseñas + un pendrive guardado). Quien la tenga puede emitir licencias.
- **Clave pública**: va en el código (`app/core/licencia.py`, diccionario `kid → clave`), así el
  programa verifica sin internet.
- **Emisión**: `herramientas/emitir_licencia.py --empresa ... --ruc ... --hasta 2027-10-12`
  pide la ruta de la clave privada, firma y muestra la línea `SAIL1....`. Registra el `id` en la
  planilla de licencias del dueño (sin la clave).
- **Verificación** (al arrancar y cada vez que se cambian los datos de la empresa):
  1. Decodificar, verificar la firma con la clave pública del `kid`.
  2. `ruc` de la licencia == `empresa.ruc` (si la empresa todavía no se configuró, la
     configuración inicial **precarga** razón social y RUC desde la licencia).
  3. **Fecha de publicación de la versión** (fija en el programa al construir el instalador,
     `VERSION.txt`) ≤ `actualizaciones_hasta`. Se compara contra la fecha de la *versión*, no
     contra el reloj de la PC: cambiar la hora de Windows no cambia nada y la licencia nunca
     "vence" para la versión que el cliente ya tiene.
- **Dónde se ve**: *Datos de la empresa* muestra "Licencia LIC-2026-0007 · actualizaciones hasta
  12/10/2027". Endpoint `GET /api/v1/licencia` (solo admin) con el estado.
- **Solo en la edición instalada**: en la nube (Vercel) no se pide licencia (la controla el
  dueño dando de alta o de baja la instancia). Se activa con una variable, por ejemplo
  `LICENCIA_REQUERIDA=true`, que pone el instalador de Windows.

## Qué pasa si no hay licencia o no es válida (a decidir; propuesta conservadora)

Nunca bloquear el acceso a los datos del cliente:

1. **Sin licencia**: modo prueba de 30 días desde la configuración inicial con un aviso visible;
   después, aviso permanente y **no se pueden registrar ventas nuevas** (sí consultar, cobrar
   deudas y exportar).
2. **Licencia de otro RUC o firma inválida**: igual que sin licencia, con el motivo claro.
3. **Versión publicada después de `actualizaciones_hasta`**: el instalador avisa *antes* de
   actualizar ("tu licencia incluye actualizaciones hasta ..."). Si igual se instala, funciona en
   modo aviso y se puede volver a la versión anterior con la copia `antes-de-instalar`.

## Lo que esto NO protege (y cómo cubrirlo)

- **El código del backend es público hoy** (`Backend-Ferreteria` es un repo público): cualquiera
  puede bajarlo, quitar la verificación y armar su propio instalador. La licencia frena al
  cliente honesto y deja todo documentado, pero la protección real es:
  - **pasar el backend a privado** antes de vender licencias perpetuas (Vercel sigue funcionando
    con su app de GitHub; GitHub Actions pasa a consumir minutos del plan privado), y
  - el **contrato de licencia** firmado con el cliente.
- Python se puede leer aunque se distribuyan `.pyc`. Ofuscar no vale la pena para este mercado.
- No se ata a la PC (número de disco, placa): las PCs de las ferreterías se cambian y se
  formatean seguido, y generaría llamados a soporte. El RUC alcanza para que copiarla no sirva.

## Decisiones que necesita el dueño

1. ¿Modo prueba de 30 días o licencia obligatoria desde la instalación?
2. ¿Se limitan los **puestos** (PCs de la red)? Contar puestos sin internet es aproximado
   (sesiones activas por equipo); propuesta: no limitar en la primera versión.
3. Duración del plan de actualizaciones incluido (¿12 meses?) y precio de la renovación.
4. ¿Se pasa el backend a privado?

## Plan de implementación (cuando se apruebe, ~2 días)

1. `app/core/licencia.py` (verificar, normalizar RUC) + tests con una clave de prueba.
2. `herramientas/emitir_licencia.py` + generación de la clave del dueño (instrucciones aparte).
3. Endpoint `GET/PUT /api/v1/licencia` (admin) y el aviso en el frontend (*Datos de la empresa* y
   un banner).
4. Instalador: `LICENCIA_REQUERIDA=true` en `sail.env` y fecha de versión en `VERSION.txt`.
5. Bloqueo de ventas nuevas según la decisión 1 (en `CajaService`, con test).
