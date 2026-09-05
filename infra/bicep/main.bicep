// Master Azure Bicep Orchestrator for LeadOps Cloud Architecture
targetScope = 'resourceGroup'

@description('The deployment environment (staging or production)')
@allowed([
  'staging'
  'production'
])
param environmentName string = 'production'

@description('Primary location for all resources')
param location string = resourceGroup().location

@description('PostgreSQL Administrator Login')
param postgresAdminUser string = 'leadopsadmin'

@description('PostgreSQL Administrator Password')
@secure()
param postgresAdminPassword string

@description('PostgreSQL SKU (Standard_B1ms for dev/staging, Standard_D2s_v3 for high-throughput production)')
param postgresSku string = 'Standard_B1ms'

@description('Container Registry Login Server (e.g. crleadops.azurecr.io)')
param acrLoginServer string = 'crleadops.azurecr.io'

@description('Container Image Tag for API and Worker')
param imageTag string = 'latest'

@description('LeadOps internal API token')
@secure()
param leadopsApiToken string

@description('PayPal Client ID')
@secure()
param paypalClientId string = ''

@description('PayPal Client Secret')
@secure()
param paypalClientSecret string = ''

@description('Clerk Secret Key')
@secure()
param clerkSecretKey string = ''

@description('Clerk Publishable Key')
param clerkPublishableKey string = ''

@description('PayPal Webhook ID')
@secure()
param paypalWebhookId string = ''

@description('SendPulse Client ID')
@secure()
param sendpulseClientId string = ''

@description('SendPulse Client Secret')
@secure()
param sendpulseClientSecret string = ''

@description('SendPulse API Key')
@secure()
param sendpulseApiKey string = ''

@description('Gemini API Key')
@secure()
param geminiApiKey string = ''

@description('Groq API Key')
@secure()
param groqApiKey string = ''

@description('NVIDIA API Key')
@secure()
param nvidiaApiKey string = ''

@description('LLM API Key (Gemini or Azure OpenAI)')
@secure()
param llmApiKey string = ''

@description('Frontend repository URL (optional)')
param repositoryUrl string = ''

// 1. Shared Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-leadops-${environmentName}-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: environmentName == 'production' ? 60 : 30
  }
}

// 2. Networking Subsystem (VNet & Subnets)
module network 'modules/network.bicep' = {
  name: 'leadops-network-deployment'
  params: {
    location: location
    environmentName: environmentName
  }
}

// 3. Persistent Relational Store (PostgreSQL Flexible Server)
module database 'modules/database.bicep' = {
  name: 'leadops-database-deployment'
  params: {
    location: location
    environmentName: environmentName
    postgresSubnetId: network.outputs.postgresSubnetId
    adminUsername: postgresAdminUser
    adminPassword: postgresAdminPassword
    skuName: postgresSku
    skuTier: postgresSku == 'Standard_B1ms' ? 'Burstable' : 'GeneralPurpose'
  }
}

// 4. Object & Artifact Storage (Azure Blob Containers)
module storage 'modules/storage.bicep' = {
  name: 'leadops-storage-deployment'
  params: {
    location: location
    environmentName: environmentName
  }
}

// 5. Message Broker (Azure Service Bus)
module serviceBus 'modules/servicebus.bicep' = {
  name: 'leadops-servicebus-deployment'
  params: {
    location: location
    environmentName: environmentName
  }
}

// 6. Security & Secret Management (Azure Key Vault & Managed Identity)
module keyVault 'modules/keyvault.bicep' = {
  name: 'leadops-keyvault-deployment'
  params: {
    location: location
    environmentName: environmentName
    databaseUrl: database.outputs.connectionString
    storageConnectionString: storage.outputs.connectionString
    serviceBusConnectionString: serviceBus.outputs.connectionString
    leadopsApiToken: leadopsApiToken
    paypalClientId: paypalClientId
    paypalClientSecret: paypalClientSecret
    paypalWebhookId: paypalWebhookId
    clerkSecretKey: clerkSecretKey
    clerkPublishableKey: clerkPublishableKey
    sendpulseClientId: sendpulseClientId
    sendpulseClientSecret: sendpulseClientSecret
    sendpulseApiKey: sendpulseApiKey
    geminiApiKey: geminiApiKey
    groqApiKey: groqApiKey
    nvidiaApiKey: nvidiaApiKey
    llmApiKey: llmApiKey
  }
}

// 7. Compute & Autonomous Swarm (Azure Container Apps)
module containerApps 'modules/containerapps.bicep' = {
  name: 'leadops-containerapps-deployment'
  params: {
    location: location
    environmentName: environmentName
    logAnalyticsWorkspaceId: logAnalytics.id
    acaSubnetId: network.outputs.acaSubnetId
    managedIdentityId: keyVault.outputs.identityId
    keyVaultUri: keyVault.outputs.keyVaultUri
    acrLoginServer: acrLoginServer
    apiImage: '${acrLoginServer}/leadops-api:${imageTag}'
    workerImage: '${acrLoginServer}/leadops-worker:${imageTag}'
    serviceBusNamespace: serviceBus.outputs.namespaceName
  }
}

// 7b. AcrPull Role Assignment for User-Assigned Managed Identity on ACR
var acrNameFromLoginServer = split(acrLoginServer, '.')[0]
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acrResource 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = if (!empty(acrLoginServer)) {
  name: acrNameFromLoginServer
}

resource roleAssignmentAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(acrLoginServer)) {
  name: guid(acrResource.id, keyVault.name, acrPullRoleId)
  scope: acrResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: keyVault.outputs.identityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 8. Edge Frontend (Azure Static Web Apps)
module staticWebApp 'modules/staticwebapp.bicep' = {
  name: 'leadops-staticwebapp-deployment'
  params: {
    location: 'centralus'
    environmentName: environmentName
    repositoryUrl: repositoryUrl
  }
}

// Comprehensive Outputs
output apiFqdn string = containerApps.outputs.apiFqdn
output frontendHostname string = staticWebApp.outputs.staticWebAppDefaultHostname
output postgresServerFqdn string = database.outputs.serverFqdn
output storageAccountName string = storage.outputs.storageAccountName
output serviceBusNamespace string = serviceBus.outputs.namespaceName
output keyVaultUri string = keyVault.outputs.keyVaultUri
