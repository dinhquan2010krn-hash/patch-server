# Chay sau khi da cai Git: https://git-scm.com/download/win
# Cach dung:
#   .\push_to_github.ps1 -RepoUrl "https://github.com/<USERNAME>/<REPO>.git"
param([Parameter(Mandatory=$true)][string]$RepoUrl)

Set-Location $PSScriptRoot
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Error "Git chua duoc cai. Tai tai: https://git-scm.com/download/win"
  exit 1
}

if (-not (Test-Path .git)) { git init }
git add .
git -c user.name="PatchServer" -c user.email="patchserver@local" commit -m "Patch server"
git remote remove origin 2>$null
git remote add origin $RepoUrl
git branch -M main
git push -u origin main
Write-Host "Da push. Vao Render de tao Web Service tu repo nay."
