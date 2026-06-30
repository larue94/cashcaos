import type { EnrichmentProvider, EnrichmentResult } from '@/types/integrations'

export class ApolloEnrichmentAdapter implements EnrichmentProvider {
  name = 'apollo'
  private apiKey: string

  constructor() {
    const key = process.env.APOLLO_API_KEY
    if (!key) throw new Error('APOLLO_API_KEY is not set')
    this.apiKey = key
  }

  async enrich(params: { email?: string; domain?: string }): Promise<EnrichmentResult> {
    const body: Record<string, string> = {}
    if (params.email)  body.email  = params.email
    if (params.domain) body.domain = params.domain

    const res = await fetch('https://api.apollo.io/v1/people/match', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
        'X-Api-Key': this.apiKey,
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) throw new Error(`Apollo API error: ${res.status}`)
    const data = await res.json() as Record<string, unknown>
    const person = (data.person || {}) as Record<string, unknown>
    const org    = (person.organization || {}) as Record<string, unknown>

    return {
      firstName:   person.first_name as string,
      lastName:    person.last_name as string,
      title:       person.title as string,
      company:     (org.name as string) || (person.organization_name as string),
      domain:      org.primary_domain as string,
      linkedinUrl: person.linkedin_url as string,
      location:    person.city as string,
      industry:    org.industry as string,
      companySize: org.estimated_num_employees as string,
      raw:         data,
    }
  }
}
