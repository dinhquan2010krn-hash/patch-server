# Tao zip DEPLOY DAY DU: code + DB + 20 file patch da import.
# Dung file nay khi upload len PythonAnywhere de co san patch.
$root = Split-Path -Parent $PSScriptRoot
$zip = Join-Path $root "patch_server_full.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }

$temp = Join-Path $env:TEMP ("patchsrvfull_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null

Get-ChildItem -Path $root -Force | ForEach-Object {
    if ($_.Name -in @('.git', '__pycache__', 'patch_server_upload.zip', 'patch_server_full.zip')) { return }
    Copy-Item $_.FullName -Destination $temp -Recurse -Force
}

Compress-Archive -Path (Join-Path $temp '*') -DestinationPath $zip -CompressionLevel Optimal
Remove-Item $temp -Recurse -Force

"Created: $zip"
"Size: $([math]::Round((Get-Item $zip).Length / 1MB, 2)) MB"
