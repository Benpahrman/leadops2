// ==============================================================================
// Microsoft Copilot & Power Platform Pay-As-You-Go (PAYG) Azure Bicep Template
// ==============================================================================
// Enables Microsoft Copilot Studio, Power Platform, and AI Builder pay-as-you-go
// billing linked to an Azure Subscription, with automated budget guardrails
// and admin alert notifications to prevent unexpected consumption spikes.
// ==============================================================================

targetScope = 'resourceGroup'

@description('The name of the Power Platform Pay-As-You-Go billing account in Azure.')
param accountName string = 'copilot-payg-billing-${uniqueString(resourceGroup().id)}'

@description('Azure region for the billing account resource.')
param location string = resourceGroup().location

@description('Admin notification email address for Copilot credit consumption and budget threshold alerts.')
param adminEmail string = 'admin@olfmailer.com'

@description('Monthly spending budget in USD to alert the admin when Copilot consumption scales.')
param monthlyBudgetAmount int = 250

@description('Set to true to deploy a Cost Management Budget and Action Group alert guardrail.')
param enableBudgetGuardrail bool = true

@description('Principal ID (Object ID) of the Microsoft 365 / Copilot Admin user or group to grant Contributor rights.')
param adminPrincipalId string = ''

@description('Set to true if you also want to provision a Microsoft Copilot for Security capacity.')
param enableSecurityCopilot bool = false

@description('Number of Security Compute Units (SCUs) for Copilot for Security if enabled (minimum 1, ~$4/hr).')
@minValue(1)
@maxValue(100)
param securityCopilotUnits int = 1

@description('Tags to organize and attribute Copilot billing in Azure Cost Management.')
param tags object = {
  Environment: 'Production'
  Workload: 'Microsoft-Copilot-PAYG'
  ManagedBy: 'Bicep'
  CostCenter: 'AI-Operations'
}

// ------------------------------------------------------------------------------
// 1. Power Platform & Copilot Studio Pay-As-You-Go Account Resource
// ------------------------------------------------------------------------------
// This resource serves as the Azure-side anchor for the Power Platform & Copilot
// Studio Pay-as-you-go billing plan. Once created, link your environment in the
// Power Platform Admin Center (admin.powerplatform.com -> Licensing -> Pay-as-you-go).
resource powerPlatformAccount 'Microsoft.PowerPlatform/accounts@2020-10-30-preview' = {
  name: accountName
  location: location
  tags: tags
  properties: {
    description: 'Azure Pay-As-You-Go billing plan for Microsoft Copilot Studio and Power Platform credit meters.'
  }
}

// ------------------------------------------------------------------------------
// 2. Action Group for Copilot Budget & Spending Alerts
// ------------------------------------------------------------------------------
resource alertActionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = if (enableBudgetGuardrail && !empty(adminEmail)) {
  name: 'ag-copilot-admin-alerts'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'CopilotAlert'
    enabled: true
    emailReceivers: [
      {
        name: 'CopilotAdmin'
        emailAddress: adminEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

// ------------------------------------------------------------------------------
// 3. Azure Cost Management Budget Guardrail
// ------------------------------------------------------------------------------
// Alerts the Microsoft / Azure admin at 50%, 80%, and 100% of the monthly budget.
resource copilotMonthlyBudget 'Microsoft.Consumption/budgets@2021-10-01' = if (enableBudgetGuardrail && !empty(adminEmail)) {
  name: 'budget-copilot-credits-monthly'
  properties: {
    category: 'Cost'
    amount: monthlyBudgetAmount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: utcNow('yyyy-MM-01T00:00:00Z')
    }
    notifications: {
      NotificationThreshold50: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 50
        contactEmails: [
          adminEmail
        ]
        contactGroups: [
          alertActionGroup.id
        ]
        thresholdType: 'Actual'
      }
      NotificationThreshold80: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 80
        contactEmails: [
          adminEmail
        ]
        contactGroups: [
          alertActionGroup.id
        ]
        thresholdType: 'Actual'
      }
      NotificationThreshold100: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        contactEmails: [
          adminEmail
        ]
        contactGroups: [
          alertActionGroup.id
        ]
        thresholdType: 'Actual'
      }
    }
  }
  dependsOn: [
    powerPlatformAccount
  ]
}

// ------------------------------------------------------------------------------
// 4. (Optional) RBAC Role Assignment: Grant Contributor to Microsoft Admin
// ------------------------------------------------------------------------------
// Built-in 'Contributor' Role Definition ID in Azure
var contributorRoleId = 'b24988ac-6180-42a0-ab88-20f7382dd24c'

resource adminRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(adminPrincipalId)) {
  name: guid(resourceGroup().id, adminPrincipalId, contributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', contributorRoleId)
    principalId: adminPrincipalId
    principalType: 'User'
  }
}

// ------------------------------------------------------------------------------
// 5. (Optional) Microsoft Copilot for Security Capacity
// ------------------------------------------------------------------------------
resource securityCopilotCapacity 'Microsoft.SecurityCopilot/capacities@2023-12-01-preview' = if (enableSecurityCopilot) {
  name: 'sec-copilot-${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  properties: {
    numberOfUnits: securityCopilotUnits
  }
}

// ------------------------------------------------------------------------------
// Outputs
// ------------------------------------------------------------------------------
@description('The Azure Resource ID of the Power Platform / Copilot Pay-As-You-Go account.')
output powerPlatformAccountId string = powerPlatformAccount.id

@description('The name of the Power Platform account to select in the Power Platform Admin Center.')
output powerPlatformAccountName string = powerPlatformAccount.name

@description('Resource Group containing the Copilot billing anchor.')
output resourceGroupName string = resourceGroup().name

@description('Azure Subscription ID linked to this Copilot billing plan.')
output subscriptionId string = subscription().subscriptionId

@description('Instructions for linking in Power Platform Admin Center.')
output nextSteps string = 'Navigate to https://admin.powerplatform.com -> Licensing -> Pay-as-you-go plans -> New billing plan. Select this Azure Subscription (${subscription().subscriptionId}), Resource Group (${resourceGroup().name}), and link your Copilot environment.'
