#define MyAppName "Extractor OCR"
; Mantener alineado con releases de GitHub (tag / versión del producto).
#define MyAppVersion "2.1.0"
#define MyAppPublisher "FGC"
#define MyAppExeName "ExtractorOCR.exe"

[Setup]
AppId={{BB2C202A-F14F-46CC-ADDA-5B77F2691967}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\ExtractorOCR
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\installer_output
OutputBaseFilename=Instalador_ExtractorOCR_{#MyAppVersion}
SetupIconFile=..\extractor_ocr.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ChangesEnvironment=yes
; Cierra ExtractorOCR si sigue abierto para poder reemplazar archivos en {app}.
CloseApplications=force
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked
Name: "launchapp"; Description: "Abrir {#MyAppName} al terminar"; GroupDescription: "Opciones adicionales:"; Flags: unchecked

[Files]
Source: "..\dist\ExtractorOCR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "API_BASE_URL"; ValueData: "https://tools.feuh.com.mx"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "LOGIN_ENDPOINT"; ValueData: "/auth/login"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "REGISTROS_ENDPOINT"; ValueData: "/registros/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "COVERTURAS_ENDPOINT"; ValueData: "/coverages/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "ENVIOS_PX_ENDPOINT"; ValueData: "/shipments-px/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "RECEIVERS_ENDPOINT"; ValueData: "/receivers/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "ADDRESSES_ENDPOINT"; ValueData: "/addresses/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "CONTACTS_ENDPOINT"; ValueData: "/contacts/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "TITLES_ENDPOINT"; ValueData: "/titles/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "JOB_ROLES_ENDPOINT"; ValueData: "/job-roles/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "ORGANIZATIONS_ENDPOINT"; ValueData: "/organizations/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "VOLANTES_ENDPOINT"; ValueData: "/volante/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "SEPOMEX_ENDPOINT"; ValueData: "/sepomex/"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "API_TIMEOUT_SECONDS"; ValueData: "60"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "OPENAI_MODEL"; ValueData: "gpt-6-luna"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "TIMEOUT_SECONDS"; ValueData: "60"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "EXPORT_DIR"; ValueData: "downloads"; Flags: uninsdeletevalue

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent; Tasks: launchapp
