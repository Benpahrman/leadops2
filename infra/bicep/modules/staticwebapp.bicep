// Azure Static Web Apps Module for Frontend Portal
@description('Primary location for Static Web App (e.g. centralus, westus2)')
param location string = 'centralus'

@description('Environment tag (staging or production)')
param environmentName string

@description('Repository URL for GitHub / deployment integration')
param repositoryUrl string = ''

@description('Repository branch')
param repositoryBranch string = 'master'

var staticWebAppName = 'swa-leadops-${environmentName}'

resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: environmentName == 'production' ? 'Standard' : 'Free'
    tier: environmentName == 'production' ? 'Standard' : 'Free'
  }
  properties: !empty(repositoryUrl) ? {
    repositoryUrl: repositoryUrl
    branch: repositoryBranch
    buildProperties: {
      appLocation: 'my-clerk-vite-app'
      apiLocation: ''
      appArtifactLocation: 'dist'
    }
  } : {}
}

output staticWebAppId string = staticWebApp.id
output staticWebAppDefaultHostname string = staticWebApp.properties.defaultHostname
