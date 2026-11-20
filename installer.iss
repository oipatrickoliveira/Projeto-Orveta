#define AppName "Orveta"
#define VersionFile FileOpen("version.txt")
#define AppVersion Trim(FileRead(VersionFile))
#expr FileClose(VersionFile)
[Setup]
AppId={{7A3CFE70-BD45-47CF-8182-4D784F985C1E}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Orveta
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
VersionInfoCopyright=Copyright (C) Orveta
VersionInfoOriginalFileName=Orveta-Instalador-{#AppVersion}.exe
DefaultDirName={localappdata}\Programs\Orveta
DefaultGroupName=Orveta
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousTasks=yes
CloseApplications=yes
RestartApplications=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=release
OutputBaseFilename=Orveta-Instalador-{#AppVersion}
SetupIconFile=orveta.ico
UninstallDisplayIcon={app}\Orveta.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
#ifdef SignedBuild
SignTool=Orveta
SignedUninstaller=yes
#endif
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; GroupDescription: "Atalhos:"
[Files]
Source: "dist\release-build\Orveta\Orveta.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\release-build\Orveta\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "vendor\yt-dlp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\ffmpeg-shared-8.1\ffmpeg.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion
Source: "vendor\ffmpeg-shared-8.1\ffprobe.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion
Source: "vendor\ffmpeg-shared-8.1\*.dll"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion
Source: "vendor\ffmpeg-shared-8.1\LICENSE.txt"; DestDir: "{app}\licenses"; DestName: "FFmpeg-LICENSE.txt"; Flags: ignoreversion
Source: "vendor\qjs-0.18.0.exe"; DestDir: "{app}\runtime"; DestName: "qjs.exe"; Flags: ignoreversion
Source: "vendor\quickjs-LICENSE.txt"; DestDir: "{app}\licenses"; DestName: "QuickJS-NG-LICENSE.txt"; Flags: ignoreversion
Source: "vendor\yt-dlp-THIRD_PARTY_LICENSES.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.md"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "build\release-build\licenses\Python-LICENSE.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "build\release-build\licenses\Tcl-Tk-LICENSE.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
[Icons]
Name: "{group}\Orveta"; Filename: "{app}\Orveta.exe"
Name: "{autodesktop}\Orveta"; Filename: "{app}\Orveta.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\Orveta.exe"; Description: "Abrir Orveta"; Flags: nowait postinstall skipifsilent
