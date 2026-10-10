; Instalador de SAIL para Windows (Inno Setup 6).
;
; En simple: instala SAIL completo en la PC de la ferretería (Python, backend,
; pantallas y PostgreSQL), deja dos servicios que arrancan con la PC, un acceso
; directo "SAIL" y una copia de seguridad diaria. Correr un instalador más nuevo
; actualiza conservando los datos. Desinstalar NO borra los datos.
;
; Se compila con construir.ps1 (GitHub Actions, windows-latest):
;   ISCC.exe /DVersion=1.0.0 /DStaging=<carpeta preparada> /O<salida> sail.iss
; Instalación silenciosa: SAIL-Instalador-1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

#ifndef Version
  #define Version "0.0.0"
#endif
#ifndef Staging
  #define Staging "staging"
#endif
#define Puerto "7245"
#define PuertoPg "7246"

[Setup]
; AppId fijo: es lo que hace que un instalador más nuevo actualice en vez de instalar otra copia.
AppId={{267EEDE2-B63F-4714-827F-E28B27003767}
AppName=SAIL
AppVersion={#Version}
AppVerName=SAIL {#Version}
AppPublisher=SAIL
AppComments=Sistema de gestión para ferreterías
VersionInfoVersion={#Version}
DefaultDirName={autopf}\SAIL
DefaultGroupName=SAIL
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes
OutputBaseFilename=SAIL-Instalador-{#Version}
SetupIconFile=sail.ico
UninstallDisplayIcon={app}\sail.ico
UninstallDisplayName=SAIL
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=admin
WizardStyle=modern
; Los servicios los frena PrepareToInstall; no hace falta el Restart Manager.
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo ""SAIL"" en el escritorio"
Name: "red"; Description: "Permitir que otras PCs de la red local usen SAIL (http://<esta PC>:{#Puerto})"; Flags: unchecked

[InstallDelete]
; Reemplazo limpio del programa al actualizar (los datos están en {commonappdata}\SAIL y no se tocan).
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\backend"
Type: filesandordirs; Name: "{app}\frontend"
Type: filesandordirs; Name: "{app}\pgsql"
Type: filesandordirs; Name: "{app}\scripts"

[Files]
Source: "{#Staging}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[INI]
Filename: "{app}\SAIL.url"; Section: "InternetShortcut"; Key: "URL"; String: "http://localhost:{#Puerto}/"
Filename: "{app}\SAIL.url"; Section: "InternetShortcut"; Key: "IconFile"; String: "{app}\sail.ico"
Filename: "{app}\SAIL.url"; Section: "InternetShortcut"; Key: "IconIndex"; String: "0"

[Icons]
Name: "{group}\SAIL"; Filename: "{app}\SAIL.url"; IconFilename: "{app}\sail.ico"; Comment: "Abrir SAIL en el navegador"
Name: "{commondesktop}\SAIL"; Filename: "{app}\SAIL.url"; IconFilename: "{app}\sail.ico"; Comment: "Abrir SAIL en el navegador"; Tasks: escritorio
Name: "{group}\Copias de seguridad de SAIL"; Filename: "{commonappdata}\SAIL\copias"
Name: "{group}\Desinstalar SAIL"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\SAIL.url"; Description: "Abrir SAIL ahora"; Flags: postinstall shellexec nowait skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\desinstalar.ps1"" -AppDir ""{app}"""; Flags: runhidden waituntilterminated; RunOnceId: "QuitarServiciosSAIL"

[UninstallDelete]
Type: files; Name: "{app}\SAIL.url"
Type: files; Name: "{app}\servicio\sail-servidor.xml"
Type: files; Name: "{app}\servicio\*.log"
Type: dirifempty; Name: "{app}\servicio"
Type: dirifempty; Name: "{app}"

[Code]
var
  ErrorConfiguracion: Integer;

function Powershell(const Argumentos: String): Integer;
var
  Codigo: Integer;
begin
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
              '-NoProfile -ExecutionPolicy Bypass ' + Argumentos, '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
    Codigo := -1;
  Result := Codigo;
end;

{ Antes de copiar archivos: frenar los servicios de una versión anterior
  para que Windows suelte los ejecutables. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  Powershell('-Command "Stop-Service -Name SAIL,SAIL-PostgreSQL -Force -ErrorAction SilentlyContinue"');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Parametros: String;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Configurando la base de datos y los servicios de SAIL (puede tardar un par de minutos)...';
    Parametros := '-File "' + ExpandConstant('{app}\scripts\instalar.ps1') + '" -AppDir "' + ExpandConstant('{app}') +
                  '" -Version "{#Version}" -Puerto {#Puerto} -PuertoPg {#PuertoPg}';
    if WizardIsTaskSelected('red') then
      Parametros := Parametros + ' -AccesoRed';
    ErrorConfiguracion := Powershell(Parametros);
    if ErrorConfiguracion <> 0 then
    begin
      Log('instalar.ps1 terminó con error ' + IntToStr(ErrorConfiguracion));
      SuppressibleMsgBox('No se pudo terminar de configurar SAIL.' + #13#10#13#10 +
        'Los archivos quedaron instalados y los datos que hubiera no se tocaron. ' +
        'Detalle para soporte: ' + ExpandConstant('{commonappdata}\SAIL\logs\instalacion.log'),
        mbError, MB_OK, IDOK);
    end;
  end;
end;

{ Instalación silenciosa: si la configuración falló, el instalador devuelve un
  código de salida distinto de cero (100 + el error), así lo detecta quien lo corre. }
function GetCustomSetupExitCode: Integer;
begin
  if ErrorConfiguracion <> 0 then
    Result := 100 + (ErrorConfiguracion mod 100)
  else
    Result := 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    SuppressibleMsgBox('SAIL se desinstaló.' + #13#10#13#10 +
      'Tus datos (base de datos, copias de seguridad y configuración) quedaron guardados en ' +
      ExpandConstant('{commonappdata}\SAIL') + '. Si volvés a instalar SAIL, sigue todo como estaba.',
      mbInformation, MB_OK, IDOK);
end;
