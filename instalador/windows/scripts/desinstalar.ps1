# Quita los servicios y la tarea de SAIL (lo llama el desinstalador, antes de borrar los archivos).
#
# En simple: deja de correr SAIL en esta PC pero NO borra los datos: la base de
# datos, las copias y la configuración quedan en C:\ProgramData\SAIL para una
# reinstalación (correr de nuevo el instalador las encuentra y sigue igual).
param([Parameter(Mandatory = $true)][string]$AppDir)

. (Join-Path $PSScriptRoot 'comun.ps1')

try {
    Iniciar-Log 'instalacion.log'
    Log "=== Desinstalando SAIL de $AppDir (los datos quedan en $(Get-SailDatos)) ==="

    if (Existe-Servicio $SAIL_SERVICIO) {
        Stop-Service -Name $SAIL_SERVICIO -Force -ErrorAction SilentlyContinue
        $exe = Join-Path $AppDir 'servicio\sail-servidor.exe'
        if (Test-Path $exe) {
            Ejecutar $exe @('uninstall') -PermitirError | Out-Null
        }
        if (Existe-Servicio $SAIL_SERVICIO) { Ejecutar sc.exe @('delete', $SAIL_SERVICIO) -PermitirError | Out-Null }
        Log 'Servicio SAIL quitado.'
    }

    if (Existe-Servicio $SAIL_SERVICIO_PG) {
        Stop-Service -Name $SAIL_SERVICIO_PG -Force -ErrorAction SilentlyContinue
        $pgctl = Join-Path $AppDir 'pgsql\bin\pg_ctl.exe'
        if (Test-Path $pgctl) {
            Ejecutar $pgctl @('unregister', '-N', $SAIL_SERVICIO_PG) -PermitirError | Out-Null
        }
        if (Existe-Servicio $SAIL_SERVICIO_PG) { Ejecutar sc.exe @('delete', $SAIL_SERVICIO_PG) -PermitirError | Out-Null }
        Log 'Servicio SAIL-PostgreSQL quitado (la base de datos queda guardada).'
    }

    Unregister-ScheduledTask -TaskName $SAIL_TAREA_COPIA -Confirm:$false -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName $SAIL_REGLA_FIREWALL -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    # Esperar a que Windows suelte los ejecutables para que se puedan borrar.
    $limite = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $limite -and ((Get-Process -Name postgres, python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$AppDir*" }))) {
        Start-Sleep -Seconds 1
    }
    Log '=== SAIL desinstalado. Datos conservados. ==='
    exit 0
} catch {
    Log "ERROR: $($_.Exception.Message)"
    exit 1
}
