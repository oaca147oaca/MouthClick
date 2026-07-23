param(
    [string]$Version = "1.0.0",
    [switch]$NoConsole
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# -----------------------------
# CONFIGURACION
# -----------------------------
$AppName = "MouthClick"
$Publisher = "Fundacion Teleton"
$PythonVersion = "3.11"

$MainScript = "mouthclick_mvp_opticalflow.py"
$ProfilesFile = "profiles.json"
$InnoScript = "MouthClick.iss"

$BuildFolder = "build"
$DistFolder = "dist"
$InstallerFolder = "installer"
$ReleaseFolder = "Release"

$SpecFile = "$AppName.spec"
$DistAppFolder = Join-Path $DistFolder $AppName
$ExePath = Join-Path $DistAppFolder "$AppName.exe"

$PortableZipName = "${AppName}_Portable_v${Version}.zip"
$InstallerFinalName = "${AppName}_Setup_v${Version}.exe"

function Write-Section {
    param([string]$Text)

    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Stop-Release {
    param([string]$Message)

    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    Write-Host ""
    Read-Host "Presiona ENTER para cerrar"
    exit 1
}

Clear-Host
Write-Section "GENERADOR DE RELEASE DE MOUTHCLICK"

Write-Host "Aplicacion : $AppName"
Write-Host "Version    : $Version"
Write-Host "Publicador : $Publisher"
Write-Host "Carpeta    : $PSScriptRoot"

# -----------------------------
# 1. VERIFICAR ARCHIVOS
# -----------------------------
Write-Section "1. VERIFICANDO ARCHIVOS"

if (-not (Test-Path ".\$MainScript")) {
    Stop-Release "No se encontro $MainScript"
}

if (-not (Test-Path ".\$InnoScript")) {
    Stop-Release "No se encontro $InnoScript"
}

if (-not (Test-Path ".\$ProfilesFile")) {
    Write-Host "ADVERTENCIA: no se encontro $ProfilesFile" -ForegroundColor Yellow
}

Write-Host "Archivos principales encontrados." -ForegroundColor Green

# -----------------------------
# 2. VERIFICAR PYTHON
# -----------------------------
Write-Section "2. VERIFICANDO PYTHON"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Stop-Release "No se encontro el comando py"
}

& py "-$PythonVersion" --version

if ($LASTEXITCODE -ne 0) {
    Stop-Release "No se encontro Python $PythonVersion"
}

# -----------------------------
# 3. VERIFICAR PYINSTALLER
# -----------------------------
Write-Section "3. VERIFICANDO PYINSTALLER"

& py "-$PythonVersion" -m PyInstaller --version

if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando PyInstaller..." -ForegroundColor Yellow
    & py "-$PythonVersion" -m pip install --upgrade pyinstaller

    if ($LASTEXITCODE -ne 0) {
        Stop-Release "No se pudo instalar PyInstaller"
    }
}

# -----------------------------
# 4. BUSCAR INNO SETUP
# -----------------------------
Write-Section "4. BUSCANDO INNO SETUP"

$PossibleInnoPaths = @(
    "${env:ProgramFiles}\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)

$ISCC = $PossibleInnoPaths |
    Where-Object { $_ -and (Test-Path $_) } |
    Select-Object -First 1

if (-not $ISCC) {
    Stop-Release "No se encontro ISCC.exe"
}

Write-Host "Inno Setup encontrado en:" -ForegroundColor Green
Write-Host $ISCC -ForegroundColor Green

# -----------------------------
# 5. LIMPIAR
# -----------------------------
Write-Section "5. LIMPIANDO COMPILACIONES ANTERIORES"

foreach ($Folder in @($BuildFolder, $DistFolder, $InstallerFolder, $ReleaseFolder)) {
    if (Test-Path ".\$Folder") {
        Remove-Item ".\$Folder" -Recurse -Force
    }
}

if (Test-Path ".\$SpecFile") {
    Remove-Item ".\$SpecFile" -Force
}

New-Item -ItemType Directory -Path ".\$ReleaseFolder" -Force | Out-Null

# -----------------------------
# 6. COMPILAR CON PYINSTALLER
# -----------------------------
Write-Section "6. COMPILANDO CON PYINSTALLER"

$ConsoleArgument = if ($NoConsole) { "--noconsole" } else { "--console" }

$PyInstallerArguments = @(
    "-$PythonVersion",
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    $ConsoleArgument,
    "--name",
    $AppName,
    "--collect-submodules",
    "mediapipe.python.solutions",
    "--collect-data",
    "mediapipe",
    "--collect-binaries",
    "mediapipe",
    "--collect-all",
    "pygrabber",
    "--collect-all",
    "comtypes",
    "--hidden-import",
    "comtypes.client",
    "--hidden-import",
    "pynput",
    "--hidden-import",
    "pyautogui",
    "--hidden-import",
    "tkinter",
    $MainScript
)

& py @PyInstallerArguments

if ($LASTEXITCODE -ne 0) {
    Stop-Release "PyInstaller termino con errores"
}

if (-not (Test-Path $ExePath)) {
    Stop-Release "No se encontro $ExePath"
}

Write-Host "Ejecutable generado correctamente." -ForegroundColor Green

# -----------------------------
# 7. COPIAR ARCHIVOS EXTRA
# -----------------------------
Write-Section "7. COPIANDO ARCHIVOS ADICIONALES"

if (Test-Path ".\$ProfilesFile") {
    Copy-Item ".\$ProfilesFile" $DistAppFolder -Force
}

$VersionText = @(
    $AppName
    "Version: $Version"
    "Publicador: $Publisher"
    "Fecha de compilacion: $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')"
    "Python utilizado: $PythonVersion"
)

$VersionText | Set-Content (Join-Path $DistAppFolder "VERSION.txt") -Encoding UTF8

# -----------------------------
# 8. ACTUALIZAR VERSION EN ISS
# -----------------------------
Write-Section "8. ACTUALIZANDO VERSION EN INNO SETUP"

$InnoContent = Get-Content ".\$InnoScript" -Raw
$VersionPattern = '#define MyAppVersion ".*?"'
$VersionReplacement = "#define MyAppVersion `"$Version`""

if ($InnoContent -match $VersionPattern) {
    $InnoContent = $InnoContent -replace $VersionPattern, $VersionReplacement
    Set-Content ".\$InnoScript" $InnoContent -Encoding UTF8
    Write-Host "Version actualizada a $Version." -ForegroundColor Green
}
else {
    Write-Host "ADVERTENCIA: no se encontro MyAppVersion en $InnoScript" -ForegroundColor Yellow
}

# -----------------------------
# 9. COMPILAR INSTALADOR
# -----------------------------
Write-Section "9. COMPILANDO INSTALADOR"

& $ISCC ".\$InnoScript"

if ($LASTEXITCODE -ne 0) {
    Stop-Release "Inno Setup termino con errores"
}

$GeneratedInstaller = Join-Path $InstallerFolder "${AppName}_Setup.exe"

if (-not (Test-Path $GeneratedInstaller)) {
    $InstallerFound = Get-ChildItem ".\$InstallerFolder" -Filter "*.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($InstallerFound) {
        $GeneratedInstaller = $InstallerFound.FullName
    }
}

if (-not (Test-Path $GeneratedInstaller)) {
    Stop-Release "No se encontro el instalador generado"
}

$FinalInstallerPath = Join-Path $ReleaseFolder $InstallerFinalName
Copy-Item $GeneratedInstaller $FinalInstallerPath -Force

# -----------------------------
# 10. CREAR ZIP PORTATIL
# -----------------------------
Write-Section "10. GENERANDO ZIP PORTATIL"

$PortableZipPath = Join-Path $ReleaseFolder $PortableZipName

Compress-Archive `
    -Path "$DistAppFolder\*" `
    -DestinationPath $PortableZipPath `
    -CompressionLevel Optimal `
    -Force

if (-not (Test-Path $PortableZipPath)) {
    Stop-Release "No se pudo generar el ZIP portatil"
}

# -----------------------------
# 11. CREAR NOTAS
# -----------------------------
Write-Section "11. CREANDO NOTAS DE VERSION"

$ReleaseNotesPath = Join-Path $ReleaseFolder "NOTAS_VERSION_$Version.txt"

$ReleaseNotes = @(
    "MOUTHCLICK"
    "Version $Version"
    ""
    "Fecha de publicacion:"
    "$(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')"
    ""
    "ARCHIVOS GENERADOS"
    ""
    "1. $InstallerFinalName"
    "   Instalador recomendado para computadoras nuevas."
    "   Incluye MouthClick y sus dependencias."
    ""
    "2. $PortableZipName"
    "   Version portatil."
    "   Extraer completamente antes de ejecutar MouthClick.exe."
    ""
    "REQUISITOS"
    ""
    "- Windows 10 u 11 de 64 bits."
    "- Camara web compatible."
    "- Permisos para acceder a la camara."
    "- No requiere instalar Python."
    "- No requiere instalar MediaPipe."
    "- No requiere ejecutar pip."
)

$ReleaseNotes | Set-Content $ReleaseNotesPath -Encoding UTF8

# -----------------------------
# 12. RESUMEN
# -----------------------------
Write-Section "RELEASE GENERADA CORRECTAMENTE"

$InstallerSize = [math]::Round((Get-Item $FinalInstallerPath).Length / 1MB, 2)
$ZipSize = [math]::Round((Get-Item $PortableZipPath).Length / 1MB, 2)

Write-Host "Version: $Version" -ForegroundColor Green
Write-Host ""
Write-Host "Instalador:"
Write-Host "  $FinalInstallerPath"
Write-Host "  Tamano: $InstallerSize MB"
Write-Host ""
Write-Host "Portable:"
Write-Host "  $PortableZipPath"
Write-Host "  Tamano: $ZipSize MB"
Write-Host ""
Write-Host "Notas:"
Write-Host "  $ReleaseNotesPath"
Write-Host ""

Invoke-Item ".\$ReleaseFolder"