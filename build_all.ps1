# build_all.ps1 — BG3 Mod Translator 빌드
#
# 기본 배포물(GitHub·Nexus 공용): Nuitka standalone 폴더(0/71)를 Inno Setup으로 감싼
#   단일 설치 파일  → BG3_ModTranslator_v<버전>_setup.exe
# 보조: 같은 폴더의 zip(무설치 사용자용)  → BG3_ModTranslator_v<버전>.zip
#
# 설치 파일은 onefile 패커와 달리 "신뢰 런타임 폴더 + 표준 인스톨러 포맷"이라 코드 서명
# 없이도 오탐이 거의 없다(Electron 앱이 NSIS로 미탐지를 얻는 것과 같은 원리).
#
# 사전 준비:
#   pip install nuitka            (+ pyinstaller — -Only exe 쓸 때만)
#   pip install -r requirements-gui.txt   (PySide6·lz4 등 런타임 의존성)
#   Inno Setup 6  https://jrsoftware.org/isdl.php   (설치 파일 생성에 필요)
#
# 사용:
#   pwsh -File build_all.ps1                 # 폴더 → 설치파일 + zip
#   pwsh -File build_all.ps1 -Only installer # 설치파일만
#   pwsh -File build_all.ps1 -Only zip       # zip만
#   pwsh -File build_all.ps1 -Only exe       # (레거시) PyInstaller 단일 EXE

param(
    [ValidateSet("all", "installer", "zip", "exe")]
    [string]$Only = "all"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$AppName = "BG3_ModTranslator"
$Entry = "bg3_mod_translator.py"
$Spec = "bg3_mod_translator.spec"

# 버전은 bg3core/constants.py 의 __version__ 을 단일 출처로 읽는다.
$Version = (python -c "import bg3core.constants as c; print(c.__version__)").Trim()
if (-not $Version) { throw "버전을 읽지 못했습니다 (bg3core/constants.py __version__)." }
Write-Host "==> BG3 Mod Translator v$Version 빌드 시작 (모드: $Only)" -ForegroundColor Cyan

function Find-ISCC {
    foreach ($p in @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )) { if (Test-Path $p) { return $p } }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

# ── (레거시) PyInstaller 단일 EXE ──────────────────────────────
if ($Only -eq "exe") {
    Write-Host "`n[PyInstaller] 단일 EXE 빌드..." -ForegroundColor Yellow
    python -m PyInstaller --noconfirm --clean $Spec
    $exe = Join-Path "dist" "$AppName.exe"
    if (-not (Test-Path $exe)) { throw "PyInstaller 산출물이 없습니다: $exe" }
    Write-Host "  ✅ $exe  (오탐 가능 — 가급적 설치파일/zip 사용 권장)" -ForegroundColor Green
    return
}

# ── Nuitka standalone 폴더 (설치파일·zip 공통 베이스) ──────────
$staged = Join-Path "nuitka_build" $AppName
Write-Host "`n[1] Nuitka standalone 폴더 빌드..." -ForegroundColor Yellow
$outDir = "nuitka_build"
if (Test-Path $outDir) { Remove-Item -Recurse -Force $outDir }

# exe에 버전 정보(회사·제품·설명)를 박아 "정상 소프트웨어"로 보이게 한다.
# 메타데이터가 비면 ML 백신이 의심 신호로 가중하므로 오탐을 줄이는 무료 조치.
# (아이콘이 있으면 --windows-icon-from-ico=resources\icon.ico 줄을 추가하면 더 좋다.)
python -m nuitka `
    --standalone `
    --assume-yes-for-downloads `
    --enable-plugin=pyside6 `
    --windows-console-mode=disable `
    --include-package=bg3gui `
    --include-package=bg3core `
    --include-package=bg3gui.i18n `
    --include-package=lz4 `
    --company-name=anboyu `
    --product-name="BG3 Mod Translator" `
    --file-version=$Version `
    --product-version=$Version `
    --file-description="BG3 Mod Translator - free AI localization for BG3 mods" `
    --copyright="Copyright (c) 2026 anboyu - MIT License" `
    --output-dir=$outDir `
    $Entry

# Nuitka standalone 출력: <outDir>\bg3_mod_translator.dist\
$distSrc = Join-Path $outDir "bg3_mod_translator.dist"
if (-not (Test-Path $distSrc)) { throw "Nuitka 산출물이 없습니다: $distSrc" }

# 폴더·실행파일 이름 정리 → nuitka_build\BG3_ModTranslator\BG3_ModTranslator.exe
if (Test-Path $staged) { Remove-Item -Recurse -Force $staged }
Rename-Item -Path $distSrc -NewName $AppName
$exeIn = Join-Path $staged "bg3_mod_translator.exe"
if (Test-Path $exeIn) { Rename-Item -Path $exeIn -NewName "$AppName.exe" }
Write-Host "  ✅ $staged" -ForegroundColor Green

# ── 설치 파일 (Inno Setup) — GitHub·Nexus 공용 ────────────────
if ($Only -eq "all" -or $Only -eq "installer") {
    Write-Host "`n[2] Inno Setup 설치 파일 생성..." -ForegroundColor Yellow
    $iscc = Find-ISCC
    if (-not $iscc) {
        Write-Warning "Inno Setup(ISCC.exe)을 찾지 못했습니다. 설치 파일을 건너뜁니다."
        Write-Warning "  설치: https://jrsoftware.org/isdl.php  (설치 후 다시 실행)"
    }
    else {
        & $iscc "/DMyAppVersion=$Version" "/DSourceDir=$staged" "installer.iss"
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup 컴파일 실패 (ISCC exit $LASTEXITCODE)." }
        $setup = "BG3_ModTranslator_v${Version}_setup.exe"
        if (-not (Test-Path $setup)) { throw "설치 파일 산출물이 없습니다: $setup" }
        Write-Host "  ✅ $setup" -ForegroundColor Green
    }
}

# ── zip (무설치 사용자용 보조) ────────────────────────────────
if ($Only -eq "all" -or $Only -eq "zip") {
    Write-Host "`n[3] zip 패킹..." -ForegroundColor Yellow
    $zip = "${AppName}_v$Version.zip"
    if (Test-Path $zip) { Remove-Item -Force $zip }
    Compress-Archive -Path $staged -DestinationPath $zip
    Write-Host "  ✅ $zip" -ForegroundColor Green
}

Write-Host "`n==> 완료. 산출물:" -ForegroundColor Cyan
if ($Only -eq "all" -or $Only -eq "installer") { Write-Host "  • BG3_ModTranslator_v${Version}_setup.exe  (GitHub·Nexus 공용, 권장)" }
if ($Only -eq "all" -or $Only -eq "zip") { Write-Host "  • ${AppName}_v$Version.zip  (무설치 보조)" }
