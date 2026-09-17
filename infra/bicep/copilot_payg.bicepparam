using './copilot_payg.bicep'

param accountName = 'copilot-payg-billing'
param location = 'unitedstates'
param adminEmail = 'admin@olfmailer.com'
param monthlyBudgetAmount = 250
param enableBudgetGuardrail = true
param enableSecurityCopilot = false
param securityCopilotUnits = 1
param tags = {
  Environment: 'Production'
  Workload: 'Microsoft-Copilot-PAYG'
  ManagedBy: 'Bicep'
  CostCenter: 'AI-Operations'
}
