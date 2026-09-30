$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$gitCommand = Get-Command git.exe -ErrorAction SilentlyContinue
$gitExe = if ($gitCommand) { $gitCommand.Source } else { 'C:\Program Files\Git\cmd\git.exe' }
$env:GIT_TERMINAL_PROMPT = '0'

function Invoke-Git {
    param([string[]]$GitArgs)
    $result = & $gitExe -C $repoRoot @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "Git failed: $($GitArgs -join ' ')" }
    return $result
}

try {
    $remote = Invoke-Git @('remote', 'get-url', 'origin')
    if ($remote -notin @('https://github.com/jedgod/IoT-Device-Repository.git', 'git@github.com:jedgod/IoT-Device-Repository.git')) {
        throw 'Automatic push stopped: origin is not the expected GitHub repository.'
    }
    $branch = Invoke-Git @('symbolic-ref', '--quiet', '--short', 'HEAD')
    if (Invoke-Git @('diff', '--name-only', '--diff-filter=U')) {
        throw 'Resolve merge conflicts before automatically pushing.'
    }
    foreach ($marker in @('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD', 'REVERT_HEAD')) {
        $markerPath = Invoke-Git @('rev-parse', '--git-path', $marker)
        if (-not [IO.Path]::IsPathRooted($markerPath)) { $markerPath = Join-Path $repoRoot $markerPath }
        if (Test-Path -LiteralPath $markerPath) { throw 'Finish the active Git operation before automatically pushing.' }
    }
    if (Invoke-Git @('status', '--porcelain')) {
        Invoke-Git @('add', '--all') | Out-Host
        Invoke-Git @('commit', '-m', "chore: sync Claude Code updates $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')") | Out-Host
    }
    Invoke-Git @('push', '--set-upstream', 'origin', "HEAD:refs/heads/$branch") | Out-Host
} catch {
    [Console]::Error.WriteLine("Automatic GitHub sync failed: $($_.Exception.Message). Local changes are preserved; resolve the issue and retry.")
    exit 1
}
