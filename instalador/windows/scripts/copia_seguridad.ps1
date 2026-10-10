# Copia de seguridad de la base de SAIL (la corre la tarea programada todos los días).
#
# En simple: guarda una copia completa de los datos en C:\ProgramData\SAIL\copias
# (un archivo .dump por día) y borra las de más de 30 días, dejando siempre al
# menos las 7 más nuevas. Para hacer una copia ahora: abrir PowerShell como
# administrador y correr este script.
#
# Detalle: pg_dump --format=custom (se restaura con restaurar_copia.ps1 o pg_restore).
param([string]$Motivo = '', [int]$Dias = 30, [int]$Minimo = 7)

. (Join-Path $PSScriptRoot 'comun.ps1')

$AppDir = Split-Path $PSScriptRoot -Parent
try {
    Iniciar-Log 'copias.log'
    $config = Leer-Config (Join-Path (Get-SailDatos) 'config\sail.env')
    if (-not $config['PG_SAIL_PASSWORD']) { throw 'No se encontró la configuración de SAIL (C:\ProgramData\SAIL\config\sail.env)' }
    if ((Get-Service -Name $SAIL_SERVICIO_PG -ErrorAction SilentlyContinue).Status -ne 'Running') {
        Log 'La base no estaba corriendo: se arranca para la copia.'
        Start-Service -Name $SAIL_SERVICIO_PG
        Esperar-Postgres (Join-Path $AppDir 'pgsql\bin') $config['PG_PUERTO']
    }
    Hacer-Copia $AppDir $config $Motivo | Out-Null

    $copias = Get-ChildItem -Path (Join-Path (Get-SailDatos) 'copias') -Filter 'sail-*.dump' | Sort-Object LastWriteTime -Descending
    $viejas = $copias | Select-Object -Skip $Minimo | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$Dias) }
    foreach ($v in $viejas) {
        Remove-Item $v.FullName -Force
        Log "Copia vieja borrada: $($v.Name)"
    }
    exit 0
} catch {
    Log "ERROR en la copia de seguridad: $($_.Exception.Message)"
    exit 1
}
