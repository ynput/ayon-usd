<#
.SYNOPSIS
  Helper script to run various tasks on ayon-usd addon repository.

.DESCRIPTION
  This script helps to manage various management function from building
  to linting.

.EXAMPLE

PS> .\tools\manage.ps1

.EXAMPLE

To create virtual environment using uv:
PS> .\tools\manage.ps1 create-env

.EXAMPLE

To run Ruff check:
PS> .\tools\manage.ps1 ruff-check

.EXAMPLE
To build the addon package:
PS> .\tools\manage.ps1 build

.LINK
https://github.com/ynput/ayon-usd

#>
# Settings and gitmodule init
$CurrentDir = Get-Location
$ScriptDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$RepoRoot = (Get-Item $ScriptDir).parent.FullName
& git submodule update --init --recursive
$env:PSModulePath = $env:PSModulePath + ";$($openpype_root)\tools\modules\powershell"

$FunctionName=$ARGS[0]
$Arguments = @()
if ($ARGS.Length -gt 1) {
    $Arguments = $ARGS[1..($ARGS.Length - 1)]
}

function Exit-WithCode($exitcode) {
    # Only exit this host process if it's a child of another PowerShell parent process...
    $parentPID = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID" | Select-Object -Property ParentProcessId).ParentProcessId
    $parentProcName = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$parentPID" | Select-Object -Property Name).Name
    if ('powershell.exe' -eq $parentProcName) { $host.SetShouldExit($exitcode) }

    exit $exitcode
}

function Test-CommandExists {
    param (
        [Parameter(Mandatory=$true)]
        [string]$command
    )

    $commandExists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
    return $commandExists
}

function Write-Info {
    <#
    .SYNOPSIS
        Write-Info function to write information messages.

        It uses Write-Color if that is available, otherwise falls back to Write-Host.

    #>
    [CmdletBinding()]
    param (
        [alias ('T')] [String[]]$Text,
        [alias ('C', 'ForegroundColor', 'FGC')] [ConsoleColor[]]$Color = [ConsoleColor]::White,
        [alias ('B', 'BGC')] [ConsoleColor[]]$BackGroundColor = $null,
        [alias ('Indent')][int] $StartTab = 0,
        [int] $LinesBefore = 0,
        [int] $LinesAfter = 0,
        [int] $StartSpaces = 0,
        [alias ('L')] [string] $LogFile = '',
        [Alias('DateFormat', 'TimeFormat')][string] $DateTimeFormat = 'yyyy-MM-dd HH:mm:ss',
        [alias ('LogTimeStamp')][bool] $LogTime = $true,
        [int] $LogRetry = 2,
        [ValidateSet('unknown', 'string', 'unicode', 'bigendianunicode', 'utf8', 'utf7', 'utf32', 'ascii', 'default', 'oem')][string]$Encoding = 'Unicode',
        [switch] $ShowTime,
        [switch] $NoNewLine
    )
    if (Test-CommandExists "Write-Color") {
        Write-Color -Text $Text -Color $Color -BackGroundColor $BackGroundColor -StartTab $StartTab -LinesBefore $LinesBefore -LinesAfter $LinesAfter -StartSpaces $StartSpaces -LogFile $LogFile -DateTimeFormat $DateTimeFormat -LogTime $LogTime -LogRetry $LogRetry -Encoding $Encoding -ShowTime $ShowTime -NoNewLine $NoNewLine
    } else {
        $message = $Text -join ' '
        if ($NoNewLine)
        {
            Write-Host $message -NoNewline
        }
        else
        {
            Write-Host $message
        }
    }
}

$art = @"

                    ▄██▄
         ▄███▄ ▀██▄ ▀██▀ ▄██▀ ▄██▀▀▀██▄    ▀███▄      █▄
        ▄▄ ▀██▄  ▀██▄  ▄██▀ ██▀      ▀██▄  ▄  ▀██▄    ███
       ▄██▀  ██▄   ▀ ▄▄ ▀  ██         ▄██  ███  ▀██▄  ███
      ▄██▀    ▀██▄   ██    ▀██▄      ▄██▀  ███    ▀██ ▀█▀
     ▄██▀      ▀██▄  ▀█      ▀██▄▄▄▄██▀    █▀      ▀██▄

     ·  · - =[ by YNPUT ]:[ http://ayon.ynput.io ]= - ·  ·

"@

function Write-AsciiArt() {
    Write-Host $art -ForegroundColor DarkGreen
}

function Show-PSWarning() {
    if ($PSVersionTable.PSVersion.Major -lt 7) {
        Write-Info -Text "!!! ", "You are using old version of PowerShell - ",  "$($PSVersionTable.PSVersion.Major).$($PSVersionTable.PSVersion.Minor)" -Color Red, Yellow, White
        Write-Info -Text "    Please update to at least 7.0 - ", "https://github.com/PowerShell/PowerShell/releases" -Color Yellow, White
        Exit-WithCode 1
    }
}

function Install-Uv() {
    Write-Info -Text ">>> ", "Installing uv ... " -Color Green, Gray
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if ($LASTEXITCODE -ne 0) {
        Write-Info -Text "!!! ", "uv installation failed." -Color Red, Yellow
        Exit-WithCode 1
    }

    # Installer runs in child process and only updates persisted user PATH,
    # make uv available in this process too.
    $uvInstallDir = $env:UV_INSTALL_DIR
    if (-not $uvInstallDir) { $uvInstallDir = $env:XDG_BIN_HOME }
    if (-not $uvInstallDir) { $uvInstallDir = Join-Path (Join-Path $HOME ".local") "bin" }
    $env:Path = "$uvInstallDir;$env:Path"
    if (-not (Test-CommandExists "uv")) {
        Write-Info -Text "!!! ", "uv not found on PATH after installation." -Color Red, Yellow
        Exit-WithCode 1
    }
}

function Set-Cwd() {
    Set-Location -Path $RepoRoot
}

function Restore-Cwd() {
    $tmp_current_dir = Get-Location
    if ("$tmp_current_dir" -ne "$CurrentDir") {
        Write-Info -Text ">>> ", "Restoring current directory" -Color Green, Gray
        Set-Location -Path $CurrentDir
    }
}

function Initialize-Environment {
    Write-Info -Text ">>> ", "Reading uv ... " -Color Green, Gray -NoNewline
    if (-not (Test-CommandExists "uv"))
    {
        Write-Info -Text "NOT FOUND" -Color Yellow
        Install-Uv
        Write-Info -Text "INSTALLED" -Color Cyan
    }
    else
    {
        Write-Info -Text "OK" -Color Green
    }

    Write-Info -Text ">>> ", "Syncing virtual environment from lock." -Color Green, Gray
    $startTime = [int][double]::Parse((Get-Date -UFormat %s))
    & uv sync --all-groups
    if ($LASTEXITCODE -ne 0)
    {
        Write-Info -Text "!!! ", "uv sync failed." -Color Red, Yellow
        Restore-Cwd
        Exit-WithCode 1
    }
    if (Test-Path -PathType Container -Path "$( $RepoRoot )\.git")
    {
        Write-Info -Text ">>> ", "Installing pre-commit hooks ..." -Color Green, White
        & uv run pre-commit install
        if ($LASTEXITCODE -ne 0)
        {
            Write-Info -Text "!!! ", "Installation of pre-commit hooks failed." -Color Red, Yellow
        }
    }
    $endTime = [int][double]::Parse((Get-Date -UFormat %s))
    Restore-Cwd
    try
    {
        if (Test-CommandExists "New-BurntToastNotification")
        {
            $app_logo = "$RepoRoot\tools\icons\ayon.ico"
            New-BurntToastNotification -AppLogo "$app_logo" -Text "AYON", "Virtual environment created.", "All done in $( $endTime - $startTime ) secs."
        }
    }
    catch {}
    Write-Info -Text ">>> ", "Virtual environment created." -Color Green, White
}

function Invoke-Ruff {
    param (
        [switch] $Fix
    )
    $RuffArgs = @( "run", "ruff", "check" )
    if ($Fix) {
        $RuffArgs += "--fix"
    }
    & uv $RuffArgs
}

function Invoke-Codespell {
    param (
        [switch] $Fix
    )
    $CodespellArgs = @( "run", "codespell" )
    if ($Fix) {
        $CodespellArgs += "--fix"
    }
    & uv $CodespellArgs
}

function Write-Help {
    <#
    .SYNOPSIS
        Write-Help function to write help messages.
    #>
    Write-Host ""
    Write-Host "AYON Addon management script"
    Write-Host ""
    Write-Info -Text "Usage: ", "./manage.ps1 ", "[command]" -Color Gray, White, Cyan
    Write-Host ""
    Write-Host "Commands:"
    Write-Host -Text "  build                         ", "Build the addon package" -ForegroundColor White -BackgroundColor Cyan
    Write-Info -Text "  create-env                    ", "Install uv and update venv by lock file" -Color White, Cyan
    Write-Info -Text "  ruff-check                    ", "Run Ruff check for the repository" -Color White, Cyan
    Write-Info -Text "  ruff-fix                      ", "Run Ruff fix for the repository" -Color White, Cyan
    Write-Info -Text "  codespell                     ", "Run codespell check for the repository" -Color White, Cyan
    Write-Host ""
}

function Resolve-Function {
    if ($null -eq $FunctionName) {
        Write-Help
        return
    }
    $FunctionName = $FunctionName.ToLower() -replace "\W"
    if ($FunctionName -eq "createenv") {
        Set-Cwd
        Initialize-Environment
    } elseif ($FunctionName -eq "ruffcheck") {
        Set-Cwd
        Invoke-Ruff
    } elseif ($FunctionName -eq "rufffix") {
        Set-Cwd
        Invoke-Ruff -Fix
    } elseif ($FunctionName -eq "codespell") {
        Set-Cwd
        Invoke-CodeSpell
    } elseif ($FunctionName -eq "build") {
        Set-Cwd
        & uv run python "$RepoRoot\create_package.py"

        Write-Host "Package created in .\package folder."
    } else {
        Write-Host "Unknown function ""$FunctionName"""
        Write-Help
    }
}

# ----------------------------------------------------------------------------

Show-PSWarning
Write-AsciiArt

Resolve-Function
