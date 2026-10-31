Unicode True
!include "MUI2.nsh"
!define APPNAME "NOMIKO"
!define VERSION "0.9.1"
!define MUI_ICON "..\assets\NOMIKO.ico"
!define MUI_UNICON "..\assets\NOMIKO.ico"
Name "${APPNAME} ${VERSION} Alpha"
OutFile "NOMIKO-Setup-0.9.1-alpha.exe"
InstallDir "$LOCALAPPDATA\Programs\NOMIKO"
RequestExecutionLevel user
SetShellVarContext current
SetCompressor /SOLID lzma
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Section "NOMIKO browser" SEC_MAIN
 SetShellVarContext current
 SetOutPath "$INSTDIR"
 File /r "..\dist\NOMIKO\*"
 File /oname=NOMIKO.ico "..\assets\NOMIKO.ico"
 WriteUninstaller "$INSTDIR\Uninstall.exe"
 CreateDirectory "$SMPROGRAMS\NOMIKO"
 CreateShortCut "$SMPROGRAMS\NOMIKO\NOMIKO.lnk" "$INSTDIR\NOMIKO.exe" "" "$INSTDIR\NOMIKO.ico" 0
 CreateShortCut "$SMPROGRAMS\NOMIKO\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
 CreateShortCut "$DESKTOP\NOMIKO.lnk" "$INSTDIR\NOMIKO.exe" "" "$INSTDIR\NOMIKO.ico" 0
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NOMIKO" "DisplayName" "NOMIKO ${VERSION} Alpha"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NOMIKO" "DisplayIcon" "$INSTDIR\NOMIKO.ico"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NOMIKO" "UninstallString" '"$INSTDIR\Uninstall.exe"'
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NOMIKO" "InstallLocation" "$INSTDIR"
 WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NOMIKO" "NoModify" 1
 WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NOMIKO" "NoRepair" 1
SectionEnd
Section "Uninstall"
 SetShellVarContext current
 Delete "$DESKTOP\NOMIKO.lnk"
 Delete "$SMPROGRAMS\NOMIKO\NOMIKO.lnk"
 Delete "$SMPROGRAMS\NOMIKO\Uninstall.lnk"
 RMDir "$SMPROGRAMS\NOMIKO"
 DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NOMIKO"
 RMDir /r "$INSTDIR"
 ; Preserve user browsing data at %APPDATA%\NOMIKO.
SectionEnd
