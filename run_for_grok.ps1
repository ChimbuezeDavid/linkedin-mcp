# Launch LinkedIn MCP Server + Cloudflare Tunnel for Grok.com
$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Starting LinkedIn MCP Server for Grok.com" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Clean up any previous server on port 8765
$existing = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue
if ($existing) {
    Stop-Process -Id $existing.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# 1. Start the LinkedIn MCP server on Port 8765 using Streamable HTTP
Write-Host "`n[1/2] Starting LinkedIn MCP Server (Streamable HTTP on port 8765)..." -ForegroundColor Yellow
$serverProcess = Start-Process -FilePath "uv" -ArgumentList "run", "linkedin-mcp", "--transport", "streamable-http", "--port", "8765" -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 3

# 2. Launch Cloudflare Tunnel
$cloudflaredPath = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
if (-not (Test-Path $cloudflaredPath)) {
    $cloudflaredPath = "cloudflared"
}

Write-Host "[2/2] Launching Cloudflare Tunnel..." -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "IMPORTANT: In Grok.com/connectors, enter the URL with /mcp at the end!" -ForegroundColor Magenta
Write-Host "Example: https://<name>.trycloudflare.com/mcp" -ForegroundColor Green
Write-Host "==================================================`n" -ForegroundColor Cyan

try {
    & $cloudflaredPath tunnel --url http://localhost:8765
}
finally {
    Write-Host "`nStopping LinkedIn MCP Server..." -ForegroundColor Red
    Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
}
