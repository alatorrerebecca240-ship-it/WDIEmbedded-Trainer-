$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
}
if ($null -eq $pythonCommand) {
    throw "需要 Python 3.9 或更高版本。"
}

Push-Location $projectRoot
try {
    if ($pythonCommand.Name -eq "py.exe" -or $pythonCommand.Name -eq "py") {
        & $pythonCommand.Source -3 trainer.py doctor
        & $pythonCommand.Source -3 trainer.py validate
    } else {
        & $pythonCommand.Source trainer.py doctor
        & $pythonCommand.Source trainer.py validate
    }
} finally {
    Pop-Location
}

