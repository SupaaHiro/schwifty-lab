<#
.SYNOPSIS
    Signs PowerShell scripts with an Authenticode certificate loaded from a PFX file.

.DESCRIPTION
    Invoke-ScriptSigning consolidates single-file and batch signing into one tool.

    Two target modes:
      - Single file  : -SourcePath points to a .ps1 / .psm1 / .psd1 file.
      - Directory    : -SourcePath points to a folder; use -Recurse for sub-folders.

    Two signing modes:
      - In-place     : files are signed where they are (default).
      - Copy mode    : files are copied from -SourcePath to -DestinationPath first,
                       then signed in the destination tree.

    The certificate must be a valid, unexpired code-signing certificate that includes
    a private key.  Its password is requested interactively when not supplied via
    -CertificatePassword (recommended for interactive use; avoid plain-text passwords
    in scripts or CI pipelines — use a SecureString from a vault instead).

.PARAMETER CertificatePath
    Path to the PFX/P12 file that contains the code-signing certificate and private key.

.PARAMETER CertificatePassword
    Password for the PFX file as a SecureString.
    When omitted the user is prompted interactively.

.PARAMETER SourcePath
    Path to the script file or directory to sign.

.PARAMETER DestinationPath
    When specified, switches to Copy mode: files are copied from SourcePath to this
    path before signing.  Must not overlap with SourcePath.

.PARAMETER Recurse
    Search sub-directories when SourcePath is a directory.

.PARAMETER Extensions
    File extensions to process.  Defaults to .ps1, .psm1, .psd1.

.PARAMETER ExcludeDirectory
    Directory names to skip during traversal.
    Defaults to: .git  .vs  bin  obj  node_modules

.PARAMETER TimestampServer
    RFC 3161 timestamp server URL.  Enables long-term signature validity after
    certificate expiry (recommended for production).
    Example: http://timestamp.digicert.com

.EXAMPLE
    # Sign a single file in-place (password prompted)
    .\Invoke-ScriptSigning.ps1 -CertificatePath .\pki\code-sign.pfx -SourcePath .\Deploy.ps1

.EXAMPLE
    # Sign all scripts in .\src recursively, writing signed copies to .\out
    .\Invoke-ScriptSigning.ps1 `
        -CertificatePath  .\pki\code-sign.pfx `
        -SourcePath       .\src `
        -DestinationPath  .\out `
        -Recurse

.EXAMPLE
    # Automation: supply password from a SecureString (e.g. from a secrets vault)
    $pwd = ConvertTo-SecureString $env:PFX_PASSWORD -AsPlainText -Force
    .\Invoke-ScriptSigning.ps1 `
        -CertificatePath     .\pki\code-sign.pfx `
        -CertificatePassword $pwd `
        -SourcePath          .\src `
        -Recurse `
        -TimestampServer     http://timestamp.digicert.com

.EXAMPLE
    # Dry run: preview what would be signed without touching any file
    .\Invoke-ScriptSigning.ps1 -CertificatePath .\pki\code-sign.pfx -SourcePath .\src -Recurse -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, DefaultParameterSetName = 'InPlace')]
param(
    [Parameter(Mandatory)]
    [string] $CertificatePath,

    [Parameter()]
    [System.Security.SecureString] $CertificatePassword,

    [Parameter(Mandatory)]
    [string] $SourcePath,

    [Parameter(ParameterSetName = 'CopyMode')]
    [string] $DestinationPath,

    [Parameter()]
    [switch] $Recurse,

    [Parameter()]
    [string[]] $Extensions = @('.ps1', '.psm1', '.psd1'),

    [Parameter()]
    [string[]] $ExcludeDirectory = @('.git', '.vs', 'bin', 'obj', 'node_modules'),

    [Parameter()]
    [string] $TimestampServer
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# On non-Windows platforms, ensure the OpenAuthenticode module is available.
if ($IsLinux -or $IsMacOS) {
    $moduleName = 'OpenAuthenticode'
    if (-not (Get-Module -ListAvailable -Name $moduleName)) {
        Write-Host "Installing required module '$moduleName' from PSGallery..." -ForegroundColor Yellow
        Install-Module -Name $moduleName -Scope CurrentUser -Force
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

function Resolve-FullPath {
    param([string] $Path, [string] $Label)
    try { return [IO.Path]::GetFullPath($Path) }
    catch { throw "$Label is not a valid path: '$Path'" }
}

function Import-SigningCertificate {
    [OutputType([System.Security.Cryptography.X509Certificates.X509Certificate2])]
    param(
        [string]                    $PfxPath,
        [System.Security.SecureString] $Password
    )

    Write-Verbose "Importing certificate: $PfxPath"
    try {
        if ($IsLinux -or $IsMacOS) {
            $cert = Get-PfxCertificate `
                -FilePath $PfxPath `
                -Password $Password
        }
        else {
            $cert = Import-PfxCertificate `
                -FilePath          $PfxPath `
                -CertStoreLocation Cert:\CurrentUser\My `
                -Password          $Password
        }
    }
    catch {
        throw "Failed to import PFX '$PfxPath': $($_.Exception.Message)"
    }

    if (-not $cert.HasPrivateKey) {
        throw "Certificate '$($cert.Subject)' does not contain a private key."
    }

    if ($cert.NotAfter -lt (Get-Date)) {
        throw "Certificate '$($cert.Subject)' expired on $($cert.NotAfter.ToString('yyyy-MM-dd'))."
    }

    $codeSignOid = '1.3.6.1.5.5.7.3.3'
    $eku = $cert.Extensions |
    Where-Object { $_ -is [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension] }

    if (-not $eku) {
        throw "Certificate '$($cert.Subject)' has no Enhanced Key Usage extension. A code-signing certificate is required."
    }

    $hasCodeSign = $eku.EnhancedKeyUsages | Where-Object { $_.Value -eq $codeSignOid }
    if (-not $hasCodeSign) {
        throw "Certificate '$($cert.Subject)' does not carry the Code Signing EKU (OID $codeSignOid)."
    }

    Write-Host "[CERT] $($cert.Subject)  |  expires $($cert.NotAfter.ToString('yyyy-MM-dd'))" -ForegroundColor Green
    return $cert
}

function Get-TargetFiles {
    param(
        [string]   $Directory,
        [string[]] $Extensions,
        [string[]] $ExcludeDirectory,
        [switch]   $Recurse
    )

    $results = [System.Collections.Generic.List[System.IO.FileInfo]]::new()

    $items = Get-ChildItem -Path $Directory -File -Recurse:$Recurse.IsPresent
    foreach ($file in $items) {
        if ($Recurse) {
            # Build path segments relative to the root to detect excluded dirs
            $relative = $file.FullName.Substring($Directory.Length)
            $parts = $relative.Split(
                [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar),
                [System.StringSplitOptions]::RemoveEmptyEntries
            )
            # The last element is the filename itself; check intermediate segments only
            $dirParts = $parts | Select-Object -SkipLast 1
            if ($dirParts | Where-Object { $ExcludeDirectory -contains $_ }) { continue }
        }

        if ($Extensions -contains $file.Extension) {
            [void] $results.Add($file)
        }
    }

    return , $results
}

function Invoke-FileSign {
    [OutputType([bool])]
    param(
        [string] $FilePath,
        [System.Security.Cryptography.X509Certificates.X509Certificate2] $Certificate,
        [string] $TimestampServer
    )

    if ($IsLinux -or $IsMacOS) {
        $params = @{
            Path          = $FilePath
            Certificate   = $Certificate
            HashAlgorithm = 'SHA256'
        }
        if ($TimestampServer) { $params['TimeStampServer'] = $TimestampServer }
        $result = Set-OpenAuthenticodeSignature @params
    }
    else {
        $params = @{
            FilePath      = $FilePath
            Certificate   = $Certificate
            HashAlgorithm = 'SHA256'
        }
        if ($TimestampServer) { $params['TimestampServer'] = $TimestampServer }
        $result = Set-AuthenticodeSignature @params
    }

    if ($result.Status -eq 'Valid') {
        Write-Host "  [OK]   $FilePath" -ForegroundColor Green
        return $true
    }
    else {
        Write-Warning "  [FAIL] $FilePath — $($result.Status): $($result.StatusMessage)"
        return $false
    }
}

function Copy-SourceTree {
    param(
        [string]   $Source,
        [string]   $Destination,
        [string[]] $ExcludeDirectory,
        [switch]   $Recurse
    )

    Write-Verbose "Copying '$Source' -> '$Destination'"

    if (Test-Path -LiteralPath $Source -PathType Leaf) {
        $destDir = Split-Path $Destination -Parent
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
        Copy-Item -LiteralPath $Source -Destination $Destination -Force
        return
    }

    if (-not (Test-Path $Destination)) { New-Item -ItemType Directory -Path $Destination -Force | Out-Null }

    Get-ChildItem -Path $Source -Recurse:$Recurse.IsPresent | ForEach-Object {
        $item = $_
        $relative = $item.FullName.Substring($Source.Length).TrimStart(
            [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
        )

        $parts = $relative.Split(
            [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar),
            [System.StringSplitOptions]::RemoveEmptyEntries
        )
        if ($parts | Where-Object { $ExcludeDirectory -contains $_ }) { return }

        $destItem = Join-Path $Destination $relative
        if ($item.PSIsContainer) {
            if (-not (Test-Path $destItem)) { New-Item -ItemType Directory -Path $destItem -Force | Out-Null }
        }
        else {
            Copy-Item -LiteralPath $item.FullName -Destination $destItem -Force
        }
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Parameter validation
# ─────────────────────────────────────────────────────────────────────────────

$CertificatePath = Resolve-FullPath $CertificatePath '-CertificatePath'
$SourcePath = Resolve-FullPath $SourcePath      '-SourcePath'

if (-not (Test-Path -LiteralPath $CertificatePath)) {
    throw "Certificate file not found: '$CertificatePath'"
}
if (-not (Test-Path -LiteralPath $SourcePath)) {
    throw "SourcePath not found: '$SourcePath'"
}

$isSingleFile = Test-Path -LiteralPath $SourcePath -PathType Leaf
$isCopyMode = $PSBoundParameters.ContainsKey('DestinationPath')

if ($isCopyMode) {
    $DestinationPath = Resolve-FullPath $DestinationPath '-DestinationPath'

    if (-not $isSingleFile) {
        $srcNorm = $SourcePath.TrimEnd('\', '/')
        $dstNorm = $DestinationPath.TrimEnd('\', '/')
        if ($dstNorm -eq $srcNorm) {
            throw '-DestinationPath must differ from -SourcePath.'
        }
        $sep = [IO.Path]::DirectorySeparatorChar
        if ($DestinationPath.StartsWith($SourcePath + $sep)) {
            throw "-DestinationPath ('$DestinationPath') is inside -SourcePath ('$SourcePath'). This would cause a copy loop."
        }
    }
}

if ($isSingleFile -and $Recurse) {
    Write-Warning '-Recurse has no effect when -SourcePath is a single file.'
}

# ─────────────────────────────────────────────────────────────────────────────
# Certificate password
# ─────────────────────────────────────────────────────────────────────────────

if (-not $CertificatePassword) {
    $CertificatePassword = Read-Host -Prompt 'Enter PFX certificate password' -AsSecureString
}

# ─────────────────────────────────────────────────────────────────────────────
# Import & validate certificate
# ─────────────────────────────────────────────────────────────────────────────

$cert = Import-SigningCertificate -PfxPath $CertificatePath -Password $CertificatePassword

# ─────────────────────────────────────────────────────────────────────────────
# Main flow
# ─────────────────────────────────────────────────────────────────────────────

$modeLabel = if ($isCopyMode) { 'Copy then sign' } else { 'In-place sign' }
Write-Host ''
Write-Host "Mode   : $modeLabel" -ForegroundColor Cyan
Write-Host "Source : $SourcePath"
if ($isCopyMode) { Write-Host "Dest   : $DestinationPath" }
Write-Host ''

$successCount = 0
$failCount = 0

if ($isSingleFile) {
    # ── Single-file path ──────────────────────────────────────────────────────
    if ($isCopyMode) {
        if ($PSCmdlet.ShouldProcess($SourcePath, "Copy to '$DestinationPath'")) {
            Copy-SourceTree -Source $SourcePath -Destination $DestinationPath `
                -ExcludeDirectory $ExcludeDirectory
        }
        $signTarget = $DestinationPath
    }
    else {
        $signTarget = $SourcePath
    }

    if ($PSCmdlet.ShouldProcess($signTarget, 'Set-AuthenticodeSignature')) {
        if (Invoke-FileSign -FilePath $signTarget -Certificate $cert -TimestampServer $TimestampServer) {
            $successCount++
        }
        else {
            $failCount++
        }
    }
}
else {
    # ── Directory path ────────────────────────────────────────────────────────
    if ($isCopyMode) {
        Write-Host "Copying tree ..." -ForegroundColor DarkCyan
        if ($PSCmdlet.ShouldProcess($SourcePath, "Copy to '$DestinationPath'")) {
            Copy-SourceTree -Source $SourcePath -Destination $DestinationPath `
                -ExcludeDirectory $ExcludeDirectory -Recurse:$Recurse
        }
    }

    $signingRoot = if ($isCopyMode) { $DestinationPath } else { $SourcePath }
    $files = Get-TargetFiles -Directory $signingRoot -Extensions $Extensions `
        -ExcludeDirectory $ExcludeDirectory -Recurse:$Recurse

    if ($files.Count -eq 0) {
        Write-Warning "No files matching ($($Extensions -join ', ')) found in '$signingRoot'."
        exit 0
    }

    Write-Host "Signing $($files.Count) file(s) in '$signingRoot' ..."
    Write-Host ''

    foreach ($file in $files) {
        if ($PSCmdlet.ShouldProcess($file.FullName, 'Set-AuthenticodeSignature')) {
            if (Invoke-FileSign -FilePath $file.FullName -Certificate $cert -TimestampServer $TimestampServer) {
                $successCount++
            }
            else {
                $failCount++
            }
        }
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

Write-Host ''
Write-Host '─────────────────────────────────' -ForegroundColor DarkGray
Write-Host "Signed : $successCount" -ForegroundColor Green
if ($failCount -gt 0) {
    Write-Host "Failed : $failCount" -ForegroundColor Red
}
Write-Host '─────────────────────────────────' -ForegroundColor DarkGray

if ($failCount -gt 0) { exit 1 }
