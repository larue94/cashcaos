import type { EnrichmentProvider, EnrichmentResult } from '@/types/integrations'

export class MockEnrichmentAdapter implements EnrichmentProvider {
  name = 'mock'

  async enrich(params: { email?: string; domain?: string }): Promise<EnrichmentResult> {
    const domain = params.domain || params.email?.split('@')[1] || 'example.com'
    return {
      company: domain.replace(/\.[^.]+$/, '').replace(/-/g, ' '),
      domain,
      industry: 'Technology',
      companySize: '11-50',
      raw: { source: 'mock', params },
    }
  }
}
