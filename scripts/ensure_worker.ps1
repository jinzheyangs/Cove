# 由 Windows 计划任务 CoveWorker 每 5 分钟调用。
# 只在没有 arq worker 在跑时才拉起一个，避免重复 worker 导致 cron 重复执行。

$running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'arq\s+app\.worker\.WorkerSettings' }

if ($running) {
  Write-Output "worker already running (pid $($running.ProcessId -join ','))"
  exit 0
}

Set-Location -LiteralPath "D:\Cove"
Start-Process -FilePath "cmd.exe" -ArgumentList '/c', "cd /d D:\Cove && .venv\Scripts\python.exe -m arq app.worker.WorkerSettings >> D:\Cove\logs\worker.log 2>&1" -WindowStyle Hidden
Write-Output "worker started"
exit 0
