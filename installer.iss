; Inno Setup 脚本 — CodePivot 安装包
; 使用方法: 先运行 build.bat 打包，再用 Inno Setup 编译此脚本

#define MyAppName "CodePivot"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "CodePivot"
#define MyAppExeName "AI模型切换器.exe"
#define MyAppDescription "AI 编程工具模型一键切换器"

[Setup]
AppId={{B8F3A2D1-5E7C-4A9B-8D6F-1C3E5A7B9D2F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=CodePivot_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"
Name: "startmenuicon"; Description: "Create Start Menu shortcut"

[Files]
; 复制 PyInstaller 输出的整个目录
Source: "dist\AI模型切换器\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenuicon; Comment: "{#MyAppDescription}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时清理运行时生成的配置文件
Type: files; Name: "{app}\config.json"
