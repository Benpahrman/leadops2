// Azure Container Apps Module: Environment, Core API, KEDA Worker Swarm, and Scheduled Jobs
@description('Primary location for all compute resources')
param location string

@description('Environment tag (staging or production)')
param environmentName string

@description('Log Analytics Workspace ID')
param logAnalyticsWorkspaceId string

@description('VNet Subnet Resource ID for Container Apps')
param acaSubnetId string

@description('User Assigned Managed Identity Resource ID')
param managedIdentityId string

@description('Key Vault URI')
param keyVaultUri string

@description('Azure Container Registry Login Server')
param acrLoginServer string

@description('Core API Image tag')
param apiImage string

@description('Worker Swarm Image tag')
param workerImage string

@description('Service Bus Namespace Name')
param serviceBusNamespace string

@description('CORS allowed origins')
param corsOrigins string = 'http://localhost:5173,https://omnileadfeeder.tech,https://www.omnileadfeeder.tech,https://leadops.app'

var containerAppEnvName = 'cae-leadops-${environmentName}'
var apiAppName = 'aca-leadops-api-${environmentName}'
var workerAppName = 'aca-leadops-worker-${environmentName}'

// Managed Environment for Container Apps
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: acaSubnetId
      internal: false
    }
  }
}

// 1. Core API Container App (HTTP / WebSocket Ingress)
resource apiApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: apiAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    environmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: split(corsOrigins, ',')
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          allowCredentials: true
        }
      }
      registries: [
        {
          server: acrLoginServer
          identity: managedIdentityId
        }
      ]
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${keyVaultUri}secrets/database-url'
          identity: managedIdentityId
        }
        {
          name: 'storage-connection-string'
          keyVaultUrl: '${keyVaultUri}secrets/storage-connection-string'
          identity: managedIdentityId
        }
        {
          name: 'servicebus-connection-string'
          keyVaultUrl: '${keyVaultUri}secrets/servicebus-connection-string'
          identity: managedIdentityId
        }
        {
          name: 'leadops-api-token'
          keyVaultUrl: '${keyVaultUri}secrets/leadops-api-token'
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'leadops-api'
          image: apiImage
          env: [
            {
              name: 'ENV'
              value: environmentName
            }
            {
              name: 'PORT'
              value: '8000'
            }
            {
              name: 'LEADOPS_CORS_ORIGINS'
              value: corsOrigins
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            {
              name: 'AZURE_SERVICE_BUS_CONNECTION_STRING'
              secretRef: 'servicebus-connection-string'
            }
            {
              name: 'LEADOPS_API_TOKEN'
              secretRef: 'leadops-api-token'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 15
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: environmentName == 'production' ? 10 : 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// 2. KEDA-Driven Autonomous Swarm Worker (Scales to Zero on Queue Depth)
resource workerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: workerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    environmentId: containerAppEnv.id
    configuration: {
      registries: [
        {
          server: acrLoginServer
          identity: managedIdentityId
        }
      ]
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${keyVaultUri}secrets/database-url'
          identity: managedIdentityId
        }
        {
          name: 'storage-connection-string'
          keyVaultUrl: '${keyVaultUri}secrets/storage-connection-string'
          identity: managedIdentityId
        }
        {
          name: 'servicebus-connection-string'
          keyVaultUrl: '${keyVaultUri}secrets/servicebus-connection-string'
          identity: managedIdentityId
        }
        {
          name: 'leadops-api-token'
          keyVaultUrl: '${keyVaultUri}secrets/leadops-api-token'
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'leadops-worker'
          image: workerImage
          env: [
            {
              name: 'ENV'
              value: environmentName
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            {
              name: 'AZURE_SERVICE_BUS_CONNECTION_STRING'
              secretRef: 'servicebus-connection-string'
            }
            {
              name: 'SERVICE_BUS_QUEUE_NAME'
              value: 'leadops-jobs'
            }
            {
              name: 'LEADOPS_API_TOKEN'
              secretRef: 'leadops-api-token'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2.0Gi' // Playwright Chromium memory allotment
          }
        }
      ]
      scale: {
        minReplicas: 0 // Scale to 0 when idle
        maxReplicas: environmentName == 'production' ? 10 : 3
        rules: [
          {
            name: 'queue-scaling'
            custom: {
              type: 'azure-servicebus'
              metadata: {
                queueName: 'leadops-jobs'
                messageCount: '1'
                namespace: serviceBusNamespace
              }
              auth: [
                {
                  secretRef: 'servicebus-connection-string'
                  triggerParameter: 'connection'
                }
              ]
            }
          }
        ]
      }
    }
  }
}

// 3. ACA Scheduled Job: Daily Delivery Runner (Mon-Fri 6:00 AM UTC)
resource dailyDeliveryJob 'Microsoft.App/jobs@2023-05-01' = {
  name: 'job-daily-delivery-${environmentName}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    environmentId: containerAppEnv.id
    configuration: {
      registries: [
        {
          server: acrLoginServer
          identity: managedIdentityId
        }
      ]
      triggerType: 'Schedule'
      scheduleTriggerConfig: {
        cronExpression: '0 6 * * 1-5'
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaTimeout: 1800
    }
    template: {
      containers: [
        {
          name: 'delivery-job'
          image: workerImage
          command: ['python', '-m', 'agents.delivery']
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
        }
      ]
    }
  }
}

// 4. ACA Scheduled Job: Drift & Retainer Monitor (Every 4 hours)
resource driftMonitorJob 'Microsoft.App/jobs@2023-05-01' = {
  name: 'job-drift-monitor-${environmentName}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    environmentId: containerAppEnv.id
    configuration: {
      registries: [
        {
          server: acrLoginServer
          identity: managedIdentityId
        }
      ]
      triggerType: 'Schedule'
      scheduleTriggerConfig: {
        cronExpression: '0 */4 * * *'
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaTimeout: 1200
    }
    template: {
      containers: [
        {
          name: 'drift-monitor'
          image: workerImage
          command: ['python', '-m', 'agents.drift_monitor']
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
        }
      ]
    }
  }
}

output apiFqdn string = apiApp.properties.configuration.ingress.fqdn
output apiId string = apiApp.id
output workerId string = workerApp.id
output environmentId string = containerAppEnv.id
