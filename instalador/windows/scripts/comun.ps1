# Funciones comunes de los scripts de SAIL en Windows (se cargan con ". comun.ps1").
# Compatibles con Windows PowerShell 5.1 (el que trae Windows 10/11).

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$SAIL_SERVICIO = 'SAIL'
$SAIL_SERVICIO_PG = 'SAIL-PostgreSQL'
$SAIL_TAREA_COPIA = 'SAIL - Copia de seguridad diaria'
$SAIL_REGLA_FIREWALL = 'SAIL (red local)'
$SAIL_PG_MAYOR = '17'   # versión mayor de PostgreSQL incluida: los datos solo sirven con esta

# SIDs (no nombres: en un Windows en castellano "Administrators" se llama "Administradores").
$SID_ADMINS = '*S-1-5-32-544'
$SID_SYSTEM = '*S-1-5-18'
$SID_NETWORK_SERVICE = '*S-1-5-20'
$CUENTA_SERVICIO = 'NT AUTHORITY\NetworkService'

function Get-SailDatos {
    if ($env:SAIL_DATOS) { return $env:SAIL_DATOS }
    return (Join-Path $env:ProgramData 'SAIL')
}

$script:SailLog = $null

function Iniciar-Log([string]$Nombre) {
    $logs = Join-Path (Get-SailDatos) 'logs'
    New-Item -ItemType Directory -Force -Path $logs | Out-Null
    $script:SailLog = Join-Path $logs $Nombre
}

function Log([string]$Mensaje) {
    $linea = '{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Mensaje
    Write-Host $linea
    if ($script:SailLog) { Add-Content -Path $script:SailLog -Value $linea -Encoding UTF8 }
}

# Ejecuta un programa, manda su salida al log y falla si devuelve error.
function Ejecutar {
    param([string]$Programa, [string[]]$Argumentos, [switch]$PermitirError)
    Log ("> {0} {1}" -f (Split-Path $Programa -Leaf), ($Argumentos -join ' '))
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Programa @Argumentos 2>&1 | ForEach-Object { Log ("  " + $_) }
        $codigo = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $anterior
    }
    if ($codigo -ne 0 -and -not $PermitirError) {
        throw ("{0} terminó con error {1}" -f (Split-Path $Programa -Leaf), $codigo)
    }
    return $codigo
}

# Lee el archivo NOMBRE=valor de configuración.
function Leer-Config([string]$Ruta) {
    $config = @{}
    if (Test-Path $Ruta) {
        foreach ($linea in [IO.File]::ReadAllLines($Ruta)) {
            $l = $linea.Trim().TrimStart([char]0xFEFF)
            if ($l -eq '' -or $l.StartsWith('#') -or -not $l.Contains('=')) { continue }
            $i = $l.IndexOf('=')
            $config[$l.Substring(0, $i).Trim()] = $l.Substring($i + 1).Trim()
        }
    }
    return $config
}

# Escribe UTF-8 sin BOM (lo leen Python y PostgreSQL).
function Escribir-Texto([string]$Ruta, [string]$Texto) {
    [IO.File]::WriteAllText($Ruta, $Texto, (New-Object Text.UTF8Encoding $false))
}

function Nueva-Clave([int]$Bytes = 24) {
    $b = New-Object byte[] $Bytes
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($b)
    $rng.Dispose()
    return (($b | ForEach-Object { $_.ToString('x2') }) -join '')
}

function Existe-Servicio([string]$Nombre) {
    return [bool](Get-Service -Name $Nombre -ErrorAction SilentlyContinue)
}

function Esperar-Postgres([string]$Bin, [string]$Puerto, [int]$Segundos = 90) {
    $limite = (Get-Date).AddSeconds($Segundos)
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        while ((Get-Date) -lt $limite) {
            & (Join-Path $Bin 'pg_isready.exe') -h 127.0.0.1 -p $Puerto -q 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { return }
            Start-Sleep -Seconds 2
        }
    } finally {
        $ErrorActionPreference = $anterior
    }
    throw "PostgreSQL no respondió en el puerto $Puerto"
}

function Esperar-Http([string]$Url, [int]$Segundos = 180) {
    $limite = (Get-Date).AddSeconds($Segundos)
    while ((Get-Date) -lt $limite) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
            if ($r.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Seconds 2
    }
    throw "SAIL no respondió en $Url"
}

# Copia de seguridad con pg_dump (formato custom). Devuelve la ruta del archivo.
function Hacer-Copia([string]$AppDir, [hashtable]$Config, [string]$Motivo = '') {
    $datos = Get-SailDatos
    $copias = Join-Path $datos 'copias'
    New-Item -ItemType Directory -Force -Path $copias | Out-Null
    $sufijo = ''
    if ($Motivo) { $sufijo = '-' + $Motivo }
    $archivo = Join-Path $copias ('sail-{0}{1}.dump' -f (Get-Date -Format 'yyyy-MM-dd_HHmmss'), $sufijo)
    $bin = Join-Path $AppDir 'pgsql\bin'
    $env:PGPASSWORD = $Config['PG_SAIL_PASSWORD']
    try {
        Ejecutar (Join-Path $bin 'pg_dump.exe') @('-h', '127.0.0.1', '-p', $Config['PG_PUERTO'], '-U', 'sail', '-d', 'sail', '--format=custom', '--no-owner', '--no-acl', '-f', $archivo) | Out-Null
        # Que se pueda leer: si el archivo está roto, pg_restore --list falla.
        Ejecutar (Join-Path $bin 'pg_restore.exe') @('--list', $archivo) | Out-Null
    } finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
    if ((Get-Item $archivo).Length -le 0) { throw "La copia $archivo quedó vacía" }
    Log ("Copia hecha: {0} ({1:N0} KB)" -f $archivo, ((Get-Item $archivo).Length / 1KB))
    return $archivo
}
