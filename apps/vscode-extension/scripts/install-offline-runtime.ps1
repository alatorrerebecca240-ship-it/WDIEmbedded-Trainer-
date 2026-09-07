param(
    [Parameter(Mandatory=$true)][string]$BundleDirectory,
    [Parameter(Mandatory=$true)][string]$Components
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$manifestPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'resources\offline-runtime.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$requested = $Components.Split(',')
if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') { throw 'Windows x64 required.' }
if (@($requested | Where-Object { $_ -notin @('python','compiler','boost') }).Count) { throw 'Unsupported component.' }
$bundle = (Resolve-Path -LiteralPath $BundleDirectory).Path
$local = [Environment]::GetFolderPath('LocalApplicationData')
$base = [IO.Path]::GetFullPath((Join-Path $local 'Programs\EmbeddedTrainer'))
$pythonTarget = [IO.Path]::GetFullPath((Join-Path $local ('Programs\Python\' + $manifest.python.directory)))
$lock = $null
$work = $null
function Check-ReparseAncestors([string]$Target) {
    $cursor = $Target
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            if ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point refused: $cursor" }
        }
        $parent = Split-Path -Parent $cursor
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}
function Check-Hash([string]$File, [string]$Expected) {
    if ((Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected) { throw "SHA-256 mismatch: $File" }
}
function Extract-PinnedZip($Asset, [string]$Stage, [bool]$HeadersOnly) {
    $inputFile = Join-Path $bundle $Asset.file
    $stream = [IO.File]::Open($inputFile, 'Open', 'Read', 'Read')
    $zip = $null
    try {
        $hasher = [Security.Cryptography.SHA256]::Create()
        try { $actual = [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-','').ToLowerInvariant() } finally { $hasher.Dispose() }
        if ($actual -ne $Asset.sha256) { throw 'ZIP changed after verification.' }
        $stream.Position = 0
        $zip = New-Object IO.Compression.ZipArchive($stream, [IO.Compression.ZipArchiveMode]::Read, $true)
        $seen = New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
        $count = 0
        $total = [long]0
        foreach ($entry in $zip.Entries) {
            $name = $entry.FullName.Replace('\','/')
            if ($name -notmatch ('^' + [regex]::Escape($Asset.directory) + '/')) { throw 'Unexpected archive root.' }
            if ($name -match '(^/|:|(^|/)\.\.(/|$)|[<>"|?*])' -or $name -match '[. ](/|$)') { throw 'Unsafe ZIP entry.' }
            if ((($entry.ExternalAttributes -shr 16) -band 61440) -eq 40960) { throw 'Symbolic link in archive refused.' }
            if (-not $seen.Add($name.TrimEnd('/'))) { throw 'Duplicate ZIP entry.' }
            $count++; $total += $entry.Length
            if ($count -gt 150000 -or $total -gt 5GB) { throw 'Archive expansion limit exceeded.' }
            $relative = $name.Substring($Asset.directory.Length + 1)
            if (-not $relative) { continue }
            if ($HeadersOnly -and $relative -notmatch '^(boost/|LICENSE_1_0.txt$)') { continue }
            $target = [IO.Path]::GetFullPath((Join-Path $Stage $relative))
            if (-not $target.StartsWith($Stage + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Archive path escaped staging directory.' }
            if ($name.EndsWith('/')) { [IO.Directory]::CreateDirectory($target) | Out-Null; continue }
            [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
            $src = $entry.Open(); $dst = $null
            try { $dst = [IO.File]::Open($target, 'CreateNew', 'Write', 'None'); $src.CopyTo($dst) }
            finally { if ($dst) { $dst.Dispose() }; $src.Dispose() }
        }
    } finally { if ($zip) { $zip.Dispose() }; $stream.Dispose() }
}
try {
    Check-ReparseAncestors $base
    Check-ReparseAncestors $pythonTarget
    New-Item -ItemType Directory -Force -Path $base | Out-Null
    $lock = [IO.File]::Open((Join-Path $base '.offline-install.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    $work = Join-Path $base ('install-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $work | Out-Null
    Add-Type -AssemblyName System.IO.Compression
    foreach ($id in $requested) { Check-Hash (Join-Path $bundle $manifest.$id.file) $manifest.$id.sha256 }
    foreach ($id in $requested) {
        $asset = $manifest.$id
        if ($id -eq 'python') {
            if (Test-Path -LiteralPath $pythonTarget) { throw "Existing Python directory will not be overwritten: $pythonTarget" }
            # A private directory prevents a bundle-provided unattend.xml from changing installation options.
            $installer = Join-Path $work $asset.file
            Copy-Item -LiteralPath (Join-Path $bundle $asset.file) -Destination $installer
            Check-Hash $installer $asset.sha256
            # The official publisher signature is checked when building the bundle.
            # Runtime uses the extension-pinned SHA-256; no online CRL/certificate fetch.
            $log = Join-Path $work 'python-install.log'
            $args = @('/quiet','/norestart','InstallAllUsers=0',('TargetDir="' + $pythonTarget + '"'),
                'PrependPath=0','AppendPath=0','Include_launcher=0','InstallLauncherAllUsers=0','AssociateFiles=0',
                'Shortcuts=0','Include_doc=0','Include_test=0','Include_tcltk=0','Include_pip=1',
                'Include_dev=1','Include_exe=1','Include_lib=1','Include_debug=0','Include_symbols=0',
                'Include_freethreaded=0','/log',('"' + $log + '"'))
            $process = Start-Process -FilePath $installer -ArgumentList $args -PassThru -WindowStyle Hidden
            if (-not $process.WaitForExit(900000)) { throw "Python installation still running. Check $log before retrying." }
            if ($process.ExitCode -notin @(0,3010)) { throw "Python installer exit code $($process.ExitCode). Log: $log" }
            if (-not (Test-Path -LiteralPath (Join-Path $pythonTarget 'python.exe'))) { throw 'Python executable not found after install.' }
            Write-Output "Installed Python: $pythonTarget"
        } else {
            $target = [IO.Path]::GetFullPath((Join-Path $base $asset.directory))
            if (-not $target.StartsWith($base + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid install target.' }
            Check-ReparseAncestors $target
            if (Test-Path -LiteralPath $target) {
                $marker = Join-Path $target '.embedded-trainer-sha256'
                if ((Test-Path -LiteralPath $marker) -and (Get-Content -LiteralPath $marker -Raw).Trim() -eq $asset.sha256) {
                    Write-Output "Already installed: $target"; continue
                }
                throw "Existing directory will not be overwritten: $target"
            }
            $stage = [IO.Path]::GetFullPath((Join-Path $work $id))
            New-Item -ItemType Directory -Path $stage | Out-Null
            Extract-PinnedZip $asset $stage ($id -eq 'boost')
            $required = if ($id -eq 'compiler') { 'bin\clang.exe' } else { 'boost\version.hpp' }
            if (-not (Test-Path -LiteralPath (Join-Path $stage $required))) { throw 'Incomplete archive.' }
            [IO.File]::WriteAllText((Join-Path $stage '.embedded-trainer-sha256'), $asset.sha256)
            # Exact paths checked above. Rename only this fresh task-owned staging directory.
            Move-Item -LiteralPath $stage -Destination $target
            Write-Output "Installed $id`: $target"
        }
    }
    Write-Output "Logs and installer recovery files: $work"
} catch {
    Write-Error $_
    exit 1
} finally {
    if ($lock) { $lock.Dispose() }
    # Keep logs / incomplete staging for diagnosis; never remove an existing environment.
}
