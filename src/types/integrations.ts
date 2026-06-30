// ─── Enrichment ──────────────────────────────────────────────────────────────

export interface EnrichmentResult {
  firstName?: string
  lastName?: string
  title?: string
  company?: string
  domain?: string
  industry?: string
  companySize?: string
  linkedinUrl?: string
  location?: string
  phone?: string
  raw?: Record<string, unknown>
}

export interface EnrichmentProvider {
  name: string
  enrich(params: { email?: string; domain?: string; linkedinUrl?: string }): Promise<EnrichmentResult>
}

// ─── Signal ──────────────────────────────────────────────────────────────────

export interface IntentSignal {
  type: string    // competitor_engagement | follows_company | hiring | tech_stack | website_visit | manual | webhook
  source: string
  payload: Record<string, unknown>
  weight?: number
  occurredAt?: Date
}

export interface SignalProvider {
  name: string
  fetchSignals(leadId: string, domain?: string): Promise<IntentSignal[]>
}

// ─── Email Channel ───────────────────────────────────────────────────────────

export interface SendEmailParams {
  to: string
  subject: string
  body: string   // HTML or plain text
  replyTo?: string
  threadId?: string
  messageId?: string
}

export interface EmailMessage {
  id: string
  threadId?: string
  from: string
  to: string
  subject: string
  body: string
  receivedAt: Date
}

export interface EmailChannel {
  name: string
  send(params: SendEmailParams): Promise<{ messageId: string; threadId?: string }>
  listReplies(since: Date): Promise<EmailMessage[]>
}

// ─── Social Channel ──────────────────────────────────────────────────────────

export interface SocialChannel {
  name: string
  available: boolean   // false = official API not yet available
  note?: string
  send?(params: { to: string; body: string }): Promise<{ messageId: string }>
}

// ─── CRM Connector ───────────────────────────────────────────────────────────

export interface CrmContact {
  externalId: string
  email?: string
  firstName?: string
  lastName?: string
  company?: string
  title?: string
}

export interface CrmConnector {
  name: string
  upsertContact(lead: {
    email?: string
    firstName?: string
    lastName?: string
    company?: string
    title?: string
  }): Promise<{ externalId: string }>
  logActivity(params: {
    contactExternalId: string
    type: string
    note: string
  }): Promise<void>
}

// ─── LLM Provider ────────────────────────────────────────────────────────────

export interface LlmMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface LlmProvider {
  name: string
  complete(messages: LlmMessage[], opts?: { maxTokens?: number; temperature?: number }): Promise<string>
}
