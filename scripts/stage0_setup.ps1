# Stage 0: bring up Frappe HR, Onyx, and OpenFGA locally via Docker.
# Run this from the repo root once Docker Desktop is installed and running.
# Each tool keeps its own docker-compose lifecycle; we clone them into
# D:\hr-assistant-external (C: is nearly full) rather than vendoring them
# into this repo. Override with -ExternalDir if you want a different path.
# Docker Desktop's own image/volume storage (the big disk consumer) is NOT
# moved by this script -- see scripts/move_docker_data_to_d.ps1 for that.

param(
    [string]$ExternalDir = "D:\hr-assistant-external"
)

$ErrorActionPreference = "Stop"
$root = git rev-parse --show-toplevel
$external = $ExternalDir
New-Item -ItemType Directory -Force -Path $external | Out-Null

Write-Host "== Frappe HR =="
if (-not (Test-Path (Join-Path $external "hrms"))) {
    git clone https://github.com/frappe/hrms (Join-Path $external "hrms")
}
Write-Host "Next: cd $(Join-Path $external 'hrms/docker'); docker compose up -d"
Write-Host "Then check http://localhost:8000"

Write-Host "== Onyx =="
$onyxInstall = Join-Path $external "onyx_install.sh"
if (-not (Test-Path $onyxInstall)) {
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/onyx-dot-app/onyx/main/deployment/docker_compose/install.sh" -OutFile $onyxInstall
}
Write-Host "Run the Onyx installer with bash (Git Bash/WSL): bash $onyxInstall"

Write-Host "== OpenFGA =="
docker compose -f (Join-Path $root "compose.yaml") up -d
Write-Host "Playground: http://localhost:3000  |  HTTP API: http://localhost:8080"
