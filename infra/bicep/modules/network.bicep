// Virtual Network and Subnets for LeadOps Azure Infrastructure
@description('Primary location for all network resources')
param location string

@description('Environment tag (staging or production)')
param environmentName string

var vnetName = 'vnet-leadops-${environmentName}'

resource nsgAca 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: 'nsg-leadops-aca-${environmentName}'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowHTTPSInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'AllowHTTPInbound'
        properties: {
          priority: 110
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '80'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource nsgPostgres 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: 'nsg-leadops-postgres-${environmentName}'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowVNetPostgresInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '5432'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'snet-aca'
        properties: {
          addressPrefix: '10.0.0.0/23'
          networkSecurityGroup: {
            id: nsgAca.id
          }
          delegations: [
            {
              name: 'aca-delegation'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'snet-postgres'
        properties: {
          addressPrefix: '10.0.2.0/24'
          networkSecurityGroup: {
            id: nsgPostgres.id
          }
          delegations: [
            {
              name: 'postgres-delegation'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
      {
        name: 'snet-endpoints'
        properties: {
          addressPrefix: '10.0.3.0/24'
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output acaSubnetId string = '${vnet.id}/subnets/snet-aca'
output postgresSubnetId string = '${vnet.id}/subnets/snet-postgres'
output endpointsSubnetId string = '${vnet.id}/subnets/snet-endpoints'
