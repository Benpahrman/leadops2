// Azure Database for PostgreSQL Flexible Server Module
@description('Primary location for all database resources')
param location string

@description('Environment tag (staging or production)')
param environmentName string

@description('VNet Subnet Resource ID for PostgreSQL delegation')
param postgresSubnetId string

@description('Administrator login name')
param adminUsername string = 'leadopsadmin'

@description('Administrator login password')
@secure()
param adminPassword string

@description('Compute SKU name')
param skuName string = 'Standard_B1ms'

@description('Compute tier')
@allowed([
  'Burstable'
  'GeneralPurpose'
  'MemoryOptimized'
])
param skuTier string = 'Burstable'

@description('Storage size in GB')
param storageSizeGB int = 32

var serverName = 'psql-leadops-${environmentName}-${uniqueString(resourceGroup().id)}'
var dbName = 'leadops'
var privateDnsZoneName = '${serverName}.private.postgres.database.azure.com'
var vnetId = split(postgresSubnetId, '/subnets/')[0]

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: privateDnsZoneName
  location: 'global'
}

resource privateDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZone
  name: 'link-${uniqueString(resourceGroup().id)}'
  location: 'global'
  properties: {
    virtualNetwork: {
      id: vnetId
    }
    registrationEnabled: false
  }
}

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: serverName
  location: location
  sku: {
    name: skuName
    tier: skuTier
  }
  dependsOn: [
    privateDnsZoneLink
  ]
  properties: {
    version: '15'
    administratorLogin: adminUsername
    administratorLoginPassword: adminPassword
    network: {
      delegatedSubnetResourceId: postgresSubnetId
      privateDnsZoneArmResourceId: privateDnsZone.id
    }
    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: environmentName == 'production' ? 30 : 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: (environmentName == 'production' && skuTier != 'Burstable') ? 'ZoneRedundant' : 'Disabled'
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: dbName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource configSsl 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  parent: postgresServer
  name: 'require_secure_transport'
  properties: {
    value: 'on'
    source: 'user-override'
  }
}

output serverId string = postgresServer.id
output serverFqdn string = postgresServer.properties.fullyQualifiedDomainName
output databaseName string = dbName
output adminUsername string = adminUsername
output connectionString string = 'postgresql://${adminUsername}:${adminPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/${dbName}?sslmode=require'
