import type { CrmConnector } from '@/types/integrations'

export class HubSpotCrmAdapter implements CrmConnector {
  name = 'hubspot'
  private token: string
  private base = 'https://api.hubapi.com'

  constructor() {
    const t = process.env.HUBSPOT_ACCESS_TOKEN
    if (!t) throw new Error('HUBSPOT_ACCESS_TOKEN is not set')
    this.token = t
  }

  private headers() {
    return {
      'Content-Type': 'application/json',
      Authorization:  `Bearer ${this.token}`,
    }
  }

  async upsertContact(lead: {
    email?: string
    firstName?: string
    lastName?: string
    company?: string
    title?: string
  }): Promise<{ externalId: string }> {
    const properties = {
      email:     lead.email || '',
      firstname: lead.firstName || '',
      lastname:  lead.lastName || '',
      company:   lead.company || '',
      jobtitle:  lead.title || '',
    }

    // Search first
    if (lead.email) {
      const search = await fetch(`${this.base}/crm/v3/objects/contacts/search`, {
        method: 'POST',
        headers: this.headers(),
        body: JSON.stringify({
          filterGroups: [{
            filters: [{ propertyName: 'email', operator: 'EQ', value: lead.email }],
          }],
        }),
      })
      const data = await search.json() as { results: { id: string }[] }
      if (data.results?.length) {
        const id = data.results[0].id
        await fetch(`${this.base}/crm/v3/objects/contacts/${id}`, {
          method: 'PATCH',
          headers: this.headers(),
          body: JSON.stringify({ properties }),
        })
        return { externalId: id }
      }
    }

    // Create
    const res  = await fetch(`${this.base}/crm/v3/objects/contacts`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify({ properties }),
    })
    if (!res.ok) throw new Error(`HubSpot create contact failed: ${res.status}`)
    const obj = await res.json() as { id: string }
    return { externalId: obj.id }
  }

  async logActivity(params: {
    contactExternalId: string
    type: string
    note: string
  }): Promise<void> {
    await fetch(`${this.base}/crm/v3/objects/notes`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify({
        properties: {
          hs_note_body:      `[${params.type}] ${params.note}`,
          hs_timestamp:      Date.now().toString(),
        },
        associations: [{
          to:   { id: params.contactExternalId },
          types: [{ associationCategory: 'HUBSPOT_DEFINED', associationTypeId: 202 }],
        }],
      }),
    })
  }
}
