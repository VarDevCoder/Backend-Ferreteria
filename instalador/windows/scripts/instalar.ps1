# Configura SAIL después de copiar los archivos (lo llama el instalador, como administrador).
#
# En simple: prepara la carpeta de datos (C:\ProgramData\SAIL), crea la base de
# datos la primera vez, registra los dos servicios de Windows (PostgreSQL y SAIL)
# para que arranquen con la PC, programa la copia de seguridad diaria y deja
# SAIL andando en http://localhost:7245.
#
# Es idempotente: al actualizar (correr un instalador más nuevo) conserva los
# datos y la configuración, hace una copia de seguridad antes de arrancar la
# versión nueva y SAIL migra la base solo al iniciar.
param(
    [Parameter(Mandatory = $true)][string]$AppDir,
    [string]$Version = '',
    [int]$Puerto = 7245,
    [int]$PuertoPg = 7246,
    [switch]$AccesoRed
)

. (Join-Path $PSScriptRoot 'comun.ps1')

$datos = Get-SailDatos
$dirConfig = Join-Path $datos 'config'
$dirBase = Join-Path $datos 'base-de-datos'
$dirLogs = Join-Path $datos 'logs'
$dirCopias = Join-Path $datos 'copias'
$archivoConfig = Join-Path $dirConfig 'sail.env'
$bin = Join-Path $AppDir 'pgsql\bin'

function Preparar-Carpetas {
    foreach ($d in @($datos, $dirConfig, $dirBase, $dirLogs, (Join-Path $dirLogs 'postgres'), $dirCopias)) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }
    # Solo administradores, SYSTEM y la cuenta de los servicios (NetworkService):
    # la configuración tiene las claves de la base y las copias tienen todos los datos.
    Ejecutar icacls.exe @($datos, '/inheritance:r', '/grant:r', "$($SID_ADMINS):(OI)(CI)F", "$($SID_SYSTEM):(OI)(CI)F") | Out-Null
    Ejecutar icacls.exe @($dirBase, '/grant', "$($SID_NETWORK_SERVICE):(OI)(CI)F") | Out-Null
    Ejecutar icacls.exe @($dirLogs, '/grant', "$($SID_NETWORK_SERVICE):(OI)(CI)M") | Out-Null
    Ejecutar icacls.exe @($dirConfig, '/grant', "$($SID_NETWORK_SERVICE):(OI)(CI)RX") | Out-Null
    $leeme = @"
SAIL - carpeta de datos
=======================
base-de-datos\  la base de datos de PostgreSQL (NO borrar ni tocar a mano)
copias\         copias de seguridad diarias (se guardan las de los ultimos 30 dias)
config\         configuracion y claves (confidencial)
logs\           registros para soporte

Desinstalar SAIL NO borra esta carpeta: los datos quedan para una reinstalacion.
Para borrar todo definitivamente, primero guarde una copia de "copias\" y despues
borre esta carpeta a mano.
"@
    Escribir-Texto (Join-Path $datos 'LEEME.txt') $leeme
}

function Preparar-Config {
    $config = Leer-Config $archivoConfig
    $nueva = $config.Count -eq 0
    if (-not $config['PG_SUPERUSUARIO_PASSWORD']) { $config['PG_SUPERUSUARIO_PASSWORD'] = Nueva-Clave }
    if (-not $config['PG_SAIL_PASSWORD']) { $config['PG_SAIL_PASSWORD'] = Nueva-Clave }
    if (-not $config['SECRET_KEY']) { $config['SECRET_KEY'] = Nueva-Clave 48 }
    if (-not $config['PG_PUERTO']) { $config['PG_PUERTO'] = "$PuertoPg" }
    $config['DATABASE_URL'] = 'postgresql+pg8000://sail:{0}@127.0.0.1:{1}/sail' -f $config['PG_SAIL_PASSWORD'], $config['PG_PUERTO']
    $config['ENVIRONMENT'] = 'production'
    $config['SEED_DEMO'] = 'false'
    $config['IP_DESDE_X_FORWARDED_FOR'] = 'false'   # PC sin proxy: no confiar en X-Forwarded-For
    if (-not $config['APP_NAME']) { $config['APP_NAME'] = 'SAIL' }
    $config['SAIL_PORT'] = "$Puerto"
    if ($AccesoRed) { $config['SAIL_HOST'] = '0.0.0.0' } else { $config['SAIL_HOST'] = '127.0.0.1' }

    $orden = @('DATABASE_URL', 'SECRET_KEY', 'ENVIRONMENT', 'SEED_DEMO', 'APP_NAME', 'IP_DESDE_X_FORWARDED_FOR',
               'SAIL_HOST', 'SAIL_PORT', 'PG_PUERTO', 'PG_SAIL_PASSWORD', 'PG_SUPERUSUARIO_PASSWORD')
    $lineas = @('# Configuracion de SAIL (la escribe el instalador). CONFIDENCIAL: tiene las claves de la base.')
    foreach ($k in $orden) { $lineas += "$k=$($config[$k])" }
    foreach ($k in ($config.Keys | Sort-Object)) { if ($orden -notcontains $k) { $lineas += "$k=$($config[$k])" } }
    Escribir-Texto $archivoConfig (($lineas -join "`r`n") + "`r`n")
    if ($nueva) { Log 'Configuración nueva creada (claves generadas al azar).' } else { Log 'Configuración existente conservada.' }
    return $config
}

function Instalar-RuntimeVisualC {
    $clave = 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64'
    $rt = Get-ItemProperty -Path $clave -ErrorAction SilentlyContinue
    if ($rt -and $rt.Installed -eq 1 -and $rt.Minor -ge 30) {
        Log "Runtime de Visual C++ presente ($($rt.Version))."
        return
    }
    $redist = Join-Path $AppDir 'redist\vc_redist.x64.exe'
    Log 'Instalando el runtime de Visual C++ (lo necesita PostgreSQL)...'
    $p = Start-Process -FilePath $redist -ArgumentList '/install', '/quiet', '/norestart' -Wait -PassThru
    if (@(0, 1638, 3010) -notcontains $p.ExitCode) { throw "El runtime de Visual C++ terminó con error $($p.ExitCode)" }
}

function Consultar([hashtable]$Config, [string]$Base, [string]$Sql) {
    $env:PGPASSWORD = $Config['PG_SUPERUSUARIO_PASSWORD']
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $salida = & (Join-Path $bin 'psql.exe') -h 127.0.0.1 -p $Config['PG_PUERTO'] -U postgres -d $Base -v ON_ERROR_STOP=1 -tAc $Sql 2>&1
        $codigo = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $anterior
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
    if ($codigo -ne 0) { throw "Error en la base: $salida" }
    return ("$salida").Trim()
}

function Preparar-PostgreSQL([hashtable]$Config) {
    $versionDatos = Join-Path $dirBase 'PG_VERSION'
    if (Test-Path $versionDatos) {
        $mayor = (Get-Content $versionDatos -TotalCount 1).Trim()
        if ($mayor -ne $SAIL_PG_MAYOR) {
            throw "Los datos son de PostgreSQL $mayor y este instalador trae PostgreSQL $SAIL_PG_MAYOR. No se puede seguir sin migrar los datos: contactá a soporte. (Tus datos no se tocaron.)"
        }
        Log "Base de datos existente (PostgreSQL $mayor): se conserva."
    } else {
        Log 'Creando la base de datos (initdb)...'
        # initdb se reinicia con permisos reducidos: el usuario que instala tiene que poder escribir.
        $yo = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        Ejecutar icacls.exe @($dirBase, '/grant', "*$($yo):(OI)(CI)F") | Out-Null
        # La clave va en un temporal del usuario: initdb con permisos reducidos no puede leer config\.
        $archivoClave = [IO.Path]::GetTempFileName()
        Escribir-Texto $archivoClave $Config['PG_SUPERUSUARIO_PASSWORD']
        try {
            Ejecutar (Join-Path $bin 'initdb.exe') @('-D', $dirBase, '-U', 'postgres', "--pwfile=$archivoClave",
                '-A', 'scram-sha-256', '-E', 'UTF8', '--no-locale') | Out-Null
        } finally {
            Remove-Item $archivoClave -Force -ErrorAction SilentlyContinue
        }
        $logsPg = (Join-Path $dirLogs 'postgres').Replace('\', '/')
        $extra = @"

# --- SAIL ---
listen_addresses = 'localhost'
port = $($Config['PG_PUERTO'])
logging_collector = on
log_directory = '$logsPg'
log_filename = 'postgresql-%a.log'
log_truncate_on_rotation = on
log_rotation_age = 1d
log_rotation_size = 0
"@
        Add-Content -Path (Join-Path $dirBase 'postgresql.conf') -Value $extra -Encoding ASCII
        Ejecutar icacls.exe @($dirBase, '/remove', "*$yo") | Out-Null
    }

    # El servicio apunta a los binarios de esta versión: se vuelve a registrar siempre.
    if (Existe-Servicio $SAIL_SERVICIO_PG) {
        Stop-Service -Name $SAIL_SERVICIO_PG -Force -ErrorAction SilentlyContinue
        Ejecutar (Join-Path $bin 'pg_ctl.exe') @('unregister', '-N', $SAIL_SERVICIO_PG) -PermitirError | Out-Null
        Start-Sleep -Seconds 2
    }
    Ejecutar (Join-Path $bin 'pg_ctl.exe') @('register', '-N', $SAIL_SERVICIO_PG, '-U', $CUENTA_SERVICIO, '-D', $dirBase, '-S', 'auto') | Out-Null
    Ejecutar sc.exe @('description', $SAIL_SERVICIO_PG, 'Base de datos de SAIL (PostgreSQL)') | Out-Null
    Ejecutar sc.exe @('failure', $SAIL_SERVICIO_PG, 'reset=', '3600', 'actions=', 'restart/10000/restart/30000/restart/60000') | Out-Null
    Start-Service -Name $SAIL_SERVICIO_PG
    Esperar-Postgres $bin $Config['PG_PUERTO']
    Log 'PostgreSQL en marcha.'

    $clave = $Config['PG_SAIL_PASSWORD']
    if ((Consultar $Config 'postgres' "SELECT count(*) FROM pg_roles WHERE rolname = 'sail'") -eq '0') {
        Consultar $Config 'postgres' "CREATE ROLE sail LOGIN PASSWORD '$clave'" | Out-Null
        Log 'Usuario de base "sail" creado.'
    } else {
        Consultar $Config 'postgres' "ALTER ROLE sail LOGIN PASSWORD '$clave'" | Out-Null
    }
    if ((Consultar $Config 'postgres' "SELECT count(*) FROM pg_database WHERE datname = 'sail'") -eq '0') {
        Consultar $Config 'postgres' "CREATE DATABASE sail OWNER sail ENCODING 'UTF8' TEMPLATE template0" | Out-Null
        Log 'Base "sail" creada (vacía: al abrir SAIL aparece la configuración inicial).'
        return $false
    }
    $tablas = Consultar $Config 'sail' "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
    return ([int]$tablas -gt 0)
}

function Instalar-ServicioSail([hashtable]$Config) {
    $dirServicio = Join-Path $AppDir 'servicio'
    $exe = Join-Path $dirServicio 'sail-servidor.exe'
    $python = Join-Path $AppDir 'python\python.exe'
    $servir = Join-Path $AppDir 'backend\servir.py'
    $xml = @"
<service>
  <id>$SAIL_SERVICIO</id>
  <name>SAIL</name>
  <description>Servidor de SAIL: pantallas y API en http://localhost:$Puerto</description>
  <executable>$python</executable>
  <arguments>"$servir" --config "$archivoConfig"</arguments>
  <workingdirectory>$(Join-Path $AppDir 'backend')</workingdirectory>
  <env name="FRONTEND_DIR" value="$(Join-Path $AppDir 'frontend')"/>
  <env name="PYTHONUNBUFFERED" value="1"/>
  <env name="PYTHONDONTWRITEBYTECODE" value="1"/>
  <env name="PYTHONUTF8" value="1"/>
  <depend>$SAIL_SERVICIO_PG</depend>
  <startmode>Automatic</startmode>
  <onfailure action="restart" delay="10 sec"/>
  <onfailure action="restart" delay="30 sec"/>
  <onfailure action="restart" delay="60 sec"/>
  <resetfailure>1 hour</resetfailure>
  <stoptimeout>20 sec</stoptimeout>
  <logpath>$dirLogs</logpath>
  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>8</keepFiles>
  </log>
</service>
"@
    Escribir-Texto (Join-Path $dirServicio 'sail-servidor.xml') $xml

    $actual = Get-CimInstance Win32_Service -Filter "Name='$SAIL_SERVICIO'" -ErrorAction SilentlyContinue
    if ($actual -and ($actual.PathName -notlike "*$exe*")) {
        Log "El servicio SAIL apuntaba a otra carpeta ($($actual.PathName)): se vuelve a registrar."
        Stop-Service -Name $SAIL_SERVICIO -Force -ErrorAction SilentlyContinue
        Ejecutar sc.exe @('delete', $SAIL_SERVICIO) -PermitirError | Out-Null
        Start-Sleep -Seconds 2
        $actual = $null
    }
    if (-not $actual) {
        Ejecutar $exe @('install') | Out-Null
    } else {
        Log 'Servicio SAIL existente: se actualiza su configuración.'
    }
    # Cuenta con pocos permisos (no SYSTEM): NetworkService.
    $svc = Get-CimInstance Win32_Service -Filter "Name='$SAIL_SERVICIO'"
    $r = Invoke-CimMethod -InputObject $svc -MethodName Change -Arguments @{ StartName = $CUENTA_SERVICIO; StartPassword = '' }
    if ($r.ReturnValue -ne 0) { throw "No se pudo asignar la cuenta del servicio SAIL (error $($r.ReturnValue))" }
    Ejecutar sc.exe @('config', $SAIL_SERVICIO, 'start=', 'auto') | Out-Null
}

function Programar-Copias {
    $script = Join-Path $AppDir 'scripts\copia_seguridad.ps1'
    $accion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $script)
    $disparador = New-ScheduledTaskTrigger -Daily -At '13:00'
    $ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName $SAIL_TAREA_COPIA -Action $accion -Trigger $disparador -Settings $ajustes -Principal $principal `
        -Description 'Copia de seguridad diaria de la base de SAIL (pg_dump). Guarda las de los ultimos 30 dias en C:\ProgramData\SAIL\copias.' -Force | Out-Null
    Log "Copia diaria programada (13:00, o apenas se prenda la PC si estaba apagada)."
}

function Configurar-Firewall {
    Get-NetFirewallRule -DisplayName $SAIL_REGLA_FIREWALL -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    if ($AccesoRed) {
        New-NetFirewallRule -DisplayName $SAIL_REGLA_FIREWALL -Direction Inbound -Protocol TCP -LocalPort $Puerto `
            -Profile Private, Domain -Action Allow | Out-Null
        Log "Acceso desde otras PCs de la red local habilitado (puerto $Puerto, redes privadas)."
    }
}

try {
    Iniciar-Log 'instalacion.log'
    Log "=== Instalando SAIL $Version en $AppDir (datos en $datos) ==="
    Preparar-Carpetas
    $config = Preparar-Config
    Instalar-RuntimeVisualC
    $habiaDatos = Preparar-PostgreSQL $config
    if ($habiaDatos) {
        $motivo = 'antes-de-instalar'
        if ($Version) { $motivo = "antes-de-instalar-$Version" }
        Log 'Había datos: copia de seguridad antes de arrancar esta versión...'
        Hacer-Copia $AppDir $config $motivo | Out-Null
    }
    Instalar-ServicioSail $config
    Configurar-Firewall
    Programar-Copias
    Log 'Arrancando SAIL (la primera vez crea o actualiza las tablas)...'
    Start-Service -Name $SAIL_SERVICIO
    Esperar-Http "http://127.0.0.1:$Puerto/api/v1/salud" 300
    Log "=== SAIL $Version listo en http://localhost:$Puerto ==="
    exit 0
} catch {
    Log "ERROR: $($_.Exception.Message)"
    Log ($_.ScriptStackTrace)
    exit 1
}
