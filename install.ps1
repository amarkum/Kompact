# Kompactor installer (Windows PowerShell), run from a clone:
#   git clone https://github.com/amarkum/kompactor.git; .\kompactor\install.ps1
# Without a clone, use PyPI instead: pipx install kompactor; kompactor setup
# Copies Kompactor to %USERPROFILE%\.kompactor\app (no pip needed), enables it for
# Claude Code (CLI + VS Code extension) and opens the dashboard.
$ErrorActionPreference = "Stop"
$Dest = Join-Path $HOME ".kompactor\app"

$Py = $null
foreach ($c in @(@("py", "-3"), @("python"), @("python3"))) {
  try {
    $exe = $c[0]; $pre = @($c | Select-Object -Skip 1)
    $ok = & $exe @pre -c "import sys; print(sys.version_info >= (3, 9))" 2>$null
    if ($ok -eq "True") { $Py = (& $exe @pre -c "import sys; print(sys.executable)").Trim(); break }
  } catch { }
}
if (-not $Py) { throw "Kompactor needs Python 3.9 or newer (https://www.python.org/downloads/)." }

if (-not ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "kompactor\_launch.py")))) {
  throw "Run .\install.ps1 from a clone of Kompactor, or install from PyPI: pipx install kompactor"
}
$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("kompactor-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $Tmp | Out-Null
Write-Host "Installing Kompactor from $PSScriptRoot..."
Copy-Item -Recurse -Path $PSScriptRoot -Destination (Join-Path $Tmp "src")
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Tmp "src\.git")
$Src = Get-ChildItem -Path $Tmp -Directory | Select-Object -First 1
if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
Move-Item -Path $Src.FullName -Destination $Dest
Remove-Item -Recurse -Force $Tmp

$Shim = Join-Path $HOME ".kompactor\kompactor.cmd"
Set-Content -Path $Shim -Value "@`"$Py`" `"$Dest\kompactor\_launch.py`" %*"
Write-Host "Command shim: $Shim (add $HOME\.kompactor to PATH to type 'kompactor')"

& $Py "$Dest\kompactor\_launch.py" setup
