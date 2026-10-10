# Construye SAIL-Instalador-x.y.z.exe (corre en Windows: GitHub Actions windows-latest).
#
# En simple: junta todo lo que necesita una PC para correr SAIL sin instalar nada más
# (Python embebido con las dependencias, el backend, las pantallas, PostgreSQL portátil,
# WinSW para el servicio y el runtime de Visual C++) y lo empaqueta con Inno Setup.
#
#   powershell -File instalador\windows\construir.ps1 -Backend . -Frontend ..\Frontend-Ferreteria -Salida salida
#
# Requisitos de la máquina que construye: Windows x64, Python 3.12 en el PATH (para
# instalar las dependencias con pip) e internet. Inno Setup se instala solo si falta.
param(
    [Parameter(Mandatory = $true)][string]$Backend,
    [Parameter(Mandatory = $true)][string]$Frontend,
    [string]$Salida = 'salida',
    [string]$Version = ''
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Versiones de lo que se incluye. PostgreSQL: SIEMPRE la misma versión mayor (17), porque
# los datos de una versión mayor no los abre otra (ver $SAIL_PG_MAYOR en scripts\comun.ps1).
# Se prueba de la más nueva a la más vieja y se usa la primera que exista en EnterpriseDB.
$PYTHON_VERSION = '3.12.10'
$PG_VERSIONES = @('17.10-1', '17.9-1', '17.8-1', '17.7-1', '17.6-1', '17.5-1', '17.4-1')
$WINSW_URL = 'https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe'
$VCREDIST_URL = 'https://aka.ms/vs/17/release/vc_redist.x64.exe'

$aqui = $PSScriptRoot
if (-not $Version) { $Version = (Get-Content (Join-Path $aqui 'VERSION') -TotalCount 1).Trim() }
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Versión inválida: '$Version' (tiene que ser x.y.z)" }
$Backend = (Resolve-Path $Backend).Path
$Frontend = (Resolve-Path $Frontend).Path
New-Item -ItemType Directory -Force -Path $Salida | Out-Null
$Salida = (Resolve-Path $Salida).Path
$staging = Join-Path $Salida 'staging'
$descargas = Join-Path $Salida 'descargas'
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Force -Path $staging, $descargas | Out-Null

function Paso([string]$Texto) { Write-Host ''; Write-Host "==> $Texto" }

function Bajar([string]$Url, [string]$Destino) {
    if (Test-Path $Destino) { return }
    Write-Host "    bajando $Url"
    Invoke-WebRequest -Uri $Url -OutFile "$Destino.parcial" -UseBasicParsing
    Move-Item "$Destino.parcial" $Destino
}

function Correr([string]$Programa, [string[]]$Argumentos) {
    & $Programa @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "$Programa terminó con error $LASTEXITCODE" }
}

# ---------------------------------------------------------------- Python embebido
Paso "Python $PYTHON_VERSION embebido"
$zipPython = Join-Path $descargas "python-$PYTHON_VERSION-embed-amd64.zip"
Bajar "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-embed-amd64.zip" $zipPython
$dirPython = Join-Path $staging 'python'
Expand-Archive -Path $zipPython -DestinationPath $dirPython
$pth = Get-ChildItem -Path $dirPython -Filter 'python3*._pth' | Select-Object -First 1
$zipStdlib = (Get-ChildItem -Path $dirPython -Filter 'python3*.zip' | Select-Object -First 1).Name
# sys.path fijo: la biblioteca estándar, las dependencias y el backend.
Set-Content -Path $pth.FullName -Encoding ASCII -Value @($zipStdlib, '.', 'Lib\site-packages', '..\backend', 'import site')

Paso 'Dependencias (pip, solo ruedas binarias para Windows)'
$pyHost = (& python -c "import sys; print('%d.%d' % sys.version_info[:2])")
if ($pyHost -ne ($PYTHON_VERSION -replace '^(\d+\.\d+).*', '$1')) { throw "Hace falta Python $PYTHON_VERSION en el PATH para pip (hay $pyHost)" }
$sitePackages = Join-Path $dirPython 'Lib\site-packages'
Correr python @('-m', 'pip', 'install', '--disable-pip-version-check', '--no-cache-dir', '--only-binary=:all:',
    '--target', $sitePackages, '-r', (Join-Path $Backend 'requirements.txt'))
Remove-Item -Recurse -Force (Join-Path $sitePackages 'bin') -ErrorAction SilentlyContinue

# ---------------------------------------------------------------- backend y frontend
Paso 'Backend'
$dirBackend = Join-Path $staging 'backend'
New-Item -ItemType Directory -Force -Path $dirBackend | Out-Null
foreach ($item in @('app', 'alembic', 'alembic.ini', 'servir.py', 'requirements.txt')) {
    Copy-Item -Recurse -Path (Join-Path $Backend $item) -Destination $dirBackend
}
Get-ChildItem -Path $dirBackend -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force

Paso 'Frontend (servidor único)'
$dirFrontend = Join-Path $staging 'frontend'
Copy-Item -Recurse -Path $Frontend -Destination $dirFrontend
foreach ($item in @('.git', '.github', 'herramientas', 'netlify.toml', '.gitattributes', '.gitignore')) {
    Remove-Item -Recurse -Force (Join-Path $dirFrontend $item) -ErrorAction SilentlyContinue
}
if (-not (Test-Path (Join-Path $dirFrontend 'index.html'))) { throw 'El frontend no tiene index.html' }

# ---------------------------------------------------------------- PostgreSQL portátil
Paso 'PostgreSQL (binarios zip oficiales de EnterpriseDB)'
$pgVersion = $null
foreach ($v in $PG_VERSIONES) {
    $zipPg = Join-Path $descargas "postgresql-$v-windows-x64-binaries.zip"
    try {
        Bajar "https://get.enterprisedb.com/postgresql/postgresql-$v-windows-x64-binaries.zip" $zipPg
        $pgVersion = $v
        break
    } catch {
        Write-Host "    $v no está disponible ($($_.Exception.Message))"
        Remove-Item "$zipPg.parcial" -ErrorAction SilentlyContinue
    }
}
if (-not $pgVersion) { throw 'No se pudo bajar PostgreSQL de EnterpriseDB' }
$tmpPg = Join-Path $descargas 'pg'
if (Test-Path $tmpPg) { Remove-Item -Recurse -Force $tmpPg }
New-Item -ItemType Directory -Force -Path $tmpPg | Out-Null
# tar de Windows (bsdtar) descomprime zip mucho más rápido que Expand-Archive.
Correr (Join-Path $env:SystemRoot 'System32\tar.exe') @('-xf', $zipPg, '-C', $tmpPg)
$dirPg = Join-Path $staging 'pgsql'
New-Item -ItemType Directory -Force -Path $dirPg | Out-Null
foreach ($item in @('bin', 'lib', 'share')) {
    Copy-Item -Recurse -Path (Join-Path $tmpPg "pgsql\$item") -Destination $dirPg
}
# Lo que no hace falta para correr el servidor (pgAdmin, StackBuilder, documentación y
# archivos de compilación ya quedaron afuera).
Get-ChildItem -Path $dirPg -Recurse -Include '*.lib', '*.pdb' | Remove-Item -Force
Correr (Join-Path $dirPg 'bin\postgres.exe') @('--version')

# ---------------------------------------------------------------- servicio y runtime
Paso 'WinSW (servicio de Windows para SAIL) y runtime de Visual C++'
New-Item -ItemType Directory -Force -Path (Join-Path $staging 'servicio'), (Join-Path $staging 'redist') | Out-Null
Bajar $WINSW_URL (Join-Path $descargas 'WinSW-x64.exe')
Copy-Item (Join-Path $descargas 'WinSW-x64.exe') (Join-Path $staging 'servicio\sail-servidor.exe')
Bajar $VCREDIST_URL (Join-Path $descargas 'vc_redist.x64.exe')
Copy-Item (Join-Path $descargas 'vc_redist.x64.exe') (Join-Path $staging 'redist\vc_redist.x64.exe')

Paso 'Scripts, ícono y datos de la versión'
Copy-Item -Recurse -Path (Join-Path $aqui 'scripts') -Destination $staging
Copy-Item -Path (Join-Path $aqui 'sail.ico') -Destination $staging
$commitBackend = ''; $commitFrontend = ''
try { $commitBackend = (git -C $Backend rev-parse --short HEAD); $commitFrontend = (git -C $Frontend rev-parse --short HEAD) } catch { }
Set-Content -Path (Join-Path $staging 'VERSION.txt') -Encoding ASCII -Value @(
    "SAIL $Version",
    "backend $commitBackend",
    "frontend $commitFrontend",
    "python $PYTHON_VERSION",
    "postgresql $pgVersion",
    "construido $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
)

# ---------------------------------------------------------------- compilar y probar el Python embebido
Paso 'Precompilar Python y probar que importa todo'
$py = Join-Path $dirPython 'python.exe'
Correr $py @('-m', 'compileall', '-q', '--invalidation-mode', 'unchecked-hash', $dirBackend, $sitePackages)
$env:FRONTEND_DIR = $dirFrontend
$env:DATABASE_URL = 'postgresql+pg8000://sail:x@127.0.0.1:7246/sail'
Correr $py @('-c', 'import app.main, servir, uvicorn, alembic, pg8000, httptools; print(''importa todo OK'')')
Remove-Item Env:\FRONTEND_DIR, Env:\DATABASE_URL

# ---------------------------------------------------------------- Inno Setup
Paso 'Inno Setup'
$iscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (-not (Test-Path $iscc)) {
    Write-Host '    Inno Setup no está: se instala con Chocolatey'
    Correr choco @('install', 'innosetup', '-y', '--no-progress')
}
if (-not (Test-Path $iscc)) { throw "No se encontró ISCC.exe en $iscc" }
Correr $iscc @("/DVersion=$Version", "/DStaging=$staging", "/O$Salida", (Join-Path $aqui 'sail.iss'))

$exe = Join-Path $Salida "SAIL-Instalador-$Version.exe"
$hash = (Get-FileHash -Algorithm SHA256 $exe).Hash.ToLower()
Set-Content -Path (Join-Path $Salida "SAIL-Instalador-$Version.sha256.txt") -Encoding ASCII -Value "$hash  SAIL-Instalador-$Version.exe"
Paso ("Listo: {0} ({1:N1} MB) sha256 {2}" -f $exe, ((Get-Item $exe).Length / 1MB), $hash)
if ($env:GITHUB_OUTPUT) {
    Add-Content -Path $env:GITHUB_OUTPUT -Value "version=$Version" -Encoding ASCII
    Add-Content -Path $env:GITHUB_OUTPUT -Value "postgresql=$pgVersion" -Encoding ASCII
}
