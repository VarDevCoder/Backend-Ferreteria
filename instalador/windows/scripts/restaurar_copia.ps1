# Restaura una copia de seguridad de SAIL (usar como administrador, con SAIL cerrado en las cajas).
#
# En simple: vuelve la base de datos al estado de una copia. ANTES hace una copia
# del estado actual ("antes-de-restaurar"), por si hay que deshacer.
#
#   powershell -ExecutionPolicy Bypass -File "C:\Program Files\SAIL\scripts\restaurar_copia.ps1" -Archivo "C:\ProgramData\SAIL\copias\sail-2026-10-10_130000.dump"
#
# Sin -Archivo muestra las copias disponibles.
param([string]$Archivo = '', [switch]$SinConfirmar)

. (Join-Path $PSScriptRoot 'comun.ps1')

$AppDir = Split-Path $PSScriptRoot -Parent
$bin = Join-Path $AppDir 'pgsql\bin'
try {
    Iniciar-Log 'copias.log'
    if (-not $Archivo) {
        Write-Host 'Copias disponibles (la más nueva primero):'
        Get-ChildItem -Path (Join-Path (Get-SailDatos) 'copias') -Filter 'sail-*.dump' | Sort-Object LastWriteTime -Descending |
            ForEach-Object { Write-Host ('  {0}   {1:N0} KB' -f $_.FullName, ($_.Length / 1KB)) }
        Write-Host 'Volvé a correr el script con -Archivo "<ruta de la copia>".'
        exit 0
    }
    if (-not (Test-Path $Archivo)) { throw "No existe la copia $Archivo" }
    if (-not $SinConfirmar) {
        $r = Read-Host "Se va a reemplazar TODA la base de SAIL por la copia $Archivo. Escribí SI para seguir"
        if ($r -ne 'SI') { Write-Host 'Cancelado.'; exit 0 }
    }
    $config = Leer-Config (Join-Path (Get-SailDatos) 'config\sail.env')
    Log "=== Restaurando $Archivo ==="
    Hacer-Copia $AppDir $config 'antes-de-restaurar' | Out-Null

    Stop-Service -Name $SAIL_SERVICIO -Force
    $env:PGPASSWORD = $config['PG_SUPERUSUARIO_PASSWORD']
    try {
        $psql = Join-Path $bin 'psql.exe'
        $comun = @('-h', '127.0.0.1', '-p', $config['PG_PUERTO'], '-U', 'postgres', '-v', 'ON_ERROR_STOP=1')
        Ejecutar $psql ($comun + @('-d', 'postgres', '-c', "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'sail' AND pid <> pg_backend_pid()")) | Out-Null
        Ejecutar $psql ($comun + @('-d', 'postgres', '-c', 'DROP DATABASE IF EXISTS sail')) | Out-Null
        Ejecutar $psql ($comun + @('-d', 'postgres', '-c', "CREATE DATABASE sail OWNER sail ENCODING 'UTF8' TEMPLATE template0")) | Out-Null
        Ejecutar (Join-Path $bin 'pg_restore.exe') @('-h', '127.0.0.1', '-p', $config['PG_PUERTO'], '-U', 'postgres', '-d', 'sail',
            '--no-owner', '--role=sail', '--exit-on-error', $Archivo) | Out-Null
    } finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
    Start-Service -Name $SAIL_SERVICIO
    Esperar-Http "http://127.0.0.1:$($config['SAIL_PORT'])/api/v1/salud" 300
    Log '=== Restauración terminada: SAIL en marcha con los datos de la copia ==='
    exit 0
} catch {
    Log "ERROR al restaurar: $($_.Exception.Message)"
    Log 'Si SAIL quedó detenido: Inicio -> Servicios -> SAIL -> Iniciar. La copia "antes-de-restaurar" tiene el estado anterior.'
    exit 1
}
