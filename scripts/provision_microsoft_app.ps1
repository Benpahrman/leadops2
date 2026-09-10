# =====================================================================
# LeadOps Microsoft Entra ID App Provisioning Script for Outlook OAuth
# =====================================================================
# Creates an Azure AD App Registration configured for Personal & Work Microsoft
# accounts, generates a client secret, configures the redirect URI, and writes
# the credentials directly into .env.

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  LeadOps: Provisioning Microsoft OAuth App Registration  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verify Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI ('az') is not installed or not in PATH. Please install from https://aka.ms/installazurecliwindows."
    exit 1
}

# 2. Verify / Refresh Azure Login
Write-Host "`n[1/4] Checking Azure CLI authentication..." -ForegroundColor Yellow
$account = az account show 2>$null
if (-not $account) {
    Write-Host "Please authenticate your Azure account in the browser..." -ForegroundColor Yellow
    az login --tenant "d0547f8c-7cec-4eb6-b27c-6bb508b6c57c" --scope "https://graph.microsoft.com/.default"
    $account = az account show | ConvertFrom-Json
} else {
    $account = $account | ConvertFrom-Json
}

Write-Host "✓ Authenticated as: $($account.user.name) (Subscription: $($account.name))" -ForegroundColor Green

# 3. Create Azure AD App Registration (multitenant + personal Microsoft accounts)
Write-Host "`n[2/4] Creating Azure AD App Registration ('OmniLeadFeeder-Outlook-Watcher')..." -ForegroundColor Yellow
$appName = "OmniLeadFeeder-Outlook-Watcher"
$redirectUri = "http://localhost:8000/api/admin/oauth/microsoft/callback"

$createAppJson = az ad app create `
    --display-name $appName `
    --sign-in-audience "AzureADandPersonalMicrosoftAccount" `
    --web-redirect-uris $redirectUri `
    --output json

if (-not $createAppJson) {
    Write-Error "Failed to create Azure AD App Registration."
    exit 1
}

$app = $createAppJson | ConvertFrom-Json
$clientId = $app.appId
Write-Host "✓ Created App Registration: $appName" -ForegroundColor Green
Write-Host "✓ Application (Client) ID: $clientId" -ForegroundColor Green

# 4. Generate Client Secret
Write-Host "`n[3/4] Generating Client Secret..." -ForegroundColor Yellow
$secretJson = az ad app credential reset `
    --id $clientId `
    --append `
    --display-name "OmniLeadFeederSecret" `
    --output json

$secret = $secretJson | ConvertFrom-Json
$clientSecret = $secret.password
Write-Host "✓ Generated Client Secret successfully." -ForegroundColor Green

# 5. Update .env File
Write-Host "`n[4/4] Updating .env file..." -ForegroundColor Yellow
$envPath = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envPath)) {
    $envPath = ".env"
}

$envContent = Get-Content $envPath -Raw

# Helper to update or append key
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
Write-Host "✓ Credentials successfully written to .env!" -ForegroundColor Green

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  PROVISIONING COMPLETE!                                  " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Client ID:     $clientId" -ForegroundColor White
Write-Host "Tenant ID:     common" -ForegroundColor White
Write-Host "Redirect URI:  $redirectUri" -ForegroundColor White
Write-Host "`nNext Step: Go to http://localhost:8000/admin?tab=inboxes" -ForegroundColor Yellow
Write-Host "and click 'Connect Microsoft Outlook via OAuth2' to authorize omnileadfeeder@outlook.com!`n" -ForegroundColor Yellow
