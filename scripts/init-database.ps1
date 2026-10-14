param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw '请先创建backend/.venv并安装requirements.lock.txt。' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'backend\.env'))) { throw '请先复制backend/.env.example为.env并填写配置。' }
$env:PYTHONIOENCODING = 'utf-8'
Push-Location (Join-Path $projectRoot 'backend')
try {
    & $pythonExe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw '数据库迁移失败。' }
    if ($Demo) { & $pythonExe -m app.infrastructure.seed --demo } else { & $pythonExe -m app.infrastructure.seed }
    if ($LASTEXITCODE -ne 0) { throw '初始化失败。' }
} finally { Pop-Location }
