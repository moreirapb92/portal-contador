#define MyAppName "Agente XML Portal do Contador"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Portal do Contador"
#define MyAppExeName "AgenteXMLPortalContador.exe"

[Setup]
AppId={{9C7C7D8A-4A55-47A9-91F8-AGENTEXMLPORTAL}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\AgenteXMLPortalContador
DefaultGroupName={#MyAppName}
OutputDir=.
OutputBaseFilename=Instalador_AgenteXMLPortalContador
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"

[Files]
Source: "dist\AgenteXMLPortalContador\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\logs"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent