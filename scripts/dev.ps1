<#
  一键起本地环境。
    1. 后端 8000（API + 同源托管 frontend/dist）
    2. 前端热更新 5173（Vite，/api 自动代理到 8000）
  用法：powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
        powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 -NoFrontend
#>
param([switch]$NoFrontend)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$frontend = Join-Path $root 'frontend'
$dist = Join-Path $frontend 'dist'

if (-not (Test-Path $python)) {
    throw "找不到虚拟环境 Python：$python （先执行 uv sync）"
}
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host '前端依赖还没装，先跑一次 npm install …' -ForegroundColor Yellow
    Push-Location $frontend; npm install; Pop-Location
}
if (-not (Test-Path (Join-Path $dist 'index.html'))) {
    Write-Host 'dist 不存在，先构建一次 …' -ForegroundColor Yellow
    Push-Location $frontend; npm run build; Pop-Location
}

Write-Host '[1/2] uvicorn  http://127.0.0.1:8000  (API + SPA, --reload)' -ForegroundColor Cyan
Start-Process -FilePath 'powershell' -WorkingDirectory $root -ArgumentList @(
    '-NoExit', '-Command',
    "Set-Location '$root'; & '$python' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

if (-not $NoFrontend) {
    Write-Host '[2/2] vite     http://127.0.0.1:5173  (热更新)' -ForegroundColor Cyan
    Start-Process -FilePath 'powershell' -WorkingDirectory $frontend -ArgumentList @(
        '-NoExit', '-Command',
        "Set-Location '$frontend'; npm run dev"
    )
}

Write-Host ''
Write-Host '地址：' -ForegroundColor Green
Write-Host '  App（热更新）   http://127.0.0.1:5173/'
Write-Host '  App（同源）     http://127.0.0.1:8000/'
Write-Host '  接口文档        http://127.0.0.1:8000/docs'
Write-Host '  健康检查        http://127.0.0.1:8000/health'
Write-Host ''
Write-Host '装到手机：cd frontend && npm run cap:android' -ForegroundColor DarkGray
