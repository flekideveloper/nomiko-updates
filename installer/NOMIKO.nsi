Unicode True
!include "MUI2.nsh"
!define APPNAME "NOMIKO"
!define VERSION "0.9.0"
Name "${APPNAME} ${VERSION} Alpha"
OutFile "NOMIKO-Setup-0.9.0-alpha.exe"
InstallDir "$LOCALAPPDATA\Programs\NOMIKO"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Section "NOMIKO browser" SEC_MAIN
 SetOutPath "$INSTDIR"
 File /r "${__FILEDIR__}\..\dist\NOMIKO\*"
 WriteUninstaller "$INSTDIR\Uninstall.exe"
 CreateDirectory "$SMPROGRAMS\NOMIKO"
 CreateShortCut "$SMPROGRAMS\NOMIKO\NOMIKO.lnk" "$INSTDIR\NOMIKO.exe"
 CreateShortCut "$SMPROGRAMS\NOMIKO\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd
Section "Uninstall"
 RMDir /r "$INSTDIR"
 RMDir /r "$SMPROGRAMS\NOMIKO"
 ; Intentionally preserve %APPDATA%\NOMIKO browser data on uninstall.
SectionEnd
