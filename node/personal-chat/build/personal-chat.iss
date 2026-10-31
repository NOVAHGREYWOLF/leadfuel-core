; Personal Chat - Windows installer (Inno Setup 6). Built by build-windows.ps1, which passes
; /DStage=<folder> and /DAppVersion=<x.y.z>. Per-user install, no administrator rights, the
; same shape as the home-node installer (home-node/build/node.iss) and as Ollama itself.
;
; UNSIGNED. A code-signing certificate is an owner spend (card V7). Until it is bought, Windows
; SmartScreen will warn on this file and it must not be distributed.

#ifndef Stage
  #error Pass /DStage=<staging folder> (build-windows.ps1 does this)
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef OutDir
  #define OutDir Stage + "\..\out"
#endif
#define AppName "Personal Chat"

[Setup]
AppId={{179F7155-7232-4A8F-9822-2C8DD9C8A041}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=ETG AI
DefaultDirName={localappdata}\Programs\PersonalChat
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#OutDir}
OutputBaseFilename=PersonalChat-Setup-{#AppVersion}-UNSIGNED
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#Stage}\PersonalChat\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "{#Stage}\NodeSpec.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Stage}\setup-windows.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\PersonalChat.exe"
Name: "{group}\{#AppName} setup (check this computer)"; Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\setup-windows.ps1"" -AppDir ""{app}"""
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\PersonalChat.exe"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\setup-windows.ps1"" -AppDir ""{app}"""; \
  Description: "Check this computer and get the right model (asks before any download)"; \
  Flags: postinstall
Filename: "{app}\PersonalChat.exe"; Description: "Open {#AppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; The app's own files only. The person's config, seat record and Ollama models are left alone:
; uninstalling a chat window must not delete gigabytes of models other apps may use.
Type: filesandordirs; Name: "{app}"
