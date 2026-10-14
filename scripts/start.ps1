param([string]$NodeExecutable = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$viteCli = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
$runtimePath = Join-Path $projectRoot 'work'
New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
if (-not (Test-Path -LiteralPath $pythonExe)) { throw '未找到Python虚拟环境，请按README安装依赖。' }
if (-not (Test-Path -LiteralPath $viteCli)) { throw '未找到前端依赖，请先执行npm ci。' }
if (-not $NodeExecutable) {
    $NodeExecutable = (Get-Command node -ErrorAction Stop).Source
    $versionParts = (& $NodeExecutable --version).TrimStart('v').Split('.')
    $major = [int]$versionParts[0]
    $minor = [int]$versionParts[1]
    if (($major -lt 22) -or (($major -eq 22) -and ($minor -lt 12))) {
        $bundledNode = Join-Path $projectRoot 'work\runtime\node.exe'
        if (Test-Path -LiteralPath $bundledNode) { $NodeExecutable = $bundledNode } else { throw '请安装Node.js 22.12或更新版本，或通过-NodeExecutable指定路径。' }
    }
}
$selectedVersion = (& $NodeExecutable --version).TrimStart('v').Split('.')
if (([int]$selectedVersion[0] -lt 22) -or (([int]$selectedVersion[0] -eq 22) -and ([int]$selectedVersion[1] -lt 12))) { throw 'Node.js版本需要22.12或更新版本。' }
foreach ($portNumber in @(8000,5173)) {
    if (Get-NetTCPConnection -LocalPort $portNumber -State Listen -ErrorAction SilentlyContinue) { throw "端口$portNumber已被占用，请确认服务是否已启动。" }
}
$env:PYTHONIOENCODING = 'utf-8'
$backendProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--workers','1' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath 'backend.log') -RedirectStandardError (Join-Path $runtimePath 'backend-error.log') -PassThru
$frontendProcess = Start-Process -FilePath $NodeExecutable -ArgumentList ('"' + $viteCli + '"'),'--host','127.0.0.1','--port','5173' -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath 'frontend.log') -RedirectStandardError (Join-Path $runtimePath 'frontend-error.log') -PassThru
@{ backend = $backendProcess.Id; frontend = $frontendProcess.Id; python = $pythonExe; vite = $viteCli } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath 'processes.json') -Encoding utf8
Write-Output '启动请求已提交。前端：http://127.0.0.1:5173；接口：http://127.0.0.1:8000/docs。'
Write-Output '初始登录名见backend/.env中的ADMIN_USERNAME，密码见ADMIN_PASSWORD。日志保存在work/。'
