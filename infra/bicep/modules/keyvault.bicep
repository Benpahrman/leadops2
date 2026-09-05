// Azure Key Vault & User-Assigned Managed Identity Module
@description('Primary location for all Key Vault resources')
param location string

@description('Environment tag (staging or production)')
param environmentName string

@description('Database connection string secret')
@secure()
param databaseUrl string

@description('Storage account connection string secret')
@secure()
param storageConnectionString string

@description('Service Bus connection string secret')
@secure()
param serviceBusConnectionString string

@description('PayPal Client ID')
@secure()
param paypalClientId string = ''

@description('PayPal Client Secret')
@secure()
param paypalClientSecret string = ''

@description('PayPal Webhook ID')
@secure()
param paypalWebhookId string = ''

@description('Clerk Secret Key')
@secure()
param clerkSecretKey string = ''

@description('Clerk Publishable Key')
param clerkPublishableKey string = ''

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

@description('LeadOps internal API token')
@secure()
param leadopsApiToken string

var keyVaultName = 'kv-leadops-${environmentName}-${uniqueString(resourceGroup().id)}'
var managedIdentityName = 'id-leadops-${environmentName}'

// User-Assigned Managed Identity
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
}

// Azure Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: take(keyVaultName, 24)
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

// Key Vault Secrets User Role Definition (Built-in: 4633458b-17de-408a-b874-0445c86b69e6)
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource roleAssignmentKeyVault 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentity.id, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Store secrets
resource secretDbUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: databaseUrl
  }
}

resource secretStorageConn 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'storage-connection-string'
  properties: {
    value: storageConnectionString
  }
}

resource secretSbConn 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'servicebus-connection-string'
  properties: {
    value: serviceBusConnectionString
  }
}

resource secretPaypalId 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(paypalClientId)) {
  parent: keyVault
  name: 'paypal-client-id'
  properties: {
    value: paypalClientId
  }
}

resource secretPaypalSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(paypalClientSecret)) {
  parent: keyVault
  name: 'paypal-client-secret'
  properties: {
    value: paypalClientSecret
  }
}

resource secretPaypalWebhook 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(paypalWebhookId)) {
  parent: keyVault
  name: 'paypal-webhook-id'
  properties: {
    value: paypalWebhookId
  }
}

resource secretClerkSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(clerkSecretKey)) {
  parent: keyVault
  name: 'clerk-secret-key'
  properties: {
    value: clerkSecretKey
  }
}

resource secretClerkPub 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(clerkPublishableKey)) {
  parent: keyVault
  name: 'clerk-publishable-key'
  properties: {
    value: clerkPublishableKey
  }
}

resource secretSendpulseId 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(sendpulseClientId)) {
  parent: keyVault
  name: 'sendpulse-client-id'
  properties: {
    value: sendpulseClientId
  }
}

resource secretSendpulseSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(sendpulseClientSecret)) {
  parent: keyVault
  name: 'sendpulse-client-secret'
  properties: {
    value: sendpulseClientSecret
  }
}

resource secretSendpulseApiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(sendpulseApiKey)) {
  parent: keyVault
  name: 'sendpulse-api-key'
  properties: {
    value: sendpulseApiKey
  }
}

resource secretGeminiApiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(geminiApiKey)) {
  parent: keyVault
  name: 'gemini-api-key'
  properties: {
    value: geminiApiKey
  }
}

resource secretGroqApiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(groqApiKey)) {
  parent: keyVault
  name: 'groq-api-key'
  properties: {
    value: groqApiKey
  }
}

resource secretNvidiaApiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(nvidiaApiKey)) {
  parent: keyVault
  name: 'nvidia-api-key'
  properties: {
    value: nvidiaApiKey
  }
}

resource secretLlmKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(llmApiKey)) {
  parent: keyVault
  name: 'llm-api-key'
  properties: {
    value: llmApiKey
  }
}

resource secretApiToken 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'leadops-api-token'
  properties: {
    value: leadopsApiToken
  }
}

output keyVaultId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri
output identityId string = managedIdentity.id
output identityClientId string = managedIdentity.properties.clientId
output identityPrincipalId string = managedIdentity.properties.principalId
