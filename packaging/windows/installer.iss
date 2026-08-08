; Inno Setup script for Order Book Simulator.
; 1. Install Inno Setup: https://jrsoftware.org/isinfo.php
; 2. First run build_windows.bat from the project root (produces dist\OrderBookSimulator\)
; 3. Compile this script (right-click -> Compile, or run from the Inno Setup CLI: iscc installer.iss)
; Output: packaging\windows\Output\OrderBookSimulator-Setup.exe

#define MyAppName "Order Book Simulator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OrderBookSim"
#define MyAppExeName "OrderBookSimulator.exe"

[Setup]
AppId={{C4C9F7B0-9C7B-4A3E-8B7A-ORDERBOOKSIM1}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=Output
OutputBaseFilename=OrderBookSimulator-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\icon.ico
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Pull in the entire onedir build produced by PyInstaller
Source: "..\..\dist\OrderBookSimulator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
