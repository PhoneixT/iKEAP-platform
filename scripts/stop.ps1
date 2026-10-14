$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot 'work\processes.json'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Output '没有项目进程记录。'; return }
$records = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
foreach ($entry in @(@{ Id = $records.backend; Kind = 'backend' }, @{ Id = $records.frontend; Kind = 'frontend' })) {
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($entry.Id)" -ErrorAction SilentlyContinue
    if (-not $processInfo) { continue }
    $matchesProject = if ($entry.Kind -eq 'backend') { $processInfo.ExecutablePath -eq $records.python } else { $processInfo.CommandLine -and $processInfo.CommandLine.Contains($records.vite) }
    if (-not $matchesProject) { throw "进程$($entry.Id)与项目记录不一致，未停止该进程。" }
    Stop-Process -Id $entry.Id -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath $pidFile
Write-Output '项目进程已停止。'
