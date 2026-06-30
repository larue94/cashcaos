import type { CrmConnector } from '@/types/integrations'
import { MockCrmAdapter }    from './mock'
import { HubSpotCrmAdapter } from './hubspot'

export function getCrmConnector(): CrmConnector {
  switch (process.env.CRM_PROVIDER) {
    case 'hubspot': return new HubSpotCrmAdapter()
    default:        return new MockCrmAdapter()
  }
}
