; Inno Setup 설치 프로그램 스크립트
; 빌드: ISCC.exe /DAppVersion=2.1.0 installer\TherapyChart.iss
;   (dist\TherapyChart.exe 빌드 후 실행. CI는 constants.APP_VERSION을 읽어 주입)
; 결과: installer\Output\TherapyChartSetup.exe

; 버전은 빌드 시 /DAppVersion=... 으로 주입한다. 미지정 시 아래 기본값 사용.
#ifndef AppVersion
  #define AppVersion "2.1.0"
#endif

[Setup]
AppId={{7E1A9C42-6B7F-4A5D-9C3E-1A2B3C4D5E6F}
AppName=도수치료 진료 기록지 입력 도우미
AppVersion={#AppVersion}
AppPublisher=Charting
DefaultDirName={autopf}\TherapyChart
DefaultGroupName=TherapyChart
UninstallDisplayName=도수치료 진료 기록지 입력 도우미
SetupIconFile=..\assets\icon.ico
OutputDir=Output
OutputBaseFilename=TherapyChartSetup
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog

[Tasks]
Name: "desktopicon"; Description: "바탕화면 바로가기 만들기"; GroupDescription: "추가 작업:"

[Files]
Source: "..\dist\TherapyChart.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\도수치료 기록 도우미"; Filename: "{app}\TherapyChart.exe"
Name: "{autodesktop}\도수치료 기록 도우미"; Filename: "{app}\TherapyChart.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TherapyChart.exe"; Description: "지금 프로그램 실행"; Flags: nowait postinstall skipifsilent
