#define MyAppName "MouthClick"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "FundaciÃ³n TeletÃ³n"
#define MyAppExeName "MouthClick.exe"

[Setup]
AppId={{5EAF982C-50B1-46DF-96D5-BF87557D31B4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={localappdata}\Programs\MouthClick
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest

OutputDir=installer
OutputBaseFilename=MouthClick_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked
Name: "startup"; Description: "Iniciar MouthClick al iniciar sesiÃ³n en Windows"; GroupDescription: "Inicio automÃ¡tico:"; Flags: unchecked

[Files]
Source: "dist\MouthClick\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MouthClick"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\MouthClick"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\MouthClick"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "Abrir MouthClick"; Flags: nowait postinstall skipifsilent
