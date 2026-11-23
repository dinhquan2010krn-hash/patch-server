# Tao file zip de upload qua trinh duyet (PythonAnywhere / host khong co Git).
# Loai tru DB va cac file patch da upload trong instance.
$root = Split-Path -Parent $PSScriptRoot
$zip = Join-Path $root "patch_server_upload.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }

$temp = Join-Path $env:TEMP ("patchsrv_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null

Get-ChildItem -Path $root -Force | ForEach-Object {
    if ($_.Name -in @('instance', '.git', '__pycache__', 'patch_server_upload.zip')) { return }
    Copy-Item $_.FullName -Destination $temp -Recurse -Force
}
New-Item -ItemType Directory -Path (Join-Path $temp 'instance\patches') -Force | Out-Null
Set-Content -Path (Join-Path $temp 'instance\patches\.gitkeep') -Value ''

Compress-Archive -Path (Join-Path $temp '*') -DestinationPath $zip -CompressionLevel Optimal
Remove-Item $temp -Recurse -Force

"Created: $zip"
"Size: $([math]::Round((Get-Item $zip).Length / 1KB, 1)) KB"
