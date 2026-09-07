# Extract using the actual installer's function, but only into a fresh workspace test directory.
# Never run Python setup, change PATH globally, or execute question-bank code.
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$bundle = Join-Path $repo '.trainer\offline-assets'
$installer = Join-Path $repo 'apps\vscode-extension\scripts\install-offline-runtime.ps1'
$manifest = Get-Content -LiteralPath (Join-Path $repo 'apps\vscode-extension\resources\offline-runtime.json') -Raw | ConvertFrom-Json
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($installer, [ref]$null, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'Installer syntax errors.' }
foreach ($definition in $ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Extract-PinnedZip'}, $true)) {
    . ([ScriptBlock]::Create($definition.Extent.Text))
}
Add-Type -AssemblyName System.IO.Compression
$resultRoot = [IO.Path]::GetFullPath((Join-Path $repo ('.trainer\environment-test-' + [Guid]::NewGuid().ToString('N'))))
if (-not $resultRoot.StartsWith((Join-Path $repo '.trainer') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid test target.' }
New-Item -ItemType Directory -Path $resultRoot | Out-Null
foreach ($id in @('compiler','boost')) {
    $stage = Join-Path $resultRoot $id
    New-Item -ItemType Directory -Path $stage | Out-Null
    Extract-PinnedZip $manifest.$id $stage ($id -eq 'boost')
    Write-Output "Extracted $id to $stage"
}
$bin = Join-Path $resultRoot 'compiler\bin'
# These environment values affect this test process and its children only.
$env:PATH = $bin + ';' + $env:PATH
$env:CPLUS_INCLUDE_PATH = Join-Path $resultRoot 'boost'
$cOutput = Join-Path $resultRoot 'smoke-c.exe'
$cppOutput = Join-Path $resultRoot 'smoke-cpp.exe'
& (Join-Path $bin 'clang.exe') -std=c11 -Wall -Wextra -Werror (Join-Path $PSScriptRoot 'fixtures\compiler-smoke.c') -o $cOutput
if ($LASTEXITCODE -ne 0) { throw 'C11 smoke compilation failed.' }
& $cOutput
if ($LASTEXITCODE -ne 0) { throw 'C11 smoke execution failed.' }
& (Join-Path $bin 'clang++.exe') -std=c++17 -Wall -Wextra (Join-Path $PSScriptRoot 'fixtures\compiler-smoke.cpp') -o $cppOutput
if ($LASTEXITCODE -ne 0) { throw 'C++17 and Boost smoke compilation failed.' }
& $cppOutput
if ($LASTEXITCODE -ne 0) { throw 'C++17 and Boost smoke execution failed.' }
Write-Output ('PASS C11, C++17, Boost; no question code executed. Test directory: ' + $resultRoot)
