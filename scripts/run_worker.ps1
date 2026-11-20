# 手动启动 ARQ worker（前台运行，日志直接打到控制台）。
# 日常不用这个脚本：Windows 计划任务 CoveWorker 直接由 cmd.exe 托管，
# 详见 README 的「本地开发」章节。

Set-Location -LiteralPath "D:\Cove"
$env:PYTHONPATH = "D:\Cove"
& "D:\Cove\.venv\Scripts\python.exe" -m arq app.worker.WorkerSettings
