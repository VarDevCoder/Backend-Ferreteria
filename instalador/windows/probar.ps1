# Prueba de punta a punta del instalador en una Windows limpia (GitHub Actions windows-latest).
#
#  1. Instalación silenciosa.
#  2. Los dos servicios corriendo y en arranque automático; acceso directo y tarea de copias.
#  3. GET / (pantallas), env.js del mismo origen, /api/v1/salud y /api/v1/configuracion-inicial.
#  4. Configuración inicial y login por la API; se carga un producto.
#  5. Copia de seguridad (la tarea programada) y restauración.
#  6. Actualización: correr el instalador de nuevo sobre la instalación existente.
#  7. Desinstalar: servicios fuera, datos conservados.
#  8. Reinstalar: mismos datos (el mismo login y el producto siguen ahí).
#
#   powershell -File instalador\windows\probar.ps1 -Instalador salida\SAIL-Instalador-1.0.0.exe
param(
    [Parameter(Mandatory = $true)][string]$Instalador,
    [string]$Logs = 'logs-prueba'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Instalador = (Resolve-Path $Instalador).Path
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$Logs = (Resolve-Path $Logs).Path

$BASE = 'http://localhost:7245'
$API = "$BASE/api/v1"
$APP = Join-Path $env:ProgramFiles 'SAIL'
$DATOS = Join-Path $env:ProgramData 'SAIL'
$ADMIN = @{ email = 'admin@ferreteria-prueba.com.py'; password = 'clave-de-prueba-123' }
$script:resultados = @()

function Paso([string]$Texto) { Write-Host ''; Write-Host "==> $Texto" }

function Chequear([string]$Nombre, [scriptblock]$Bloque) {
    try {
        $r = & $Bloque
        if ($r -eq $false) { throw 'la condición no se cumplió' }
        Write-Host "  [OK]    $Nombre"
        $script:resultados += [pscustomobject]@{ Chequeo = $Nombre; Resultado = 'OK' }
    } catch {
        Write-Host "  [FALLO] $Nombre -> $($_.Exception.Message)"
        $script:resultados += [pscustomobject]@{ Chequeo = $Nombre; Resultado = "FALLO: $($_.Exception.Message)" }
    }
}

function Esperar-Http([string]$Url, [int]$Segundos = 300) {
    $limite = (Get-Date).AddSeconds($Segundos)
    while ((Get-Date) -lt $limite) {
        try { if ((Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200) { return $true } } catch { }
        Start-Sleep -Seconds 3
    }
    throw "no respondió $Url en $Segundos s"
}

function Json([string]$Metodo, [string]$Url, $Cuerpo = $null, [string]$Token = '') {
    $h = @{}
    if ($Token) { $h['Authorization'] = "Bearer $Token" }
    $p = @{ Method = $Metodo; Uri = $Url; Headers = $h; UseBasicParsing = $true; TimeoutSec = 60 }
    if ($null -ne $Cuerpo) {
        $p['ContentType'] = 'application/json; charset=utf-8'
        $p['Body'] = [Text.Encoding]::UTF8.GetBytes(($Cuerpo | ConvertTo-Json -Depth 5))
    }
    return Invoke-RestMethod @p
}

function Instalar([string]$Etiqueta) {
    $log = Join-Path $Logs "inno-$Etiqueta.log"
    $p = Start-Process -FilePath $Instalador -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=`"$log`"" -Wait -PassThru
    return $p.ExitCode
}

function Desinstalar {
    $unins = Join-Path $APP 'unins000.exe'
    $p = Start-Process -FilePath $unins -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
    # unins000.exe se copia a %TEMP% y sigue desde ahí: esperar a que termine de verdad.
    $limite = (Get-Date).AddSeconds(180)
    while ((Get-Date) -lt $limite -and (Test-Path $unins)) { Start-Sleep -Seconds 2 }
    Start-Sleep -Seconds 3
    return $p.ExitCode
}

function Login {
    return (Json POST "$API/auth/login" $ADMIN).access_token
}

function Productos([string]$Token) {
    $r = Json GET "$API/productos" $null $Token
    if ($r.PSObject.Properties.Name -contains 'items') { $r = $r.items }   # por si se pagina
    return @($r | ForEach-Object { $_.nombre })
}

function Guardar-Logs {
    Copy-Item -Recurse -Force -Path (Join-Path $DATOS 'logs') -Destination (Join-Path $Logs 'ProgramData-SAIL-logs') -ErrorAction SilentlyContinue
}

try {
    # ------------------------------------------------------------ 1. instalación
    Paso "Instalación silenciosa de $(Split-Path $Instalador -Leaf)"
    $codigo = Instalar 'instalacion'
    Chequear 'el instalador termina sin error' { if ($codigo -ne 0) { throw "código $codigo" } }

    # ------------------------------------------------------------ 2. servicios y accesos
    Paso 'Servicios, acceso directo y tarea de copias'
    foreach ($s in @('SAIL-PostgreSQL', 'SAIL')) {
        Chequear "servicio $s corriendo y automático" {
            $svc = Get-Service -Name $s
            if ($svc.Status -ne 'Running') { throw "estado $($svc.Status)" }
            if ($svc.StartType -ne 'Automatic') { throw "inicio $($svc.StartType)" }
        }
    }
    Chequear 'servicio SAIL con cuenta NetworkService' { (Get-CimInstance Win32_Service -Filter "Name='SAIL'").StartName -like '*NetworkService*' }
    Chequear 'acceso directo SAIL en el escritorio' { Test-Path (Join-Path $env:PUBLIC 'Desktop\SAIL.lnk') }
    Chequear 'acceso directo apunta a http://localhost:7245/' { (Get-Content (Join-Path $APP 'SAIL.url') -Raw) -match 'URL=http://localhost:7245/' }
    Chequear 'tarea programada de copia diaria' { [bool](Get-ScheduledTask -TaskName 'SAIL - Copia de seguridad diaria') }
    Chequear 'configuración: IP_DESDE_X_FORWARDED_FOR=false' { (Get-Content (Join-Path $DATOS 'config\sail.env') -Raw) -match 'IP_DESDE_X_FORWARDED_FOR=false' }
    Chequear 'PostgreSQL solo escucha en la PC (127.0.0.1)' {
        $c = @(Get-NetTCPConnection -LocalPort 7246 -State Listen)
        if (-not $c.Count) { throw 'no escucha' }
        if ($c | Where-Object { @('127.0.0.1', '::1') -notcontains $_.LocalAddress }) { throw ($c.LocalAddress -join ',') }
    }

    # ------------------------------------------------------------ 3. servidor único
    Paso 'Servidor único: pantallas y API en http://localhost:7245'
    Esperar-Http "$API/salud" | Out-Null
    Chequear 'GET / devuelve las pantallas (HTML)' {
        $r = Invoke-WebRequest -Uri "$BASE/" -UseBasicParsing
        ($r.StatusCode -eq 200) -and ($r.Headers['Content-Type'] -like 'text/html*') -and ($r.Content -match 'SAIL')
    }
    Chequear 'los .js salen como text/javascript' { (Invoke-WebRequest -Uri "$BASE/assets/js/config.js" -UseBasicParsing).Headers['Content-Type'] -like 'text/javascript*' }
    Chequear 'env.js apunta la API al mismo origen' { (Invoke-WebRequest -Uri "$BASE/assets/js/env.js" -UseBasicParsing).Content -match 'window.location.origin' }
    Chequear 'GET /api/v1/salud' { (Json GET "$API/salud").status -eq 'ok' }
    Chequear 'GET /api/v1/configuracion-inicial pide configurar' { (Json GET "$API/configuracion-inicial").requiere_configuracion -eq $true }

    # ------------------------------------------------------------ 4. configuración inicial y login
    Paso 'Configuración inicial y login por la API'
    Chequear 'POST /configuracion-inicial crea empresa y admin' {
        $r = Json POST "$API/configuracion-inicial" @{
            empresa = @{ nombre_comercial = 'Ferretería de Prueba Windows'; ruc = '80012345-6'; moneda_codigo = 'PYG'; moneda_simbolo = 'Gs.'; locale = 'es-PY' }
            admin = @{ name = 'Administrador'; email = $ADMIN.email; password = $ADMIN.password }
        }
        [bool]$r.access_token
    }
    $token = $null
    Chequear 'login del administrador' { $script:token = Login; [bool]$script:token }
    $token = $script:token
    Chequear 'GET /auth/me con el token' { (Json GET "$API/auth/me" $null $token).email -eq $ADMIN.email }
    Chequear 'cargar un producto' { [bool](Json POST "$API/productos" @{ nombre = 'Martillo de prueba'; precio_compra = 30000; precio_venta = 45000 } $token).id }
    Chequear 'la configuración inicial queda cerrada' { (Json GET "$API/configuracion-inicial").requiere_configuracion -eq $false }

    # ------------------------------------------------------------ 5. copias de seguridad
    Paso 'Copia de seguridad (tarea programada) y restauración'
    $copias = Join-Path $DATOS 'copias'
    $antes = @(Get-ChildItem $copias -Filter '*.dump' -ErrorAction SilentlyContinue).Count
    Start-ScheduledTask -TaskName 'SAIL - Copia de seguridad diaria'
    $limite = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $limite -and @(Get-ChildItem $copias -Filter '*.dump' -ErrorAction SilentlyContinue).Count -le $antes) { Start-Sleep -Seconds 3 }
    Start-Sleep -Seconds 5
    $copia = Get-ChildItem $copias -Filter '*.dump' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    Chequear 'la tarea programada dejó una copia .dump' { $copia -and $copia.Length -gt 0 }

    Chequear 'restaurar la copia deja los datos de ese momento' {
        Json POST "$API/productos" @{ nombre = 'Producto posterior a la copia'; precio_compra = 1000; precio_venta = 1500 } $token | Out-Null
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $APP 'scripts\restaurar_copia.ps1') -Archivo $copia.FullName -SinConfirmar
        if ($LASTEXITCODE -ne 0) { throw "restaurar_copia.ps1 terminó con $LASTEXITCODE" }
        $nombres = Productos (Login)
        if ($nombres -notcontains 'Martillo de prueba') { throw 'falta el producto de la copia' }
        if ($nombres -contains 'Producto posterior a la copia') { throw 'quedó el producto posterior a la copia' }
    }

    # ------------------------------------------------------------ 6. actualización
    Paso 'Actualización: correr el instalador sobre la instalación existente'
    $codigo = Instalar 'actualizacion'
    Chequear 'la actualización termina sin error' { if ($codigo -ne 0) { throw "código $codigo" } }
    Chequear 'antes de arrancar la versión nueva hizo una copia' { [bool](Get-ChildItem $copias -Filter '*antes-de-instalar*.dump') }
    Esperar-Http "$API/salud" | Out-Null
    Chequear 'después de actualizar: mismo login y mismos datos' { (Productos (Login)) -contains 'Martillo de prueba' }

    # ------------------------------------------------------------ 7. desinstalar
    Paso 'Desinstalar (los datos tienen que quedar)'
    $codigo = Desinstalar
    Chequear 'el desinstalador termina sin error' { if ($codigo -ne 0) { throw "código $codigo" } }
    Chequear 'los servicios ya no existen' { -not (Get-Service -Name 'SAIL', 'SAIL-PostgreSQL' -ErrorAction SilentlyContinue) }
    Chequear 'la tarea programada ya no existe' { -not (Get-ScheduledTask -TaskName 'SAIL - Copia de seguridad diaria' -ErrorAction SilentlyContinue) }
    Chequear 'el programa se borró' { -not (Test-Path (Join-Path $APP 'backend')) }
    Chequear 'los datos siguen en C:\ProgramData\SAIL' {
        (Test-Path (Join-Path $DATOS 'base-de-datos\PG_VERSION')) -and (Test-Path (Join-Path $DATOS 'config\sail.env')) -and
        @(Get-ChildItem (Join-Path $DATOS 'copias') -Filter '*.dump').Count -gt 0
    }
    Chequear 'SAIL ya no responde' { try { Invoke-WebRequest -Uri "$API/salud" -UseBasicParsing -TimeoutSec 5 | Out-Null; $false } catch { $true } }

    # ------------------------------------------------------------ 8. reinstalar
    Paso 'Reinstalar: tiene que encontrar los datos'
    $codigo = Instalar 'reinstalacion'
    Chequear 'la reinstalación termina sin error' { if ($codigo -ne 0) { throw "código $codigo" } }
    Esperar-Http "$API/salud" | Out-Null
    Chequear 'después de reinstalar: no pide configuración inicial' { (Json GET "$API/configuracion-inicial").requiere_configuracion -eq $false }
    Chequear 'después de reinstalar: mismo login y mismos datos' { (Productos (Login)) -contains 'Martillo de prueba' }
} catch {
    Write-Host "ERROR inesperado en la prueba: $($_.Exception.Message)"
    $script:resultados += [pscustomobject]@{ Chequeo = 'prueba completa'; Resultado = "FALLO: $($_.Exception.Message)" }
} finally {
    Guardar-Logs
}

Paso 'Resumen'
$script:resultados | Format-Table -AutoSize | Out-String -Width 200 | Write-Host
$fallos = @($script:resultados | Where-Object { $_.Resultado -ne 'OK' }).Count
$script:resultados | ConvertTo-Json | Set-Content -Path (Join-Path $Logs 'resultados.json') -Encoding UTF8
if ($env:GITHUB_STEP_SUMMARY) {
    $md = @('## Prueba del instalador en Windows', '', '| Chequeo | Resultado |', '|---|---|')
    foreach ($r in $script:resultados) { $md += "| $($r.Chequeo) | $($r.Resultado) |" }
    Add-Content -Path $env:GITHUB_STEP_SUMMARY -Value $md -Encoding UTF8
}
if ($fallos) { Write-Host "$fallos chequeo(s) fallaron"; exit 1 }
Write-Host "Todos los chequeos pasaron ($($script:resultados.Count))."
exit 0
