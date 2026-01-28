# Proxi Agent Registration Script
# Registers a running agent with Proxi Core
#
# Usage: .\scripts\register-agent.ps1 -AgentName "my-agent" [-CoreUrl "http://localhost:4000"] [-Port 8081]

param(
    [Parameter(Mandatory=$true)]
    [string]$AgentName,                             # Unique agent ID
    
    [string]$CoreUrl = "http://localhost:4000",     # Core server URL
    [string]$DisplayName = "",                      # Display name (defaults to AgentName)
    [string]$Description = "Windows desktop automation agent",
    [string]$Type = "windows",                      # windows, linux, container
    [string]$AgentHost = "host.docker.internal",     # How Core reaches the agent
    [int]$Port = 8081,                              # Agent port
    [string[]]$Capabilities = @("terminal", "screenshot", "desktop", "file_operations"),
    [string]$AgentKey = ""                          # PROXI_AGENT_KEY for secure communication
)

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Proxi Agent Registration" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Set display name
if ([string]::IsNullOrEmpty($DisplayName)) {
    $DisplayName = "Agent: $AgentName"
}

# Check if agent is running
Write-Host "[INFO] Checking agent health at http://localhost:$Port..." -ForegroundColor Blue
try {
    $headers = @{}
    if (-not [string]::IsNullOrEmpty($AgentKey)) {
        $headers["X-Agent-Key"] = $AgentKey
        Write-Host "[INFO] Using Agent API Key for authentication" -ForegroundColor Blue
    }
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:$Port/health" -Headers $headers -UseBasicParsing -TimeoutSec 5
    if ($healthResponse.StatusCode -eq 200) {
        Write-Host "[OK] Agent is running" -ForegroundColor Green
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 401) {
        Write-Host "[ERROR] Agent requires API key. Use -AgentKey parameter." -ForegroundColor Red
        exit 1
    }
    Write-Host "[WARNING] Agent may not be running at localhost:$Port" -ForegroundColor Yellow
    Write-Host "[INFO] Make sure the agent is started before registering" -ForegroundColor Yellow
}

# Check if Core is reachable
Write-Host "[INFO] Checking Core at $CoreUrl..." -ForegroundColor Blue
try {
    $coreResponse = Invoke-WebRequest -Uri "$CoreUrl/api/health" -UseBasicParsing -TimeoutSec 5
    if ($coreResponse.StatusCode -eq 200) {
        Write-Host "[OK] Core is reachable" -ForegroundColor Green
    }
} catch {
    Write-Host "[ERROR] Cannot reach Core at $CoreUrl" -ForegroundColor Red
    exit 1
}

# Build registration payload
$body = @{
    id = $AgentName
    name = $DisplayName
    description = $Description
    workstation_type = $Type
    host = $AgentHost
    port = $Port
    capabilities = $Capabilities
} | ConvertTo-Json

Write-Host ""
Write-Host "[INFO] Registering agent..." -ForegroundColor Blue
Write-Host "  ID:           $AgentName" -ForegroundColor Gray
Write-Host "  Name:         $DisplayName" -ForegroundColor Gray
Write-Host "  Type:         $Type" -ForegroundColor Gray
Write-Host "  Host:Port:    ${AgentHost}:$Port" -ForegroundColor Gray
Write-Host "  Capabilities: $($Capabilities -join ', ')" -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "$CoreUrl/api/workstations" -Method POST -ContentType "application/json" -Body $body
    Write-Host "[SUCCESS] Agent registered!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Agent will appear in the UI dropdown within 30 seconds." -ForegroundColor Cyan
    Write-Host "Or refresh the page to see it immediately." -ForegroundColor Cyan
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 400) {
        Write-Host "[INFO] Agent may already be registered. Updating..." -ForegroundColor Yellow
        # Could implement update here
    } else {
        Write-Host "[ERROR] Registration failed: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "--- Useful Commands ---" -ForegroundColor Yellow
Write-Host "List all agents:    Invoke-RestMethod '$CoreUrl/api/workstations'" -ForegroundColor Gray
Write-Host "Check agent health: Invoke-RestMethod '$CoreUrl/api/workstations/$AgentName/health'" -ForegroundColor Gray
Write-Host "Delete agent:       Invoke-RestMethod '$CoreUrl/api/workstations/$AgentName' -Method DELETE" -ForegroundColor Gray
