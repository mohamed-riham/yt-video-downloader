@echo off
title YT Video Downloader - Create Shareable ZIP
color 0A
setlocal
cd /d "%~dp0\.."

echo ========================================================
echo       CREATE CLEAN SHAREABLE ZIP FOR YOUR FRIEND
echo ========================================================
echo.
echo [*] Packaging YT Video Downloader without local virtual environments...
echo.

powershell -NoProfile -Command ^
  "$dest = '..\YT-Video-Downloader.zip'; " ^
  "if (Test-Path $dest) { Remove-Item $dest -Force }; " ^
  "$files = Get-ChildItem -Path . -Recurse -File | Where-Object { $_.FullName -notmatch '\\\.venv\\' -and $_.FullName -notmatch '\\__pycache__\\' -and $_.FullName -notmatch '\\\.pytest_cache\\' -and $_.Extension -ne '.pyc' }; " ^
  "Add-Type -AssemblyName System.IO.Compression.FileSystem; " ^
  "$zip = [System.IO.Compression.ZipFile]::Open($dest, 'Create'); " ^
  "foreach ($f in $files) { " ^
  "    $rel = Resolve-Path -Path $f.FullName -Relative; " ^
  "    $rel = $rel.TrimStart('.\'); " ^
  "    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $f.FullName, \"YT-Video-Downloader/$rel\"); " ^
  "}; " ^
  "$zip.Dispose(); " ^
  "$size = [math]::Round((Get-Item $dest).Length / 1KB, 1); " ^
  "Write-Host \"[OK] Successfully created clean zip at: $dest ($size KB)\" -ForegroundColor Green"

echo.
echo ========================================================
echo Done! You can now send 'YT-Video-Downloader.zip' to your friend!
echo ========================================================
pause
