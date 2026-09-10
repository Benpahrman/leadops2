# =====================================================================
# LeadOps Microsoft Entra ID App Provisioning Script for Outlook OAuth
# =====================================================================

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  LeadOps: Provisioning Microsoft OAuth App Registration  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verify Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI ('az') is not installed or not in PATH."
    exit 1
}

# 2. Check and Refresh Azure Login
Write-Host "`n[1/4] Verifying Azure CLI authentication..." -ForegroundColor Yellow
$tenantId = "d0547f8c-7cec-4eb6-b27c-6bb508b6c57c"

$tokenValid = $false
try {
    $test = az account get-access-token --resource "https://graph.microsoft.com" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $tokenValid = $true
    }
} catch {
    $tokenValid = $false
}

if (-not $tokenValid) {
    Write-Host "Azure CLI session expired or requires interactive sign-in." -ForegroundColor Yellow
    Write-Host "Using device-code authentication to bypass local port/firewall issues..." -ForegroundColor Cyan
    az login --use-device-code --tenant $tenantId
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Azure sign-in was not completed."
        exit 1
    }
}

$account = az account show | ConvertFrom-Json
Write-Host "[OK] Authenticated as: $($account.user.name) ($($account.name))" -ForegroundColor Green

# 3. Create or Locate App Registration
Write-Host "`n[2/4] Checking/Creating App Registration ('OmniLeadFeeder-Outlook-Watcher')..." -ForegroundColor Yellow
$appName = "OmniLeadFeeder-Outlook-Watcher"
$redirectUri = "http://localhost:8000/api/admin/oauth/microsoft/callback"

$clientId = $null
$existingJson = az ad app list --display-name $appName --output json 2>$null
if ($existingJson) {
    $existing = $existingJson | ConvertFrom-Json
    if ($existing -and $existing.Count -gt 0) {
        $clientId = $existing[0].appId
        Write-Host "[OK] Found existing App Registration: $appName (Client ID: $clientId)" -ForegroundColor Green
    }
}

if (-not $clientId) {
    Write-Host "Registering new multitenant app '$appName'..." -ForegroundColor Cyan
    $createAppJson = az ad app create --display-name $appName --sign-in-audience "AzureADandPersonalMicrosoftAccount" --web-redirect-uris $redirectUri --output json
    if (-not $createAppJson) {
        Write-Error "Failed to create Azure AD App Registration."
        exit 1
    }
    $app = $createAppJson | ConvertFrom-Json
    $clientId = $app.appId
    Write-Host "[OK] Created new App Registration: $appName (Client ID: $clientId)" -ForegroundColor Green
}

# 4. Generate Client Secret
Write-Host "`n[3/4] Generating fresh Client Secret..." -ForegroundColor Yellow
$secretJson = az ad app credential reset --id $clientId --append --display-name "OmniLeadFeederSecret" --output json
if (-not $secretJson) {
    Write-Error "Failed to generate client secret."
    exit 1
}

$secret = $secretJson | ConvertFrom-Json
$clientSecret = $secret.password
Write-Host "[OK] Client Secret generated successfully." -ForegroundColor Green

# 5. Update .env File
Write-Host "`n[4/4] Writing credentials to .env file..." -ForegroundColor Yellow
$envPath = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envPath)) {
    $envPath = ".env"
}

$envContent = Get-Content $envPath -Raw

function Set-EnvVar($content, $key, $value) {
    $pattern = "(?m)^" + [regex]::Escape($key) + "=.*$"
    if ($content -match $pattern) {
        return ($content -replace $pattern, "$key=`"$value`"")
    } else {
        return ($content.TrimEnd() + "`r`n$key=`"$value`"`r`n")
    }
}

$envContent = Set-EnvVar $envContent "MICROSOFT_CLIENT_ID" $clientId
$envContent = Set-EnvVar $envContent "MICROSOFT_CLIENT_SECRET" $clientSecret
$envContent = Set-EnvVar $envContent "MICROSOFT_TENANT_ID" "common"
$envContent = Set-EnvVar $envContent "MICROSOFT_REDIRECT_URI" $redirectUri

Set-Content -Path $envPath -Value $envContent -Encoding UTF8
Write-Host "[OK] Updated MICROSOFT_CLIENT_ID in .env" -ForegroundColor Green
Write-Host "[OK] Updated MICROSOFT_CLIENT_SECRET in .env" -ForegroundColor Green
Write-Host "[OK] Updated MICROSOFT_TENANT_ID=common in .env" -ForegroundColor Green
Write-Host "[OK] Updated MICROSOFT_REDIRECT_URI in .env" -ForegroundColor Green

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!                                         " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Client ID:     $clientId" -ForegroundColor White
Write-Host "Redirect URI:  $redirectUri" -ForegroundColor White
Write-Host "`nYou can now click 'Connect Microsoft Outlook via OAuth2' in your dashboard:" -ForegroundColor Yellow
Write-Host "http://localhost:8000/admin?tab=inboxes`n" -ForegroundColor Yellow
