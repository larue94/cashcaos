import type { CrmConnector } from '@/types/integrations'

export class MockCrmAdapter implements CrmConnector {
  name = 'mock'

  async upsertContact(lead: { email?: string; firstName?: string; lastName?: string }) {
    const externalId = `mock-${lead.email || Math.random().toString(36).slice(2)}`
    console.log('[MockCRM] upsertContact', { externalId, ...lead })
    return { externalId }
  }

  async logActivity(params: { contactExternalId: string; type: string; note: string }) {
    console.log('[MockCRM] logActivity', params)
  }
}
