// ============================================================================
// Azure Communication Services & Email Communication Services Module
// Custom Domain: olfmailer.com
// ============================================================================

@description('Prefix for resource names')
param prefix string = 'leadops'

@description('Primary custom domain name for outbound email delivery')
param domainName string = 'olfmailer.com'

@description('Geographic location for communication resource data storage')
param dataLocation string = 'United States'

@description('Resource tags')
param tags object = {
  Environment: 'Production'
  Application: 'LeadOps'
  ManagedBy: 'Bicep'
}

// 1. Email Communication Services Resource
resource emailService 'Microsoft.Communication/emailServices@2023-04-01' = {
  name: '${prefix}-email-service'
  location: 'global'
  tags: tags
  properties: {
    dataLocation: dataLocation
  }
}

// 2. Custom Domain Registration under Email Service
resource emailDomain 'Microsoft.Communication/emailServices/domains@2023-04-01' = {
  parent: emailService
  name: domainName
  location: 'global'
  tags: tags
  properties: {
    domainManagement: 'CustomerManaged'
    userEngagementTracking: 'Disabled'
  }
}

// 3. Azure Communication Services Resource (Linked to Custom Domain)
resource communicationService 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: '${prefix}-acs'
  location: 'global'
  tags: tags
  properties: {
    dataLocation: dataLocation
    linkedDomains: [
      emailDomain.id
    ]
  }
}

// Outputs
output communicationServiceId string = communicationService.id
output communicationServiceName string = communicationService.name
output emailServiceId string = emailService.id
output emailServiceName string = emailService.name
output emailDomainId string = emailDomain.id
output primaryConnectionString string = communicationService.listKeys().primaryConnectionString
output verificationRecords object = emailDomain.properties.verificationRecords
