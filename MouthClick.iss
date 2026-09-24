#define MyAppName "MouthClick"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "Fundación Teletón"
#define MyAppExeName "MouthClick.exe"
#ifndef AppSource
  #define AppSource "dist\MouthClick"
#endif

[Setup]
AppId={{5EAF982C-50B1-46DF-96D5-BF87557D31B4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={localappdata}\Programs\MouthClick
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
MinVersion=10.0

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
Name: "startup"; Description: "Iniciar MouthClick al iniciar sesión en Windows"; GroupDescription: "Inicio automático:"; Flags: unchecked

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Excludes: "profiles.json"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#AppSource}\profiles.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\MouthClick"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Configurar MouthClick"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--config"; WorkingDir: "{app}"
Name: "{autodesktop}\MouthClick"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\MouthClick"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "Abrir MouthClick"; Flags: nowait postinstall skipifsilent
