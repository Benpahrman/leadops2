// Azure Service Bus Module for Asynchronous Swarm Coordination
@description('Primary location for all Service Bus resources')
param location string

@description('Environment tag (staging or production)')
param environmentName string

var serviceBusNamespaceName = 'sb-leadops-${environmentName}-${uniqueString(resourceGroup().id)}'

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: serviceBusNamespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    minimumTlsVersion: '1.2'
    zoneRedundant: environmentName == 'production'
  }
}

// Main job queue
resource jobsQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'leadops-jobs'
  properties: {
    lockDuration: 'PT5M'
    maxDeliveryCount: 5
    deadLetteringOnMessageExpiration: true
    requiresDuplicateDetection: true
    duplicateDetectionHistoryTimeWindow: 'PT10M'
    enableBatchedOperations: true
  }
}

// Priority job queue for urgent repairs and webhooks
resource priorityQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'leadops-priority-jobs'
  properties: {
    lockDuration: 'PT5M'
    maxDeliveryCount: 3
    deadLetteringOnMessageExpiration: true
    enableBatchedOperations: true
  }
}

// Dead letter queue
resource deadLetterQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'leadops-deadletter'
  properties: {
    lockDuration: 'PT5M'
    maxDeliveryCount: 10
  }
}

resource authRules 'Microsoft.ServiceBus/namespaces/AuthorizationRules@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'RootManageSharedAccessKey'
  properties: {
    rights: [
      'Listen'
      'Send'
      'Manage'
    ]
  }
}

output namespaceId string = serviceBusNamespace.id
output namespaceName string = serviceBusNamespace.name
output jobsQueueName string = jobsQueue.name
output priorityQueueName string = priorityQueue.name
output deadLetterQueueName string = deadLetterQueue.name
output connectionString string = listKeys(authRules.id, '2022-10-01-preview').primaryConnectionString
