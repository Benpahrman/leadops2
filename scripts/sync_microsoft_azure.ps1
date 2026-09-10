# LeadOps: Synchronize Microsoft Outlook OAuth to Azure Production
# Reads working local .env credentials and pushes them to Azure Entra ID App Registration and Azure Container Apps.

param(
    [string]$ResourceGroupName = "rg-omnileadfeeder-production",
    [string]$ApiAppName = "aca-leadops-api-production",
    [string]$WorkerAppName = "aca-leadops-worker-production",
    [string]$PublicDomain = "https://omnileadfeeder.tech"
)

$ErrorActionPreference = "Stop"
if (Test-Path Variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Sync Microsoft Outlook Inbound Watcher to Azure ACA   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Read Local .env file
$envPath = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envPath)) {
    Write-Error "Local .env file not found at $envPath"
    exit 1
}

Write-Host "`n[1/4] Reading Microsoft credentials from local .env..." -ForegroundColor Yellow
$envContent = Get-Content $envPath

function Get-EnvVal($content, $key) {
    $line = $content | Where-Object { $_ -match "^$key=" } | Select-Object -First 1
    if ($line) {
        $val = ($line -split "=", 2)[1].Trim().Trim('"').Trim("'")
        return $val
    }
    return $null
}

$clientId = Get-EnvVal $envContent "MICROSOFT_CLIENT_ID"
$clientSecret = Get-EnvVal $envContent "MICROSOFT_CLIENT_SECRET"
$refreshToken = Get-EnvVal $envContent "MICROSOFT_REFRESH_TOKEN"
$tenantId = Get-EnvVal $envContent "MICROSOFT_TENANT_ID"
if (-not $tenantId) { $tenantId = "common" }
$watcherEmail = Get-EnvVal $envContent "INBOX_WATCHER_EMAIL"
if (-not $watcherEmail) { $watcherEmail = Get-EnvVal $envContent "OUTLOOK_USER" }
if (-not $watcherEmail) { $watcherEmail = "omnileadfeeder@outlook.com" }

if (-not $clientId -or -not $clientSecret) {
    Write-Error "MICROSOFT_CLIENT_ID or MICROSOFT_CLIENT_SECRET not found in .env."
    exit 1
}

Write-Host "  Client ID: $clientId" -ForegroundColor DarkGray
Write-Host "  Watcher Email: $watcherEmail" -ForegroundColor DarkGray
Write-Host "  Refresh Token Present: $([bool]$refreshToken)" -ForegroundColor DarkGray

# 2. Azure CLI Login Verification
Write-Host "`n[2/4] Verifying Azure CLI authentication..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Azure CLI session expired or requires interactive sign-in." -ForegroundColor Yellow
    Write-Host "Initiating az login..." -ForegroundColor Cyan
    az login --output none
    $account = az account show | ConvertFrom-Json
}
Write-Host "Authenticated as: $($account.user.name) (Subscription: $($account.name))" -ForegroundColor Green

# 3. Ensure Both Redirect URIs exist in Azure Entra ID App Registration
Write-Host "`n[3/4] Updating Azure Entra ID App Registration redirect URIs..." -ForegroundColor Yellow
$localRedirect = "http://localhost:8000/api/admin/oauth/microsoft/callback"
$prodRedirect = "$PublicDomain/api/admin/oauth/microsoft/callback"

try {
    $appJson = az ad app show --id $clientId --output json 2>$null
    if ($appJson) {
        $app = $appJson | ConvertFrom-Json
        $existingUris = @()
        if ($app.web -and $app.web.redirectUris) {
            $existingUris = @($app.web.redirectUris)
        }

        $allUris = @($existingUris + $localRedirect + $prodRedirect) | Select-Object -Unique
        Write-Host "Setting registered Web Redirect URIs:" -ForegroundColor Cyan
        $allUris | ForEach-Object { Write-Host "  - $_" -ForegroundColor DarkGray }

        az ad app update --id $clientId --web-redirect-uris $allUris --output none
        Write-Host "[OK] Azure Entra ID redirect URIs updated successfully." -ForegroundColor Green
    } else {
        Write-Warning "Could not find App Registration for Client ID $clientId to update redirect URIs automatically. Please ensure '$prodRedirect' is added in Azure Portal -> App Registrations -> Authentication."
    }
} catch {
    Write-Warning "Could not update Entra ID redirect URIs automatically: $_"
}

# 4. Inject Environment Variables into Azure Container Apps
Write-Host "`n[4/4] Injecting Microsoft credentials into Azure Container Apps..." -ForegroundColor Yellow

$envVars = @(
    "MICROSOFT_CLIENT_ID=$clientId",
    "MICROSOFT_CLIENT_SECRET=$clientSecret",
    "MICROSOFT_TENANT_ID=$tenantId",
    "MICROSOFT_REDIRECT_URI=$prodRedirect",
    "INBOX_WATCHER_EMAIL=$watcherEmail",
    "OUTLOOK_USER=$watcherEmail"
)

if ($refreshToken) {
    $envVars += "MICROSOFT_REFRESH_TOKEN=$refreshToken"
}

Write-Host "Updating API Container App: $ApiAppName..." -ForegroundColor Cyan
az containerapp update `
    --name $ApiAppName `
    --resource-group $ResourceGroupName `
    --set-env-vars $envVars `
    --output none

Write-Host "[OK] $ApiAppName updated." -ForegroundColor Green

Write-Host "Updating Worker Container App: $WorkerAppName..." -ForegroundColor Cyan
az containerapp update `
    --name $WorkerAppName `
    --resource-group $ResourceGroupName `
    --set-env-vars $envVars `
    --output none

Write-Host "[OK] $WorkerAppName updated." -ForegroundColor Green

# 5. Verification
Write-Host "`nVerifying live status from production endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 8
try {
    $statusResponse = Invoke-RestMethod -Uri "$PublicDomain/api/admin/oauth/microsoft/status" -Method Get -TimeoutSec 15
    if ($statusResponse.ok -and $statusResponse.status.success) {
        Write-Host "==========================================================" -ForegroundColor Green
        Write-Host "SUCCESS: Microsoft Outlook is CONNECTED on $PublicDomain!" -ForegroundColor Green
        Write-Host "  Connected Account: $($statusResponse.status.account_email)" -ForegroundColor Green
        Write-Host "==========================================================" -ForegroundColor Green
    } else {
        Write-Host "Status check output:" -ForegroundColor Yellow
        $statusResponse | ConvertTo-Json -Depth 3 | Write-Host
    }
} catch {
    Write-Host "Could not query status immediately (container revision may still be provisioning): $_" -ForegroundColor DarkGray
}

Write-Host "`nDone!" -ForegroundColor Green
