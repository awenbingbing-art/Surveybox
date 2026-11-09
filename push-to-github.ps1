# 一键把本目录推到 GitHub
# 用法：
#   .\push-to-github.ps1 -User 你的GitHub用户名
#   .\push-to-github.ps1 -User 你的GitHub用户名 -Repo my-survey-tool -Private
# 需要：一个带 repo 权限的 Personal Access Token（会安全提示输入，不落盘）

param(
    [Parameter(Mandatory = $true)][string]$User,
    [string]$Repo = "beijing-air-survey",
    [switch]$Private
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- 1. 取 token（安全输入，不进历史记录）---
$sec = Read-Host -AsSecureString "粘贴 GitHub Personal Access Token（输入不回显）"
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
$Token = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
if (-not $Token) { throw "没有拿到 token" }

$pair = "{0}:{1}" -f $User, $Token
$basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
$headers = @{ Authorization = "Basic $basic"; "User-Agent" = "dsh-push" }

# --- 2. 不存在就建仓 ---
$api = "https://api.github.com/repos/$User/$Repo"
$exists = $true
try {
    Invoke-RestMethod -Uri $api -Headers $headers -Method Get -TimeoutSec 30 | Out-Null
    Write-Host "· 仓库已存在：$User/$Repo"
} catch {
    $exists = $false
}

if (-not $exists) {
    $body = @{
        name        = $Repo
        description = "本地问卷采集与统计工具：零依赖 Python，自带问卷页、统计看板与导出"
        private     = [bool]$Private
        has_issues  = $true
        auto_init   = $false
    } | ConvertTo-Json
    Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Headers $headers `
        -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30 | Out-Null
    Write-Host "· 已创建仓库：$User/$Repo"
}

# --- 3. 设置 remote 并推送 ---
$url = "https://github.com/$User/$Repo.git"
$hasOrigin = (git remote) -contains "origin"
if ($hasOrigin) { git remote set-url origin $url } else { git remote add origin $url }
Write-Host "· remote = $url"

git -c "http.extraheader=AUTHORIZATION: Basic $basic" push -u origin main
if ($LASTEXITCODE -ne 0) { throw "推送失败，检查 token 权限（需要 repo 读写）" }

Write-Host ""
Write-Host "✅ 完成：https://github.com/$User/$Repo" -ForegroundColor Green
