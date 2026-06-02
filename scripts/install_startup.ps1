<#
.SYNOPSIS
    注册每日任务仪表盘为开机自启任务（Windows 任务计划程序）

.DESCRIPTION
    此脚本会在用户登录时自动启动 daily-dashboard 服务。
    需要以管理员身份运行 PowerShell。

.EXAMPLE
    # 以管理员身份运行：
    powershell -ExecutionPolicy Bypass -File scripts\install_startup.ps1
#>

$ProjectDir = Resolve-Path "$PSScriptRoot\.."
$StartScript = "$ProjectDir\scripts\start.bat"
$TaskName = "DailyDashboard"

# 检查是否以管理员身份运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] 请以管理员身份运行此脚本！" -ForegroundColor Red
    Write-Host "        右键点击 PowerShell，选择「以管理员身份运行」" -ForegroundColor Yellow
    exit 1
}

# 创建计划任务
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$StartScript`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "每日任务仪表盘 — 开机自动启动" `
    -Force

Write-Host "[SUCCESS] 开机自启已注册！" -ForegroundColor Green
Write-Host "        任务名称: $TaskName" -ForegroundColor Cyan
Write-Host "        启动脚本: $StartScript" -ForegroundColor Cyan
Write-Host ""
Write-Host "如需取消自启，请运行：" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor Gray
