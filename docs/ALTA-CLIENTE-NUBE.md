# Alta de un cliente en la nube (SAIL con pago mensual)

Guía para el dueño. Con esto se crea la instancia de SAIL de una ferretería nueva en unos
**30 minutos**: una base de datos propia en **Neon** y un proyecto propio en **Vercel** que muestra
las pantallas y atiende la API en **una sola dirección** (servidor único).

```
  Cliente (navegador) ──► https://sail-ferreteria-x.vercel.app ──► Neon (base del cliente)
                           pantallas en /  ·  API en /api/v1
```

Cada cliente tiene **su propia base y su propio proyecto**: los datos de una ferretería nunca se
mezclan con los de otra, y se puede dar de baja, restaurar o mover a uno sin tocar a los demás.

> **Antes del primer cliente**, hacé una sola vez la sección [0. Preparación](#0-preparación-una-sola-vez).
> Las capturas se describen con el nombre exacto de los botones; los paneles de Neon y Vercel
> cambian de diseño seguido, así que si un botón se movió, buscalo por su nombre.

---

## Resumen (para tener a mano)

| # | Paso | Dónde | Tiempo |
|---|---|---|---|
| 1 | Crear la base del cliente | Neon | 5 min |
| 2 | Generar las variables | tu PC (`herramientas/alta_cliente.py`) | 2 min |
| 3 | Crear el proyecto y pegar las variables | Vercel | 10 min |
| 4 | Verificar que responde | tu PC | 2 min |
| 5 | Configuración inicial con el cliente | el navegador | 5 min |
| 6 | (Opcional) Dominio propio | Vercel + el proveedor del dominio | 5 min + espera |
| 7 | Anotar el cliente en tu planilla | tu planilla | 2 min |

---

## 0. Preparación (una sola vez)

1. **Cuenta de Neon** (https://neon.tech) — donde viven las bases de datos.
2. **Cuenta de Vercel** (https://vercel.com) conectada a tu GitHub (la que ya tiene `ankor-backend`).
   - **Importante:** el plan **Hobby** (gratis) de Vercel es para uso personal y **no comercial**.
     Para cobrarle a clientes hay que pasar a **Pro** (Vercel → *Settings* → *Billing*). Revisá
     los términos y precios vigentes antes de vender.
   - Lo mismo con Neon: el plan gratis tiene límites de espacio, de horas de cómputo y de
     cantidad de proyectos; para clientes que pagan conviene un plan pago.
3. **Acceso al frontend.** El repo `Frontend-Ferreteria` es **privado** y Vercel tiene que poder
   bajar las pantallas al construir. Elegí una de dos:
   - **(a) Hacer público el repo del frontend** (GitHub → `Frontend-Ferreteria` → *Settings* →
     *General* → abajo de todo *Danger Zone* → *Change visibility* → *Public*). Es código que de
     todas formas ya descarga cualquier navegador que abre el sistema. Con esto **no hace falta
     token**: borrás la línea `FRONTEND_TOKEN` del bloque de variables.
   - **(b) Crear un token de solo lectura** (si querés mantenerlo privado):
     GitHub → tu foto (arriba a la derecha) → *Settings* → *Developer settings* (abajo de todo a
     la izquierda) → *Personal access tokens* → *Fine-grained tokens* → **Generate new token**.
     - *Token name*: `SAIL Vercel frontend` · *Expiration*: 1 año (anotá cuándo vence).
     - *Repository access*: **Only select repositories** → `Frontend-Ferreteria`.
     - *Permissions* → *Repository permissions* → **Contents: Read-only** (nada más).
     - **Generate token** y copialo (empieza con `github_pat_`). GitHub lo muestra una sola vez.
       Guardalo en tu gestor de contraseñas: lo vas a pegar en cada cliente como `FRONTEND_TOKEN`.
4. **Python 3.12 en tu PC** (para el paso 2 y 4). En Windows: https://www.python.org/downloads/
   (en el instalador, marcá *Add python.exe to PATH*). Bajá el backend: en GitHub,
   `Backend-Ferreteria` → botón verde **Code** → **Download ZIP**, y descomprimilo.
   - Si no querés instalar Python, el paso 2 se puede hacer a mano (ver
     [SECRET_KEY sin Python](#secret_key-sin-python)) y el paso 4 abriendo las direcciones en el navegador.

---

## 1. Crear la base del cliente en Neon (5 min)

1. Entrá a https://console.neon.tech → botón **New Project** (o *Create project*).
2. Completá:
   - **Project name**: `sail-<cliente>` (ej. `sail-ferreteria-san-jose`). Usá siempre el mismo
     nombre en Neon y en Vercel: después es fácil encontrar todo.
   - **Postgres version**: la que sugiere (16 o 17).
   - **Region**: **AWS São Paulo (sa-east-1)**: es la más cercana a Paraguay.
   - **Create**.
3. En el panel del proyecto, botón **Connect** (arriba a la derecha). Se abre una ventana con la
   *Connection string*:
   - **Connection pooling**: **activado** (la dirección del host tiene que decir `-pooler`).
   - Botón **Copy snippet** / ícono de copiar. Queda algo como
     `postgresql://neondb_owner:xxxx@ep-algo-123-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
   - **No la pegues en ningún chat, mail ni planilla**: tiene la contraseña de la base. Solo va a
     Vercel (paso 3). Si se filtra, en Neon → *Roles* → *Reset password* y actualizala en Vercel.

> Detalle técnico: SAIL usa el driver `pg8000`. La cadena de Neon se puede pegar **tal cual**
> (`postgresql://...`): el backend la convierte a `postgresql+pg8000://` y traduce `sslmode` y
> `channel_binding` (ver `app/infrastructure/db/session.py`).

---

## 2. Generar las variables (2 min)

En tu PC, en la carpeta del backend, abrí una terminal (Windows: clic derecho en la carpeta →
*Abrir en Terminal*) y corré:

```
python herramientas/alta_cliente.py variables --nombre "Ferretería San José"
```

Muestra qué es cada variable y un **bloque para pegar de una vez** en Vercel:

```
DATABASE_URL=<pegar la cadena de Neon tal cual, la del host con -pooler>
SECRET_KEY=Xk3...(64 letras al azar, distinta cada vez)
ENVIRONMENT=production
SEED_DEMO=false
APP_NAME=SAIL - Ferretería San José
FRONTEND_DIR=frontend
FRONTEND_TOKEN=<token de GitHub de solo lectura del repo del frontend>
```

| Variable | Para qué | Valor |
|---|---|---|
| `DATABASE_URL` | Conexión a la base del cliente | La cadena del paso 1 (host con `-pooler`) |
| `SECRET_KEY` | Firma las sesiones. Quien la tenga podría entrar como cualquier usuario | Generada al azar, **una distinta por cliente**. El script no la guarda: copiala ya |
| `ENVIRONMENT` | Modo producción | `production` |
| `SEED_DEMO` | Datos de ejemplo | **`false` siempre** en un cliente (la demo tiene contraseñas conocidas) |
| `APP_NAME` | Nombre que muestra la API | `SAIL - <cliente>` |
| `FRONTEND_DIR` | **Servidor único**: pantallas y API en la misma dirección, sin CORS | `frontend` |
| `FRONTEND_TOKEN` | Para bajar las pantallas del repo privado | El token de la preparación (b). Si hiciste público el repo, **borrá esta línea** |

No hace falta `CORS_ORIGINS`: con servidor único todo sale del mismo origen.

**Opcional, antes de crear el proyecto** (necesita `pip install -r requirements.txt`):

```
python herramientas/alta_cliente.py probar-base   # pega la cadena en una entrada oculta, no se guarda
python herramientas/alta_cliente.py migrar        # crea las tablas ya (si no, se crean al primer arranque)
```

`probar-base` avisa si la base **ya tiene usuarios** (señal de que te equivocaste de base).

### SECRET_KEY sin Python

En Windows, abrí **PowerShell** y pegá:

```powershell
$b = New-Object byte[] 48; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); [Convert]::ToBase64String($b)
```

---

## 3. Crear el proyecto en Vercel (10 min)

1. Entrá a https://vercel.com → botón **Add New…** (arriba a la derecha) → **Project**.
2. En *Import Git Repository*, buscá **Backend-Ferreteria** → **Import**. (Se puede importar el
   mismo repo muchas veces: cada importación es un proyecto distinto.)
3. Pantalla *Configure Project*:
   - **Project Name**: `sail-<cliente>` (el mismo que en Neon). Esto define la dirección:
     `https://sail-<cliente>.vercel.app`.
   - **Framework Preset**: **Other**. **Root Directory**: `./` (no tocar).
   - *Build and Output Settings*: **no tocar** (el repo ya trae `vercel.json` con el build).
   - Desplegá **Environment Variables**, hacé clic en el primer casillero **Key** y **pegá el
     bloque entero** del paso 2: Vercel lo separa en filas solo. Reemplazá `DATABASE_URL` por la
     cadena de Neon y `FRONTEND_TOKEN` por el token (o borrá esa fila).
   - **Deploy**. Tarda 1 a 2 minutos. En el log del build tiene que aparecer
     `SAIL: frontend listo (NN archivos).`
4. Cuando termina, **Settings** → **Functions** → **Function Region** → elegí **São Paulo, Brazil
   (gru1)** (cerca de la base) → **Save**. Después **Deployments** → en el último, menú **⋯** →
   **Redeploy** para que tome la región.

> Detalle técnico: `vercel.json` corre `herramientas/vercel_build.sh`, que con `FRONTEND_DIR`
> baja el frontend (`api.github.com/repos/VarDevCoder/Frontend-Ferreteria/tarball/main`) a
> `frontend/` y lo incluye en la función (`includeFiles`). Sin `FRONTEND_DIR` no hace nada (así
> sigue `ankor-backend`). El primer arranque aplica las migraciones (`api/index.py`).

---

## 4. Verificar (2 min)

```
python herramientas/alta_cliente.py verificar https://sail-ferreteria-san-jose.vercel.app
```

Tiene que decir:

```
  [OK] API en línea (salud: HTTP 200)
  [OK] La demo NO está activa (correcto para un cliente real)
  [OK] Las pantallas se ven en / (servidor único)
  [OK] El frontend usa la API de su mismo origen
  [ATENCIÓN] Falta la configuración inicial: hacela YA (...)
```

Sin Python: abrí en el navegador `https://sail-<cliente>.vercel.app/api/v1/salud` (tiene que
decir `"status":"ok"`) y `https://sail-<cliente>.vercel.app/` (tiene que aparecer la pantalla
**Configuración inicial**).

La **primera** vez puede tardar hasta un minuto (crea las tablas). Si da error, ver
[Problemas comunes](#problemas-comunes).

---

## 5. Configuración inicial y administrador del cliente (5 min)

**Hacelo enseguida del paso 4**: mientras la base no tenga usuarios, *cualquiera* que conozca la
dirección podría completar este paso y quedarse como administrador.

1. Abrí `https://sail-<cliente>.vercel.app` — aparece **Configuración inicial**.
2. Completá con el cliente (o con sus datos):
   - **Datos de la ferretería**: nombre comercial, razón social, **RUC**, teléfono, email,
     dirección, ciudad, moneda (Guaraní), IVA (10 %), margen de ganancia por defecto, pie del ticket.
   - **Usuario administrador**: nombre, email y contraseña (mínimo 8). Lo ideal es que el
     **cliente escriba su contraseña** él mismo. Si la ponés vos, pedile que la cambie al entrar
     (pie del menú → *Cambiar contraseña*).
3. **Crear y empezar**. Entra directo al sistema.
4. Desde ahí, el cliente (admin) da de alta a su personal en **Gestión → Usuarios**, carga
   productos y el stock inicial (ver el README del frontend, "Instalar para una ferretería nueva").

Corré otra vez `verificar`: ahora tiene que decir *Configuración inicial hecha*.

---

## 6. Dominio propio (opcional)

Por ejemplo `sistema.ferreteriasanjose.com.py` o un subdominio tuyo como `sanjose.sail.com.py`.

1. Vercel → el proyecto → **Settings** → **Domains** → escribí el dominio → **Add**.
2. Vercel muestra qué registro DNS crear. Para un subdominio es un **CNAME**:
   - *Nombre*: `sistema` (o `sanjose`) · *Valor*: el que indica Vercel (del estilo `cname.vercel-dns.com`).
   - Se carga en el panel de quien administra el dominio (para `.com.py`, el proveedor donde se
     registró, por ejemplo NIC.py o el hosting del cliente).
3. Esperá a que Vercel muestre **Valid Configuration** (minutos a unas horas). El certificado
   HTTPS lo pone Vercel solo.
4. Listo: con servidor único **no hay que cambiar nada más** (ni CORS ni el frontend).

---

## 7. Actualizaciones: cómo funcionan y qué riesgo tienen

**Cómo es hoy:** todos los proyectos de Vercel están conectados al mismo repo. Un `git push` a
`main` del backend **redespliega a la vez la demo y a todos los clientes**, y cada uno aplica las
migraciones de la base al arrancar. El frontend se baja en cada deploy, así que también se
actualiza.

- Un cambio **solo en el frontend** no dispara deploys de los clientes: hay que redeployar cada
  proyecto (*Deployments* → **⋯** → **Redeploy**) o esperar al próximo push del backend.

**Riesgos:**

1. **Un error llega a todos los clientes al mismo tiempo.** Si una versión tiene un bug, todas las
   ferreterías lo sufren juntas, en horario de atención.
2. **Las migraciones no tienen vuelta atrás automática.** Vercel permite volver a la versión
   anterior del código (*Instant Rollback*), pero **la base ya quedó migrada**. Si la migración
   borró o transformó datos, volver el código no los devuelve; y el código viejo con la base
   nueva puede fallar.
3. **Una migración pesada** en una base grande puede pasarse del tiempo máximo de la función
   (60 s) en el primer arranque; el lock de Postgres evita que dos instancias migren a la vez,
   pero el cliente ve errores hasta que termina.
4. **El frontend sale de `main`** en el momento del build: si el frontend publica algo que necesita
   un backend más nuevo, un cliente redeployado puede quedar desparejo.

**Recomendación (cuando haya más de 2 o 3 clientes):** actualizar por etapas.

1. Crear en GitHub una rama **`estable`** (en el backend) y, en cada proyecto de **cliente**,
   Vercel → **Settings** → **Environments** → **Production** → *Branch Tracking* (en paneles
   anteriores: *Settings* → *Git* → *Production Branch*) = `estable`. La demo sigue en `main`.
2. Cada versión nueva va primero a `main` → se prueba en la demo (`ankor-backend`) un par de días.
3. Si anda bien: llevar `estable` a la misma versión (fast-forward) → se actualizan los clientes.
   Fijar también `FRONTEND_REF` (variable de Vercel) a un tag o commit del frontend probado.
4. Antes de una versión con migraciones, **hacer una copia** de cada base (sección 8) y avisar a
   los clientes; mejor fuera del horario de atención.

---

## 8. Copias de seguridad y restauración

### Nivel 1 — lo que trae Neon (automático)

Neon guarda el historial de la base y permite **volver a cualquier momento** dentro de su ventana
de historial (en el plan gratis son pocas horas; en los pagos, días: revisá tu plan).

- **Restaurar a un momento:** Neon → el proyecto del cliente → **Backup & Restore** (en paneles
  anteriores: *Restore* o *Branches*) → elegí fecha y hora → Neon muestra una vista previa →
  **Restore**. Conviene antes crear una rama de respaldo del estado actual (Neon lo ofrece en el
  mismo paso).
- Es el camino para "borré algo sin querer hace un rato".

### Nivel 2 — copias propias (recomendado: semanal y antes de cada actualización)

Necesita las herramientas de PostgreSQL en tu PC (instalador de https://www.postgresql.org/download/windows/,
alcanza con *Command Line Tools*). Usá la cadena **directa** de Neon (sin `-pooler`: en
*Connect*, desactivá *Connection pooling*).

```
pg_dump --format=custom --no-owner --no-acl --dbname="postgresql://...neon.tech/neondb?sslmode=require" --file=sail-sanjose-2026-10-10.dump
```

Guardá los `.dump` en un lugar seguro y **fuera de Neon** (un disco y una nube distinta).
Contienen todos los datos del cliente: tratalos como confidenciales.

**Restaurar una copia** (la forma segura, sin pisar la base en uso):

1. En Neon, crear una base nueva para la restauración (*Branches* → *Create branch* vacía, o un
   proyecto nuevo `sail-<cliente>-restaurada`).
2. `pg_restore --no-owner --no-acl --dbname="<cadena directa de la base nueva>" sail-sanjose-2026-10-10.dump`
3. Revisar que estén los datos (podés crear un proyecto de Vercel temporal apuntando ahí).
4. En el proyecto de Vercel del cliente, cambiar `DATABASE_URL` por la cadena (`-pooler`) de la
   base restaurada → **Redeploy**. La base vieja queda como respaldo hasta que confirmes.

> Pendiente sugerido: automatizar el Nivel 2 con una tarea programada (GitHub Actions, cuando la
> cuenta esté habilitada) que haga `pg_dump` de cada cliente cada noche y lo guarde cifrado.

---

## 9. Baja de un cliente

1. **Copia final**: `pg_dump` (sección 8) y entregásela al cliente si la pide (sus datos son suyos).
   Guardá una copia el tiempo que diga tu contrato (por ejemplo, 90 días) y después borrala.
2. **Vercel** → el proyecto → **Settings** → **General** → abajo de todo **Delete Project**.
   (Si tenía dominio propio, se libera solo; avisale al cliente que borre el registro DNS.)
3. **Neon** → el proyecto → **Settings** → **Delete project**.
4. Si fue un token o una cuenta compartida solo para ese cliente, revocala.
5. Marcá la baja en tu planilla.

Para **suspender** por falta de pago sin borrar nada: Vercel → **Settings** → **General** →
**Pause Project** (si tu plan lo ofrece) o quitar el dominio. La base queda intacta.

---

## 10. Tu planilla de clientes

Una fila por cliente, **sin contraseñas ni cadenas de conexión**:

| Cliente | RUC | Proyecto Vercel | Proyecto Neon | Dirección | Alta | Plan / vence | Último backup propio | Notas |
|---|---|---|---|---|---|---|---|---|

---

## Problemas comunes

| Qué pasa | Por qué | Qué hacer |
|---|---|---|
| El build falla con `no se pudo bajar el frontend` | El repo del frontend es privado y falta `FRONTEND_TOKEN`, o el token venció | Revisar la variable (preparación 3) y **Redeploy** |
| `/` muestra `{"status":"ok"...}` en vez de la pantalla | Falta `FRONTEND_DIR=frontend` | Agregarla en *Settings* → *Environment Variables* y **Redeploy** |
| Error 500 `FUNCTION_INVOCATION_FAILED` | La app no arrancó | Vercel → *Logs*: si dice `FRONTEND_DIR=... no tiene index.html`, el build no bajó el frontend; si dice algo de conexión, revisar `DATABASE_URL` |
| La primera carga tarda | Neon "duerme" la base cuando no se usa y la despierta al primer pedido; o se están creando las tablas | Esperar; en planes pagos se puede desactivar la suspensión |
| `verificar` dice que la demo está activa | `SEED_DEMO=true` o falta | Poner `SEED_DEMO=false` y **Redeploy**. Si alguien ya entró con usuarios demo, borrarlos o rehacer la base |
| Cambié una variable y no se nota | Las variables se leen al desplegar | **Redeploy** |

---

## Recomendación: ¿un solo despliegue multiempresa más adelante?

**Hoy:** un proyecto de Vercel + una base de Neon por cliente. **Ventajas:** aislamiento total de
datos, copia y restauración por cliente, baja limpia, un cliente grande no afecta a otro, y el
código ya está hecho así (una sola fila en `empresa`, sin `empresa_id`). **Costos:** ~30 minutos
manuales por alta, N proyectos para mirar, y las actualizaciones llegan a todos juntos.

Opciones para más adelante:

| Opción | Qué es | Cambio en el código | Riesgo |
|---|---|---|---|
| **A. Seguir como hoy** + automatizar el alta | Un script que cree el proyecto de Neon y el de Vercel por sus APIs | Ninguno en la app | Bajo |
| **B. Un despliegue, una base por cliente** | Un solo backend; según el subdominio (`sanjose.sail.com.py`) elige la base del cliente | Medio: sesión de base por pedido, migrar N bases al actualizar, alta de clientes en una tabla central | Medio |
| **C. Multiempresa en tablas compartidas** | Una sola base con `empresa_id` en cada tabla | Grande: todas las tablas, consultas, numeraciones, permisos y tests | Alto: un error en un filtro muestra datos de otra ferretería |

**Recomendación:** quedarse con **A** mientras sean pocos clientes (hasta unos 10-15),
automatizando el alta y adoptando ya las **actualizaciones por etapas** (sección 7). Si el número
crece, pasar a **B**, que mantiene el aislamiento por base (y las copias por cliente) con un solo
despliegue. **C** solo conviene con cientos de clientes chicos, y exige antes resolver la
concurrencia (varias cajas) y una auditoría de seguridad. Cualquier camino sirve también para la
versión Windows, que es "una instancia por PC" y usa el mismo código.
