# LeadOps Azure Container App Restart & Health Verification Script
param(
    [string]$ResourceGroupName = "rg-omnileadfeeder-production",
    [string]$ApiAppName = "aca-leadops-api-production",
    [string]$WorkerAppName = "aca-leadops-worker-production",
    [switch]$WorkerOnly,
    [switch]$ApiOnly,
    [switch]$FollowLogs
)

$ErrorActionPreference = "Stop"
if (Test-Path Variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  LeadOps Azure Container App Restart & Verification     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Gray

# 1. Restart API App
if (-not $WorkerOnly) {
    Write-Host "`n[1/3] Restarting API App ($ApiAppName)..." -ForegroundColor Yellow
    try {
        $apiRevision = az containerapp show `
            --name $ApiAppName `
            --resource-group $ResourceGroupName `
            --query "properties.latestRevisionName" -o tsv 2>$null

        if ($apiRevision) {
            Write-Host "Restarting latest active revision: $apiRevision" -ForegroundColor Gray
            az containerapp revision restart `
                --name $ApiAppName `
                --resource-group $ResourceGroupName `
                --revision $apiRevision
            Write-Host "API App revision restarted successfully." -ForegroundColor Green
        } else {
            Write-Host "Could not locate revision for $ApiAppName. Trying app restart..." -ForegroundColor DarkYellow
        }
    } catch {
        Write-Host "Warning restarting API revision: $_" -ForegroundColor Red
    }
}

# 2. Restart Worker App
if (-not $ApiOnly) {
    Write-Host "`n[2/3] Restarting Worker App ($WorkerAppName)..." -ForegroundColor Yellow
    try {
        $workerRevision = az containerapp show `
            --name $WorkerAppName `
            --resource-group $ResourceGroupName `
            --query "properties.latestRevisionName" -o tsv 2>$null

        if ($workerRevision) {
            Write-Host "Restarting latest active revision: $workerRevision" -ForegroundColor Gray
            az containerapp revision restart `
                --name $WorkerAppName `
                --resource-group $ResourceGroupName `
                --revision $workerRevision
            Write-Host "Worker App revision restarted successfully." -ForegroundColor Green
        }
    } catch {
        Write-Host "Warning restarting Worker revision: $_" -ForegroundColor Red
    }
}

# 3. Verify Health Endpoint
Write-Host "`n[3/3] Verifying live API health..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
$fqdn = az containerapp show `
    --name $ApiAppName `
    --resource-group $ResourceGroupName `
    --query "properties.configuration.ingress.fqdn" -o tsv 2>$null

if ($fqdn) {
    $healthUrl = "https://$fqdn/health"
    Write-Host "Checking health at: $healthUrl" -ForegroundColor Gray
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 15
        Write-Host "SUCCESS: Live API is healthy and responding!" -ForegroundColor Green
        $response | Format-Table | Out-String | Write-Host -ForegroundColor Cyan
    } catch {
        Write-Host "Health check failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "Could not retrieve ingress FQDN for $ApiAppName." -ForegroundColor Red
}

if ($FollowLogs) {
    Write-Host "`nStreaming live logs for $ApiAppName (Press Ctrl+C to stop)..." -ForegroundColor Cyan
    az containerapp logs show `
        --name $ApiAppName `
        --resource-group $ResourceGroupName `
        --follow --tail 50
}
