import type { EnrichmentProvider } from '@/types/integrations'
import { MockEnrichmentAdapter } from './mock'
import { ApolloEnrichmentAdapter } from './apollo'

export function getEnrichmentProvider(): EnrichmentProvider {
  switch (process.env.ENRICHMENT_PROVIDER) {
    case 'apollo': return new ApolloEnrichmentAdapter()
    default:       return new MockEnrichmentAdapter()
  }
}
