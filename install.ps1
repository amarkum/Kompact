# Kompactor installer (Windows PowerShell). From a clone of your team's repo:
#   .\install.ps1
# Or without a clone:
#   $env:KOMPACTOR_REPO = "amarkum/kompactor"; .\install.ps1
# Copies Kompactor to %USERPROFILE%\.kompactor\app (no pip needed), enables it for
# Claude Code (CLI + VS Code extension) and opens the dashboard.
$ErrorActionPreference = "Stop"
$Repo = $env:KOMPACTOR_REPO
$Ref = if ($env:KOMPACTOR_REF) { $env:KOMPACTOR_REF } else { "main" }
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

$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("kompactor-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $Tmp | Out-Null
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "kompactor\_launch.py"))) {
  # Run from a checkout (git clone ... ; .\install.ps1): install that copy
  $Origin = try { (& git -C $PSScriptRoot remote get-url origin 2>$null) } catch { "" }
  Write-Host "Installing Kompactor from $PSScriptRoot..."
  Copy-Item -Recurse -Path $PSScriptRoot -Destination (Join-Path $Tmp "src")
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Tmp "src\.git")
} else {
  if (-not $Repo) { throw "Run .\install.ps1 from a clone of your Kompactor repo, or set `$env:KOMPACTOR_REPO = 'your-org/kompactor'." }
  $Origin = "https://github.com/$Repo"
  Write-Host "Downloading Kompactor ($Repo@$Ref)..."
  $Zip = Join-Path $Tmp "kompactor.zip"
  Invoke-WebRequest -Uri "https://codeload.github.com/$Repo/zip/$Ref" -OutFile $Zip
  Expand-Archive -Path $Zip -DestinationPath $Tmp
  Remove-Item $Zip
}
$Src = Get-ChildItem -Path $Tmp -Directory | Select-Object -First 1
if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
Move-Item -Path $Src.FullName -Destination $Dest
# so the dashboard can show teammates the exact install commands for your repo (credentials stripped)
if ($Origin) { Set-Content -Path (Join-Path $Dest ".kompactor-source") -Value ($Origin -replace '^(https?://)[^/@]*@', '$1') }
Remove-Item -Recurse -Force $Tmp

$Shim = Join-Path $HOME ".kompactor\kompactor.cmd"
Set-Content -Path $Shim -Value "@`"$Py`" `"$Dest\kompactor\_launch.py`" %*"
Write-Host "Command shim: $Shim (add $HOME\.kompactor to PATH to type 'kompactor')"

& $Py "$Dest\kompactor\_launch.py" setup
