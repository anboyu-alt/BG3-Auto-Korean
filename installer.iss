; installer.iss — BG3 Mod Translator 설치 마법사 (Inno Setup)
;
; Nuitka standalone 폴더(0/71, build_all.ps1이 nuitka_build\BG3_ModTranslator로 스테이징)를
; 단일 setup.exe로 감싼다. Electron 앱(Icosa)이 NSIS 인스톨러로 미탐지를 얻는 것과 같은 원리:
; "신뢰 런타임 폴더 + 표준 인스톨러 포맷". 코드 서명 없이도 onefile 패커보다 오탐이 훨씬 적다.
;
; 컴파일(빌드 스크립트가 자동 호출):
;   ISCC.exe /DMyAppVersion=7.0 installer.iss
;
; PrivilegesRequired=lowest → 관리자 권한 없이 사용자 폴더에 설치(엘리베이션 없음 = AV 마찰↓).

#ifndef MyAppVersion
  #define MyAppVersion "0.0"
#endif
#ifndef SourceDir
  #define SourceDir "nuitka_build\BG3_ModTranslator"
#endif

#define MyAppName "BG3 Mod Translator"
#define MyAppPublisher "anboyu"
#define MyAppURL "https://github.com/anboyu/BG3-Auto-Korean"
#define MyAppExeName "BG3_ModTranslator.exe"

[Setup]
; AppId는 버전이 바뀌어도 고정해야 업그레이드 설치로 인식된다.
AppId={{B7E1C9A4-2F38-4D6E-9C5A-1E0F7A2B3C4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\BG3 Mod Translator
DefaultGroupName=BG3 Mod Translator
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename=BG3_ModTranslator_v{#MyAppVersion}_setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
