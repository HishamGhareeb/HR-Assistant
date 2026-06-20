# Relocates Docker Desktop's WSL2 data disk (images, containers, volumes --
# the actual multi-GB consumer, not the app itself) from C: to D:. Run this
# once, right after installing Docker Desktop, before pulling any images.
# Docker Desktop must be fully quit (not just the window closed) before running.

$ErrorActionPreference = "Stop"
$targetDir = "D:\docker-data"
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

Write-Host "Make sure Docker Desktop is fully quit, then press Enter to continue."
Read-Host | Out-Null

wsl --shutdown

Write-Host "Exporting docker-desktop-data distro to $targetDir\docker-desktop-data.tar ..."
wsl --export docker-desktop-data "$targetDir\docker-desktop-data.tar"

Write-Host "Unregistering the old C: distro..."
wsl --unregister docker-desktop-data

Write-Host "Importing into $targetDir ..."
wsl --import docker-desktop-data "$targetDir" "$targetDir\docker-desktop-data.tar" --version 2

Remove-Item "$targetDir\docker-desktop-data.tar"

Write-Host "Done. Start Docker Desktop again -- its image/volume storage now lives on D:."
