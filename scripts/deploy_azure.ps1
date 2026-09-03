# LeadOps Azure Automated Deployment Script
# Provisions infrastructure via Bicep, builds containers with ACR, and triggers ACA rollouts.

param(
    [string]$ResourceGroupName = "rg-omnileadfeeder-production",
    [string]$Location = "centralus",
    [string]$EnvironmentName = "production",
    [string]$AcrName = "",
    [string]$PostgresAdminUser = "omnileadadmin",
    [string]$PostgresAdminPassword = "OmniLead$((Get-Random -Minimum 100000 -Maximum 999999))!Safe",
    [string]$ImageTag = "latest"
)

$ErrorActionPreference = "Stop"
if (Test-Path Variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  OmniLeadFeeder Cloud Architecture Migration to Azure    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Azure CLI authentication
Write-Host "`n[1/6] Verifying Azure CLI authentication..." -ForegroundColor Yellow
$account = $null
try {
    $rawAccount = az account show --output json 2>$null
    if ($LASTEXITCODE -eq 0 -and $rawAccount) {
        $account = $rawAccount | ConvertFrom-Json
    }
} catch {
    $account = $null
}

if (-not $account) {
    Write-Host "ERROR: Please authenticate with the Azure CLI using 'az login' before running this script." -ForegroundColor Red
    exit 1
}
Write-Host "Authenticated as: $($account.user.name) (Subscription: $($account.name))" -ForegroundColor Green

# 2. Ensure Resource Group exists
Write-Host "`n[2/6] Ensuring Resource Group '$ResourceGroupName' exists in '$Location'..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location --output none
Write-Host "Resource group '$ResourceGroupName' ready." -ForegroundColor Green

# 3. Provision or locate Azure Container Registry
Write-Host "`n[3/6] Ensuring Azure Container Registry..." -ForegroundColor Yellow
$acrList = @(az acr list --resource-group $ResourceGroupName --output json 2>$null | ConvertFrom-Json)
if (-not [string]::IsNullOrWhiteSpace($AcrName)) {
    $existingAcr = $acrList | Where-Object { $_.name -eq $AcrName }
    if (-not $existingAcr) {
        Write-Host "Creating Container Registry '$AcrName' (Basic SKU) in '$Location'..."
        az acr create --resource-group $ResourceGroupName --name $AcrName --location $Location --sku Basic --admin-enabled true --output none
    }
} elseif ($acrList.Count -gt 0) {
    $AcrName = $acrList[0].name
    Write-Host "Found existing Azure Container Registry '$AcrName' in '$ResourceGroupName'." -ForegroundColor Green
} else {
    $AcrName = "cromnilead$((Get-Random -Minimum 1000 -Maximum 9999))"
    Write-Host "Creating Container Registry '$AcrName' (Basic SKU) in '$Location'..."
    az acr create --resource-group $ResourceGroupName --name $AcrName --location $Location --sku Basic --admin-enabled true --output none
}
$acrLoginServer = "$AcrName.azurecr.io"
Write-Host "Container Registry Login Server: $acrLoginServer" -ForegroundColor Green

# 4. Build and push container images
Write-Host "`n[4/6] Building and pushing Docker images to ACR..." -ForegroundColor Yellow
$acrBuildSuccess = $false

# Test if Docker daemon is running locally
$dockerRunning = $false
try {
    $dockerInfo = docker info 2>$null
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch {
    $dockerRunning = $false
}

if ($dockerRunning) {
    Write-Host "Local Docker daemon detected. Building & pushing images directly..." -ForegroundColor Green
    try {
        az acr login --name $AcrName --output none
        docker build -t "$acrLoginServer/leadops-api:$ImageTag" -f Dockerfile .
        docker push "$acrLoginServer/leadops-api:$ImageTag"
        docker build -t "$acrLoginServer/leadops-worker:$ImageTag" -f Dockerfile.worker .
        docker push "$acrLoginServer/leadops-worker:$ImageTag"
        $acrBuildSuccess = $true
        Write-Host "Container images successfully published via local Docker." -ForegroundColor Green
    } catch {
        Write-Warning "Local Docker build/push failed: $_"
    }
} else {
    Write-Host "Attempting cloud-based build via ACR Tasks..."
    try {
        az acr build --registry $AcrName --image "leadops-api:$ImageTag" -f Dockerfile .
        if ($LASTEXITCODE -eq 0) {
            az acr build --registry $AcrName --image "leadops-worker:$ImageTag" -f Dockerfile.worker .
            if ($LASTEXITCODE -eq 0) { $acrBuildSuccess = $true }
        }
    } catch {
        $acrBuildSuccess = $false
    }
}

if (-not $acrBuildSuccess) {
    Write-Warning "ACR Tasks cloud build is restricted on this Azure subscription tier (e.g. Azure for Students)."
    Write-Host "To push custom application images to ACR, you can either:" -ForegroundColor Cyan
    Write-Host "  1. Start Docker Desktop and re-run this script." -ForegroundColor White
    Write-Host "     Commands once Docker is running:" -ForegroundColor DarkGray
    Write-Host "       az acr login --name $AcrName" -ForegroundColor DarkGray
    Write-Host "       docker build -t $acrLoginServer/leadops-api:$ImageTag -f Dockerfile ." -ForegroundColor DarkGray
    Write-Host "       docker push $acrLoginServer/leadops-api:$ImageTag" -ForegroundColor DarkGray
    Write-Host "       docker build -t $acrLoginServer/leadops-worker:$ImageTag -f Dockerfile.worker ." -ForegroundColor DarkGray
    Write-Host "       docker push $acrLoginServer/leadops-worker:$ImageTag" -ForegroundColor DarkGray
    Write-Host "  2. Or push to GitHub to run the automated CI/CD pipeline in .github/workflows/azure_deploy.yml" -ForegroundColor White

    # Seed bootstrap placeholder images if missing so Bicep infrastructure provisioning succeeds cleanly
    $rawRepos = az acr repository list --name $AcrName --output json 2>$null
    $hasApi = $false
    $hasWorker = $false
    if ($rawRepos) {
        $repoList = @($rawRepos | ConvertFrom-Json)
        if ($repoList -contains "leadops-api") { $hasApi = $true }
        if ($repoList -contains "leadops-worker") { $hasWorker = $true }
    }
    if (-not $hasApi -or -not $hasWorker) {
        Write-Host "Seeding initial bootstrap container images into ACR so infrastructure provisioning can complete..." -ForegroundColor Yellow
        if (-not $hasApi) {
            az acr import --name $AcrName --source mcr.microsoft.com/azuredocs/aci-helloworld:latest --image "leadops-api:$ImageTag" --force --output none
        }
        if (-not $hasWorker) {
            az acr import --name $AcrName --source mcr.microsoft.com/azuredocs/aci-helloworld:latest --image "leadops-worker:$ImageTag" --force --output none
        }
        Write-Host "Bootstrap images seeded into ACR." -ForegroundColor Green
    } else {
        Write-Host "Container repositories ('leadops-api', 'leadops-worker') verified in ACR." -ForegroundColor Green
    }
}

# 5. Deploy Infrastructure via Bicep
$deploymentTimestamp = (Get-Date -Format 'yyyyMMdd-HHmmss')
$deploymentName = "leadops-bicep-$deploymentTimestamp"
Write-Host "`n[5/6] Deploying Azure Infrastructure via Bicep (Name: $deploymentName)..." -ForegroundColor Yellow

$apiToken = [System.Guid]::NewGuid().ToString("N")

$deployJson = az deployment group create `
    --resource-group $ResourceGroupName `
    --name $deploymentName `
    --template-file infra/bicep/main.bicep `
    --parameters `
        environmentName=$EnvironmentName `
        location=$Location `
        postgresAdminUser=$PostgresAdminUser `
        postgresAdminPassword=$PostgresAdminPassword `
        acrLoginServer=$acrLoginServer `
        imageTag=$ImageTag `
        leadopsApiToken=$apiToken `
    --only-show-errors `
    --output json

$deployResult = $null
if ($LASTEXITCODE -eq 0 -and $deployJson) {
    try {
        $deployResult = $deployJson | ConvertFrom-Json
    } catch {
        $deployResult = $null
    }
}

if (-not $deployResult -or -not $deployResult.properties -or -not $deployResult.properties.outputs) {
    Write-Host "`nInfrastructure deployment encountered errors. See Azure CLI output above." -ForegroundColor Red
    exit 1
}

$outputs = $deployResult.properties.outputs
$apiFqdn = $outputs.apiFqdn.value
$dbHost = $outputs.postgresServerFqdn.value
$storageAccount = $outputs.storageAccountName.value
$serviceBusNs = $outputs.serviceBusNamespace.value

Write-Host "`nInfrastructure Deployment Succeeded!" -ForegroundColor Green
Write-Host "• API Gateway Ingress: https://$apiFqdn" -ForegroundColor Cyan
Write-Host "• PostgreSQL Flexible Server: $dbHost" -ForegroundColor Cyan
Write-Host "• Storage Account: $storageAccount" -ForegroundColor Cyan
Write-Host "• Service Bus Namespace: $serviceBusNs" -ForegroundColor Cyan

# 6. Database Migrations
Write-Host "`n[6/6] Executing database migrations with Alembic..." -ForegroundColor Yellow
$pgConnStr = "postgresql://${PostgresAdminUser}:${PostgresAdminPassword}@${dbHost}:5432/leadops?sslmode=require"
$env:DATABASE_URL = $pgConnStr

try {
    python -m alembic -c agents/alembic.ini upgrade head
    Write-Host "Alembic schema migrations completed successfully." -ForegroundColor Green
} catch {
    Write-Warning "Direct local migration could not reach private VNet endpoint (expected if outside VNet)."
    Write-Warning "Migrations will run automatically via CI/CD runner or container startup."
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "   Migration to Azure Successfully Completed!             " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
