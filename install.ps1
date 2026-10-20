# Kompact one-line installer (Windows PowerShell):
#   irm https://raw.githubusercontent.com/amarkum/Kompact/main/install.ps1 | iex
# Downloads Kompact to %USERPROFILE%\.kompact\app (no pip needed), enables it for
# Claude Code (CLI + VS Code extension) and opens the dashboard.
$ErrorActionPreference = "Stop"
$Repo = if ($env:KOMPACT_REPO) { $env:KOMPACT_REPO } else { "amarkum/Kompact" }
$Ref = if ($env:KOMPACT_REF) { $env:KOMPACT_REF } else { "main" }
$Dest = Join-Path $HOME ".kompact\app"

$Py = $null
foreach ($c in @(@("py", "-3"), @("python"), @("python3"))) {
  try {
    $exe = $c[0]; $pre = @($c | Select-Object -Skip 1)
    $ok = & $exe @pre -c "import sys; print(sys.version_info >= (3, 9))" 2>$null
    if ($ok -eq "True") { $Py = (& $exe @pre -c "import sys; print(sys.executable)").Trim(); break }
  } catch { }
}
if (-not $Py) { throw "Kompact needs Python 3.9 or newer (https://www.python.org/downloads/)." }

Write-Host "Downloading Kompact ($Repo@$Ref)..."
$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("kompact-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $Tmp | Out-Null
$Zip = Join-Path $Tmp "kompact.zip"
Invoke-WebRequest -Uri "https://codeload.github.com/$Repo/zip/$Ref" -OutFile $Zip
Expand-Archive -Path $Zip -DestinationPath $Tmp
$Src = Get-ChildItem -Path $Tmp -Directory | Select-Object -First 1
if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
Move-Item -Path $Src.FullName -Destination $Dest
Remove-Item -Recurse -Force $Tmp

$Shim = Join-Path $HOME ".kompact\kompact.cmd"
Set-Content -Path $Shim -Value "@`"$Py`" `"$Dest\kompact\_launch.py`" %*"
Write-Host "Command shim: $Shim (add $HOME\.kompact to PATH to type 'kompact')"

& $Py "$Dest\kompact\_launch.py" setup
