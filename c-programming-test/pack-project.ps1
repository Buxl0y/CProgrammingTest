$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$zip = Join-Path $root 'CProgrammingTest.zip'
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $root '*') -DestinationPath $zip -Force
Write-Host "Created $zip"
