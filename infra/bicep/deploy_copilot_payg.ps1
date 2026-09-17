<#
.SYNOPSIS
    Deploys Azure Bicep Infrastructure for Microsoft Copilot Studio / Power Platform Pay-As-You-Go Billing.

.DESCRIPTION
    1. Registers the 'Microsoft.PowerPlatform' resource provider on your Azure subscription.
    2. Creates the target Resource Group (default: 'rg-copilot-payg').
    3. Deploys the Bicep template (copilot_payg.bicep) to establish the Azure billing account and budget guardrails.
    4. Outputs the exact settings to link in the Power Platform Admin Center.

.EXAMPLE
    .\deploy_copilot_payg.ps1 -SubscriptionId "your-sub-id" -AdminEmail "admin@olfmailer.com" -MonthlyBudget 250
#>

param (
    [string]$ResourceGroupName = "rg-copilot-payg",
    [string]$Location = "eastus",
    [string]$AccountName = "copilot-payg-billing",
    [string]$AdminEmail = "admin@olfmailer.com",
    [int]$MonthlyBudget = 250,
    [string]$SubscriptionId = ""
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host " 🚀 Deploying Microsoft Copilot Pay-As-You-Go Azure Billing Setup" -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan

# 1. Set Subscription if provided
if ($SubscriptionId) {
    Write-Host "📌 Setting Azure subscription: $SubscriptionId" -ForegroundColor Yellow
    az account set --subscription $SubscriptionId
}

$CurrentSub = (az account show --query "{name:name, id:id}" -o json | ConvertFrom-Json)
Write-Host "✅ Active Azure Subscription: $($CurrentSub.name) ($($CurrentSub.id))" -ForegroundColor Green

# 2. Register Microsoft.PowerPlatform resource provider (required for PAYG Copilot credits)
Write-Host "🔧 Registering resource provider 'Microsoft.PowerPlatform'..." -ForegroundColor Yellow
az provider register --namespace "Microsoft.PowerPlatform" --wait

# 3. Create Resource Group if not existing
Write-Host "📁 Ensuring Resource Group '$ResourceGroupName' exists in $Location..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location -o table

# 4. Deploy Bicep template
$BicepFile = Join-Path $PSScriptRoot "copilot_payg.bicep"
Write-Host "📦 Deploying Bicep template ($BicepFile)..." -ForegroundColor Yellow

$DeployResult = az deployment group create `
    --resource-group $ResourceGroupName `
    --template-file $BicepFile `
    --parameters accountName=$AccountName `
                 adminEmail=$AdminEmail `
                 monthlyBudgetAmount=$MonthlyBudget `
    --query "properties.outputs" -o json | ConvertFrom-Json

Write-Host "`n🎉 Bicep Deployment Succeeded!" -ForegroundColor Green
Write-Host "--------------------------------------------------------------------------"
Write-Host "Power Platform Account ID   : $($DeployResult.powerPlatformAccountId.value)" -ForegroundColor White
Write-Host "Power Platform Account Name : $($DeployResult.powerPlatformAccountName.value)" -ForegroundColor White
Write-Host "Resource Group              : $($DeployResult.resourceGroupName.value)" -ForegroundColor White
Write-Host "Monthly Budget Alert Cap    : `$$MonthlyBudget USD" -ForegroundColor White
Write-Host "Admin Alert Email           : $AdminEmail" -ForegroundColor White
Write-Host "--------------------------------------------------------------------------"

Write-Host "`n👉 NEXT STEPS FOR MICROSOFT / POWER PLATFORM ADMIN:" -ForegroundColor Cyan
Write-Host "1. Open the Power Platform Admin Center: https://admin.powerplatform.com" -ForegroundColor White
Write-Host "2. In the left navigation, select 'Licensing' -> 'Pay-as-you-go plans'." -ForegroundColor White
Write-Host "3. Click '+ New billing plan' (or select an existing plan)." -ForegroundColor White
Write-Host "4. Select Azure Subscription: '$($CurrentSub.name)' ($($CurrentSub.id))" -ForegroundColor White
Write-Host "5. Select Resource Group    : '$ResourceGroupName'" -ForegroundColor White
Write-Host "6. Link your Copilot Studio Environment(s)." -ForegroundColor White
Write-Host "`nAll excess Copilot messages and AI Builder credits will now be metered directly to your Azure bill!" -ForegroundColor Green
