import type { EmailChannel, SendEmailParams, EmailMessage } from '@/types/integrations'
import { randomUUID } from 'crypto'

// Logs to console; useful for local dev without real email credentials
export class MockEmailAdapter implements EmailChannel {
  name = 'mock'

  async send(params: SendEmailParams): Promise<{ messageId: string; threadId?: string }> {
    const messageId = `mock-${randomUUID()}`
    console.log('[MockEmail] SEND', { to: params.to, subject: params.subject, messageId })
    return { messageId, threadId: params.threadId || messageId }
  }

  async listReplies(_since: Date): Promise<EmailMessage[]> {
    return []
  }
}
