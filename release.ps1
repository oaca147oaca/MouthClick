param(
    [ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version = '1.4.0',
    [switch]$NoConsole
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$releaseWork = Join-Path $PSScriptRoot ".visual-build\release-$Version"
$releaseDist = Join-Path $releaseWork 'dist'
$releaseBuild = Join-Path $releaseWork 'build'
$releaseApp = Join-Path $releaseDist 'MouthClick'
$compiler = @(
    "${env:ProgramFiles}\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compiler) { throw 'No se encontro Inno Setup.' }
& py -3.11 -m unittest test_runtime test_lighting
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas.' }
# Windowed builds; retain NoConsole for compatibility with older commands.
& py -3.11 -m PyInstaller --noconfirm --clean --distpath $releaseDist --workpath $releaseBuild MouthClick.spec
if ($LASTEXITCODE -ne 0) { throw 'Fallo PyInstaller.' }
# Only seed the base profile; preserve local profiles and enable first-run setup.
$seedScript = @'
import json, sys
from pathlib import Path
profiles = json.loads(Path('profiles.json').read_text(encoding='utf-8'))
base = dict(profiles.get('Por Defecto', next(iter(profiles.values()))))
base = {k:v for k,v in base.items() if not k.startswith('_')}
base.update(camera=0, setup_complete=False, startup_default=True)
Path(sys.argv[1]).write_text(json.dumps({'Por Defecto':base}, ensure_ascii=False, indent=4), encoding='utf-8')
'@
$seedScript | & py -3.11 - (Join-Path $releaseApp 'profiles.json')
if ($LASTEXITCODE -ne 0) { throw 'Fallo la preparacion del perfil inicial.' }
"MouthClick $Version`r`nWindows 10/11 x64`r`nBuild: $(Get-Date -Format o)" | Set-Content -LiteralPath (Join-Path $releaseApp 'VERSION.txt') -Encoding UTF8
& $compiler "/DMyAppVersion=$Version" "/DAppSource=$releaseApp" (Join-Path $PSScriptRoot 'MouthClick.iss')
if ($LASTEXITCODE -ne 0) { throw 'Fallo Inno Setup.' }
$installerPath = Join-Path $PSScriptRoot "Entregas\MouthClick_Setup_v$Version.exe"
if (-not (Test-Path -LiteralPath $installerPath)) { throw 'No se encontro el instalador.' }
Get-Item -LiteralPath $installerPath | Select-Object FullName, Length
Get-FileHash -LiteralPath $installerPath -Algorithm SHA256
exit 0
