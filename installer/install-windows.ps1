# Prerequisites for Windows 11 (amd64), then installer/install-ubuntu.sh and installer/install.sh inside WSL2
# (ADR-08, SPEC-02 §2.3). It only prepares the host: every installation decision stays in install.sh and grdm-dev.
#
# What it may change, after showing it and asking: the WSL feature (administrator, through a UAC prompt), the
# Ubuntu-24.04 distribution, and a clone of this repository inside the WSL file system. It never clones under
# /mnt/c, and it does not install Docker Desktop, whose licence is the user's decision.
#
# Compatible with Windows PowerShell 5.1. The file is UTF-8 with a BOM: without one, 5.1 reads it in the system
# code page and the Japanese strings break the parser. Exit codes are those of installer/grdm_dev/messages.tsv:
# 2 refused or no consent, 10 host, 11 Docker.
[CmdletBinding(PositionalBinding = $false)]
param(
    [switch]$Yes,
    [switch]$DryRun,
    [switch]$Help,
    [string]$Branch = 'develop',
    [string]$Directory = 'RDM-developer-guide',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$InstallArgs = @()
)

$ErrorActionPreference = 'Stop'
$Distro = 'Ubuntu-24.04'
$RepoUrl = 'https://github.com/RCOSDP/RDM-developer-guide.git'
$Script:Plan = New-Object System.Collections.ArrayList

function Write-Both([string]$English, [string]$Japanese) {
    Write-Host "[install-windows.ps1] $English"
    if ($Japanese) { Write-Host "[install-windows.ps1] $Japanese" }
}

function Stop-Prereq([int]$Code, [string]$English, [string]$Japanese) {
    if ($DryRun) {
        Write-Both "[dry-run] would stop with exit ${Code}: $English" $Japanese
        return
    }
    [Console]::Error.WriteLine("[install-windows.ps1] exit ${Code}: $English")
    if ($Japanese) { [Console]::Error.WriteLine("  $Japanese") }
    exit $Code
}

function Test-Interactive {
    return ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected)
}

function Confirm-Step([string]$English, [string]$Japanese) {
    if ($Yes) { return }
    if ($DryRun) {
        if (-not (Test-Interactive)) {
            Write-Both '[dry-run] would stop with exit 2: no terminal and no -Yes' '[dry-run] 端末が無く -Yes も無いため終了 2 で止まります'
        }
        return
    }
    if (-not (Test-Interactive)) {
        Stop-Prereq 2 'no terminal to ask on: add -Yes to consent' '確認する端末がありません。同意するには -Yes を付けてください'
    }
    Write-Host $English
    $answer = Read-Host "$Japanese [y/N]"
    if ($answer -notmatch '^(y|yes)$') {
        Stop-Prereq 2 'declined; nothing further was changed' '同意がなかったため、これ以上は変更しません'
    }
}

function Get-WslText([string[]]$Arguments) {
    # wsl.exe prints UTF-16; read as text it arrives with NUL characters between the letters.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & wsl.exe @Arguments 2>$null
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    $text = (($output | ForEach-Object { "$_" }) -join "`n") -replace "`0", ''
    return @{ Code = $code; Text = $text }
}

function ConvertTo-BashWord([string]$Value) {
    return "'" + ($Value -replace "'", "'\''") + "'"
}

if ($Help) {
    @'
Usage: powershell -ExecutionPolicy Bypass -File installer\install-windows.ps1 [-Yes] [-DryRun] [-Branch <name>] [-Directory <name>] [grdm-dev install options...]

  Prepares WSL2 with Ubuntu 24.04, checks Docker Desktop, clones this repository inside WSL, and runs the installer there.
    -Yes        consent to every change listed in the plan (--yes also works)
    -DryRun     detect and print what would happen; change nothing (--dry-run also works)
    -Branch     branch to clone (default: develop)
    -Directory  folder under your WSL home directory (default: RDM-developer-guide)
  Other options go to install.sh unchanged, for example --profile minimum.

使い方: powershell -ExecutionPolicy Bypass -File installer\install-windows.ps1 [-Yes] [-DryRun] [-Branch <名前>] [-Directory <名前>] [grdm-dev install のオプション...]

  WSL2 と Ubuntu 24.04 を準備し、Docker Desktop を確認し、WSL の中にこのリポジトリを clone して、そこでインストーラーを実行します。
    -Yes        計画に載せたすべての変更に同意する（--yes も可）
    -DryRun     判定して予定を表示するだけで、何も変更しない（--dry-run も可）
    -Branch     clone するブランチ（既定: develop）
    -Directory  WSL のホームディレクトリの下のフォルダ（既定: RDM-developer-guide）
  ほかのオプションはそのまま install.sh に渡します。例: --profile minimum
'@ | Write-Host
    exit 0
}

# Unix-style flags, so that the same habits work on every OS.
$Forward = New-Object System.Collections.ArrayList
foreach ($argument in $InstallArgs) {
    switch ($argument) {
        '--yes' { $Yes = $true }
        '-y' { $Yes = $true }
        '--dry-run' { $DryRun = $true }
        default { [void]$Forward.Add($argument) }
    }
}
if ($Yes) { [void]$Forward.Add('--yes') }

# The folder must be a plain name under the WSL home: that is what keeps the clone off /mnt/c.
if ($Directory -notmatch '^[A-Za-z0-9._-]+$' -or $Directory -match '^\.+$') {
    [Console]::Error.WriteLine('[install-windows.ps1] exit 2: -Directory must be one folder name under the WSL home directory, never a path such as /mnt/c/... / -Directory は WSL のホームの下のフォルダ名一つにしてください。/mnt/c/... のようなパスは使えません')
    exit 2
}
if ($Branch -notmatch '^[A-Za-z0-9._/-]+$') {
    [Console]::Error.WriteLine('[install-windows.ps1] exit 2: -Branch contains characters that are not allowed / -Branch に使えない文字が含まれています')
    exit 2
}

# --- host check (read-only) --------------------------------------------------------------------------
$build = [Environment]::OSVersion.Version.Build
if ([Environment]::OSVersion.Platform -ne 'Win32NT' -or $build -lt 22000) {
    Stop-Prereq 10 "Windows 11 is required (this is build $build)." "Windows 11 が必要です（このホストのビルドは $build）。"
}
$cpu = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
if ($cpu -ne 'AMD64') {
    Stop-Prereq 10 "Only amd64 Windows is supported (this is $cpu)." "対応するのは amd64 の Windows だけです（このホストは $cpu）。"
}

# --- detection (read-only) ---------------------------------------------------------------------------
$wslReady = $false
if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    $wslReady = (Get-WslText @('--status')).Code -eq 0
}
$distroPresent = $false
$distroVersion = ''
if ($wslReady) {
    foreach ($line in ((Get-WslText @('--list', '--verbose')).Text -split "`n")) {
        $fields = ($line -replace '^\s*\*?\s*', '') -split '\s+'
        if ($fields.Count -ge 3 -and $fields[0] -eq $Distro) {
            $distroPresent = $true
            $distroVersion = $fields[2]
        }
    }
}
if (-not $wslReady) {
    [void]$Script:Plan.Add(@('administrator: enable WSL2 (wsl.exe --install --no-distribution); a restart may be needed', '管理者: WSL2 を有効にする（wsl.exe --install --no-distribution）。再起動が要ることがあります'))
}
if (-not $distroPresent) {
    [void]$Script:Plan.Add(@("install the $Distro distribution from Microsoft's catalog", "Microsoft のカタログから $Distro を入れる"))
} elseif ($distroVersion -ne '2') {
    [void]$Script:Plan.Add(@("convert $Distro to WSL version 2", "$Distro を WSL 版 2 に変換する"))
}
[void]$Script:Plan.Add(@("inside WSL: install git with sudo if it is absent, clone $RepoUrl (branch $Branch) to ~/$Directory if absent, then run installer/install-ubuntu.sh, which lists its own changes", "WSL の中で: git が無ければ sudo で入れ、無ければ $RepoUrl（ブランチ $Branch）を ~/$Directory に clone し、installer/install-ubuntu.sh を実行する（変更点はそのスクリプトが示します）"))

Write-Both 'This script will make these changes:' 'このスクリプトは次の変更を行います:'
$number = 0
foreach ($item in $Script:Plan) {
    $number++
    Write-Host "  $number. $($item[0])"
    Write-Host "     $($item[1])"
}
Write-Both 'Note: the integration repositories are private. This script never asks for, reads or stores a token.' '注意: 統合リポジトリは非公開です。このスクリプトはトークンを尋ねず、読まず、保存しません。'
Write-Both 'Inside WSL, before the build, give git your own access, for example: gh auth login, then gh auth setup-git' 'WSL の中で、ビルドの前に git へ自分の権限を設定してください。例: gh auth login の後に gh auth setup-git'
Confirm-Step 'Make these changes?' 'これらの変更を行いますか?'

# --- changes -----------------------------------------------------------------------------------------
if (-not $wslReady) {
    if ($DryRun) {
        Write-Both '[dry-run] administrator (UAC prompt): wsl.exe --install --no-distribution'
    } else {
        $process = Start-Process -FilePath 'wsl.exe' -ArgumentList '--install', '--no-distribution' -Verb RunAs -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            Stop-Prereq 10 "wsl.exe --install failed with code $($process.ExitCode)." "wsl.exe --install がコード $($process.ExitCode) で失敗しました。"
        }
        Stop-Prereq 10 'WSL was enabled. Restart Windows, then run this script again.' 'WSL を有効にしました。Windows を再起動して、もう一度実行してください。'
    }
}

if (-not $distroPresent) {
    if ($DryRun) {
        Write-Both "[dry-run] wsl.exe --install --distribution $Distro --no-launch"
    } else {
        & wsl.exe --install --distribution $Distro --no-launch
        if ($LASTEXITCODE -ne 0) {
            Stop-Prereq 10 "Could not install $Distro (code $LASTEXITCODE)." "$Distro を入れられませんでした（コード $LASTEXITCODE）。"
        }
    }
} elseif ($distroVersion -ne '2') {
    if ($DryRun) {
        Write-Both "[dry-run] wsl.exe --set-version $Distro 2"
    } else {
        & wsl.exe --set-version $Distro 2
        if ($LASTEXITCODE -ne 0) {
            Stop-Prereq 10 "Could not convert $Distro to WSL version 2 (code $LASTEXITCODE)." "$Distro を WSL 版 2 に変換できませんでした（コード $LASTEXITCODE）。"
        }
    }
}

# Everything below talks to the distribution, which a dry run may not have.
if (-not $DryRun) {
    $identity = Get-WslText @('--distribution', $Distro, '--exec', 'id', '-u')
    if ($identity.Code -ne 0 -or $identity.Text.Trim() -eq '0') {
        Stop-Prereq 10 "$Distro has no regular user yet. Run 'wsl -d $Distro' once, create your user, then run this script again." "$Distro にまだ一般利用者がいません。'wsl -d $Distro' を一度実行して利用者を作り、もう一度実行してください。"
    }
}

$desktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
$desktopHelp = 'https://www.docker.com/products/docker-desktop/'
$engineAnswers = $false
if (-not $DryRun) {
    $engineAnswers = (Get-WslText @('--distribution', $Distro, '--exec', 'docker', 'info', '--format', 'ok')).Code -eq 0
}
if (-not $engineAnswers) {
    if (-not (Test-Path -LiteralPath $desktop)) {
        Stop-Prereq 11 "Docker Desktop was not found. Install it from $desktopHelp (check that its licence fits your organisation), start it, then run this script again." "Docker Desktop が見つかりません。$desktopHelp から入れ（ライセンスが所属組織に合うか確認してください）、起動してから、もう一度実行してください。"
    } elseif (-not $DryRun) {
        Stop-Prereq 11 "Docker does not answer inside $Distro. Start Docker Desktop and enable Settings > Resources > WSL Integration > $Distro, then run this script again." "$Distro の中で Docker が応答しません。Docker Desktop を起動し、Settings > Resources > WSL Integration > $Distro を有効にして、もう一度実行してください。"
    }
}

# The boot script travels base64-encoded in one environment variable, so no quoting layer of PowerShell, wsl.exe
# or the login shell can change it, and the terminal stays attached for sudo and the installer's questions.
$forwardWords = ($Forward | ForEach-Object { ConvertTo-BashWord $_ }) -join ' '
$bootLines = @(
    'set -euo pipefail',
    'cd "$HOME"',
    'case "$HOME" in /mnt/*) echo "the WSL home directory is on the Windows disk; refusing to clone there" >&2; exit 10 ;; esac',
    'if ! command -v git >/dev/null 2>&1; then',
    '  sudo apt-get update && sudo apt-get install -y git',
    'fi',
    "target=`"`$HOME/$Directory`"",
    'if [ -d "$target/.git" ]; then',
    '  echo "using the existing checkout at $target; it is not changed"',
    'else',
    "  git clone --branch $(ConvertTo-BashWord $Branch) $(ConvertTo-BashWord $RepoUrl) `"`$target`"",
    'fi',
    'cd "$target"',
    "exec bash installer/install-ubuntu.sh $forwardWords"
)
$boot = ($bootLines -join "`n") + "`n"

if ($DryRun) {
    Write-Both "[dry-run] would run inside ${Distro}:"
    Write-Host $boot
    exit 0
}

$env:GRDM_WSL_BOOT = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($boot))
$env:WSLENV = if ($env:WSLENV) { "$($env:WSLENV):GRDM_WSL_BOOT" } else { 'GRDM_WSL_BOOT' }
& wsl.exe --distribution $Distro --cd '~' --exec bash -c 'source <(base64 -d <<<$GRDM_WSL_BOOT)'
exit $LASTEXITCODE
