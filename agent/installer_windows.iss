; Form Discoverer Agent - Windows Installer Script
; Inno Setup Configuration

[Setup]
AppName=Form Discoverer Agent
AppVersion=2.0.0
AppPublisher=Form Discoverer
AppPublisherURL=https://formdiscoverer.com
DefaultDirName={autopf}\FormDiscovererAgent
DefaultGroupName=Form Discoverer
OutputDir=dist\installers
OutputBaseFilename=FormDiscovererAgent-Setup-Windows
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\FormDiscovererAgent.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\FormDiscovererAgent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Form Discoverer Agent"; Filename: "{app}\FormDiscovererAgent.exe"
Name: "{group}\Uninstall Form Discoverer Agent"; Filename: "{uninstallexe}"
Name: "{commonstartup}\Form Discoverer Agent"; Filename: "{app}\FormDiscovererAgent.exe"; Tasks: autostartup

[Tasks]
Name: "autostartup"; Description: "Start agent automatically on system startup"; GroupDescription: "Additional options:"; Flags: unchecked
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\FormDiscovererAgent.exe"; Description: "Launch Form Discoverer Agent"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
