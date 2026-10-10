# SAIL instalado en Windows (licencia perpetua)

**En simple:** un solo archivo, `SAIL-Instalador-x.y.z.exe`, deja SAIL funcionando en la PC de
la ferretería sin que el cliente tenga que saber nada: doble clic → *Siguiente* → *Instalar*.
Queda un acceso directo **SAIL** en el escritorio que abre `http://localhost:7245` en el
navegador. No necesita internet para funcionar.

```
 PC de la ferretería
 ├─ Servicio "SAIL"             → Python embebido + backend + pantallas (servidor único), puerto 7245
 ├─ Servicio "SAIL-PostgreSQL"  → PostgreSQL 17 portátil, solo en la PC (127.0.0.1:7246)
 ├─ Tarea "SAIL - Copia de seguridad diaria" → pg_dump a C:\ProgramData\SAIL\copias (30 días)
 └─ Acceso directo "SAIL"       → http://localhost:7245
```

| Qué | Dónde |
|---|---|
| Programa (se reemplaza al actualizar) | `C:\Program Files\SAIL` (`python\`, `backend\`, `frontend\`, `pgsql\`, `servicio\`, `scripts\`) |
| **Datos** (nunca los borra el instalador) | `C:\ProgramData\SAIL` |
| Base de datos | `C:\ProgramData\SAIL\base-de-datos` |
| Copias de seguridad | `C:\ProgramData\SAIL\copias` |
| Configuración y claves (confidencial) | `C:\ProgramData\SAIL\config\sail.env` |
| Registros para soporte | `C:\ProgramData\SAIL\logs` (`instalacion.log`, `copias.log`, los del servicio `*.out.log`/`*.err.log`, `postgres\`) |

---

## 1. Cómo se construye el instalador (dueño)

El instalador se arma y **se prueba solo** en GitHub Actions, en una Windows limpia.

1. GitHub → repo **Backend-Ferreteria** → pestaña **Actions**.
2. A la izquierda, **Instalador Windows** → botón **Run workflow** (a la derecha).
   - *Versión*: por ejemplo `1.0.1` (vacío = la de `instalador/windows/VERSION`). Subí el número
     en cada versión que entregues.
   - *Rama del frontend*: `main` salvo que quieras otra.
   - **Run workflow**.
3. Tarda unos 20 a 30 minutos. Son dos pasos:
   - **Construir el instalador**: baja Python, PostgreSQL, WinSW y el runtime de Visual C++, junta
     el backend y las pantallas y compila con Inno Setup.
   - **Probar en Windows limpio**: lo instala en silencio y verifica servicios, pantallas, API,
     configuración inicial y login, copia y restauración, actualización, desinstalación y
     reinstalación con los datos intactos. El resumen aparece en la página de la ejecución.
4. Cuando los dos pasos están en verde, en la misma página, abajo, sección **Artifacts** →
   **SAIL-Instalador-x.y.z** → se baja un `.zip` con el `.exe`, su huella SHA-256 y
   `VERSION.txt` (qué versiones lleva adentro). Los artefactos duran 90 días: guardá el `.exe` de
   cada versión que entregues.

**Requisitos de la cuenta de GitHub:**
- **Actions habilitado.** Hoy la cuenta muestra *"The job was not started because your account is
  locked due to a billing issue"*: hay que regularizarlo en GitHub → *Settings* → *Billing and
  plans*. Sin eso no corre ningún workflow (tampoco el CI).
- **Acceso al frontend.** `Frontend-Ferreteria` es privado: crear el secreto
  **`FRONTEND_REPO_TOKEN`** en Backend-Ferreteria → *Settings* → *Secrets and variables* →
  *Actions* → **New repository secret**, con un token *fine-grained* de solo lectura
  (*Contents: Read-only*) sobre `Frontend-Ferreteria` (el mismo token sirve para la nube, ver
  `ALTA-CLIENTE-NUBE.md`). Si el frontend se hace público, no hace falta.

> Detalle técnico: `.github/workflows/instalador-windows.yml` (también corre solo en cada push a
> `main` que toque `instalador/windows/`, `servir.py` o el workflow), `instalador/windows/construir.ps1`,
> `sail.iss` y `probar.ps1`. Versiones incluidas: Python 3.12.10 embebido, PostgreSQL 17 (la
> última 17.x disponible en EnterpriseDB), WinSW 2.12.0.

---

## 2. Instalar en la PC del cliente

Requisitos: Windows 10 u 11 de 64 bits, un usuario administrador, ~600 MB libres.

1. Copiar `SAIL-Instalador-x.y.z.exe` a la PC (pendrive o descarga) y hacer doble clic.
   - Windows puede mostrar **"Windows protegió su PC"** (SmartScreen) porque el instalador no
     está firmado: *Más información* → **Ejecutar de todas formas**. (Ver riesgos.)
2. *Siguiente* → elegir si se quiere el acceso directo en el escritorio y si **otras PCs de la red**
   van a usar SAIL (por ejemplo, una segunda caja) → **Instalar**.
3. Al final dice *Configurando la base de datos y los servicios* (1 o 2 minutos) y abre SAIL.
4. Aparece **Configuración inicial**: datos de la ferretería y su usuario administrador
   (igual que en la nube). Listo.

**Otras PCs de la red** (si se marcó la opción): abren `http://<nombre-o-IP-de-la-PC>:7245`
(por ejemplo `http://192.168.1.10:7245`). Conviene fijar la IP de esa PC en el router.

**Instalación silenciosa** (técnicos): `SAIL-Instalador-x.y.z.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
(agregar `/TASKS="escritorio,red"` para habilitar la red). Devuelve 0 si todo salió bien y 100+
si falló la configuración (ver `C:\ProgramData\SAIL\logs\instalacion.log`).

## 3. Actualizar

**Correr un instalador más nuevo** sobre el que está. Conserva los datos y la configuración:

1. Frena los servicios, reemplaza el programa (`C:\Program Files\SAIL`) y vuelve a registrar los
   servicios.
2. **Antes de arrancar la versión nueva hace una copia de seguridad**
   (`copias\sail-<fecha>-antes-de-instalar-x.y.z.dump`).
3. SAIL arranca y **actualiza la base solo** (migraciones de Alembic, igual que en la nube).

El cliente elige cuándo actualizar (licencia perpetua). Como la base se migra al arrancar, **no
se puede volver a una versión anterior** instalando un `.exe` viejo sobre una base ya migrada:
para volver atrás hay que restaurar la copia `antes-de-instalar` con la versión anterior.

> Regla para el equipo: el instalador trae **siempre PostgreSQL 17**. Si algún día se cambia de
> versión mayor, hay que agregar una migración de datos (`pg_upgrade` o `pg_dump`/restore): el
> instalador se niega a seguir si los datos son de otra versión mayor, sin tocarlos.

## 4. Copias de seguridad

- **Automáticas**: todos los días a las 13:00 (si la PC estaba apagada, apenas se prende), en
  `C:\ProgramData\SAIL\copias`. Se guardan las de los **últimos 30 días** (y siempre las 7 más
  nuevas). Cada copia se verifica (`pg_restore --list`).
- **Llevarlas afuera**: las copias están en la misma PC; si se rompe el disco o hay un robo, se
  pierden con ella. Recomendación al cliente: copiar la carpeta `copias` a un pendrive o a una nube
  una vez por semana (o configurar OneDrive/Google Drive sobre esa carpeta).
- **Copia ahora**: PowerShell como administrador →
  `powershell -ExecutionPolicy Bypass -File "C:\Program Files\SAIL\scripts\copia_seguridad.ps1"`
  (o *Programador de tareas* → *SAIL - Copia de seguridad diaria* → *Ejecutar*).

**Restaurar** (técnico, como administrador, con SAIL cerrado en las cajas):

```
powershell -ExecutionPolicy Bypass -File "C:\Program Files\SAIL\scripts\restaurar_copia.ps1"
```

Sin parámetros lista las copias; con `-Archivo "<ruta>"` restaura esa (pide escribir `SI`). Antes
de restaurar hace una copia `antes-de-restaurar` del estado actual.

## 5. Desinstalar

*Configuración de Windows* → *Aplicaciones* → **SAIL** → *Desinstalar* (o el acceso del menú
Inicio). Quita los servicios, la tarea y el programa, pero **no borra los datos**
(`C:\ProgramData\SAIL`). Reinstalar SAIL los encuentra y sigue todo como estaba. Para borrar
todo definitivamente: guardar una copia de `copias\` y después borrar esa carpeta a mano.

## 6. Problemas comunes

| Qué pasa | Qué hacer |
|---|---|
| El acceso directo abre "No se puede acceder a este sitio" | Esperar 1 minuto después de prender la PC. Si sigue: *Servicios* (Win+R → `services.msc`) → **SAIL** y **SAIL-PostgreSQL** tienen que estar *En ejecución*; si no, botón derecho → *Iniciar*. Ver los `*.err.log` y `*.out.log` de `C:\ProgramData\SAIL\logs` |
| Otra PC de la red no entra | Reinstalar marcando "Permitir que otras PCs de la red usen SAIL"; la red de Windows tiene que estar como **Privada**; probar con la IP |
| La instalación dice "No se pudo terminar de configurar SAIL" | Mandar `C:\ProgramData\SAIL\logs\instalacion.log` a soporte. Los datos no se tocaron |
| El antivirus bloquea `sail-servidor.exe` o `postgres.exe` | Agregar `C:\Program Files\SAIL` como excepción |

## 7. Seguridad (detalle técnico)

- PostgreSQL escucha **solo en la PC** (`listen_addresses = 'localhost'`, puerto 7246) con
  contraseñas `scram-sha-256` generadas al azar en la instalación.
- Los servicios corren como **NetworkService** (no como SYSTEM). `C:\ProgramData\SAIL` solo es
  accesible por administradores, SYSTEM y esa cuenta.
- `IP_DESDE_X_FORWARDED_FOR=false` y uvicorn con `proxy_headers=False`: en una PC sin proxy nadie
  puede esquivar el bloqueo de login inventando la cabecera `X-Forwarded-For`.
- `SECRET_KEY` propia de cada instalación, generada al azar.
- Con acceso desde la red, el tráfico va por **HTTP sin cifrar** dentro de la red local. Para una
  red de confianza (la del local) es aceptable; no exponer el puerto 7245 a internet.
