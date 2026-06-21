# build_all.ps1 — BG3 Mod Translator 듀얼 빌드 (v6.0)
#
# 배포물 2종을 한 번에 생성한다:
#   1) GitHub용  : PyInstaller 단일 EXE   → dist\BG3_ModTranslator.exe
#   2) Nexus용   : Nuitka standalone 폴더 → BG3_ModTranslator_v<버전>.zip
#
# 사전 준비(가상환경 권장):
#   pip install pyinstaller nuitka
#   pip install -r requirements.txt   (PySide6 등 런타임 의존성)
#
# 사용:
#   pwsh -File build_all.ps1            # 둘 다 빌드
#   pwsh -File build_all.ps1 -Only exe  # PyInstaller만
#   pwsh -File build_all.ps1 -Only zip  # Nuitka(zip)만

param(
    [ValidateSet("all", "exe", "zip")]
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

# ── 1) PyInstaller 단일 EXE (GitHub용) ─────────────────────────
if ($Only -eq "all" -or $Only -eq "exe") {
    Write-Host "`n[1/2] PyInstaller 단일 EXE 빌드..." -ForegroundColor Yellow
    python -m PyInstaller --noconfirm --clean $Spec
    $exe = Join-Path "dist" "$AppName.exe"
    if (-not (Test-Path $exe)) { throw "PyInstaller 산출물이 없습니다: $exe" }
    Write-Host "  ✅ $exe" -ForegroundColor Green
}

# ── 2) Nuitka standalone 폴더 → zip (Nexus용) ──────────────────
if ($Only -eq "all" -or $Only -eq "zip") {
    Write-Host "`n[2/2] Nuitka standalone 빌드..." -ForegroundColor Yellow
    $outDir = "nuitka_build"
    if (Test-Path $outDir) { Remove-Item -Recurse -Force $outDir }

    python -m nuitka `
        --standalone `
        --assume-yes-for-downloads `
        --enable-plugin=pyside6 `
        --windows-console-mode=disable `
        --include-package=bg3gui `
        --include-package=bg3core `
        --include-package=bg3gui.i18n `
        --output-dir=$outDir `
        $Entry

    # Nuitka standalone 출력: <outDir>\bg3_mod_translator.dist\
    $distSrc = Join-Path $outDir "bg3_mod_translator.dist"
    if (-not (Test-Path $distSrc)) { throw "Nuitka 산출물이 없습니다: $distSrc" }

    # 폴더·실행파일 이름 정리
    $staged = Join-Path $outDir $AppName
    if (Test-Path $staged) { Remove-Item -Recurse -Force $staged }
    Rename-Item -Path $distSrc -NewName $AppName
    $exeIn = Join-Path $staged "bg3_mod_translator.exe"
    if (Test-Path $exeIn) { Rename-Item -Path $exeIn -NewName "$AppName.exe" }

    # zip 패킹
    $zip = "${AppName}_v$Version.zip"
    if (Test-Path $zip) { Remove-Item -Force $zip }
    Compress-Archive -Path $staged -DestinationPath $zip
    Write-Host "  ✅ $zip" -ForegroundColor Green
}

Write-Host "`n==> 완료. 산출물:" -ForegroundColor Cyan
if ($Only -ne "zip") { Write-Host "  • dist\$AppName.exe  (GitHub Release 업로드)" }
if ($Only -ne "exe") { Write-Host "  • ${AppName}_v$Version.zip  (Nexus 업로드)" }
