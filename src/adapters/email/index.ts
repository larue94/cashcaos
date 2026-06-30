import type { EmailChannel } from '@/types/integrations'
import { MockEmailAdapter }       from './mock'
import { ResendEmailAdapter }     from './resend'
import { NodemailerEmailAdapter } from './nodemailer'

export function getEmailChannel(): EmailChannel {
  switch (process.env.EMAIL_PROVIDER) {
    case 'resend':      return new ResendEmailAdapter()
    case 'nodemailer':  return new NodemailerEmailAdapter()
    case 'smtp':        return new NodemailerEmailAdapter()
    default:            return new MockEmailAdapter()
  }
}

// Social channels — only official APIs, stubs otherwise
export const socialChannels = [
  {
    name:      'LinkedIn',
    available: false,
    note:      'LinkedIn does not offer an official messaging API for outbound sales. Requires LinkedIn Sales Navigator API (enterprise partnership).',
  },
  {
    name:      'Twitter / X',
    available: false,
    note:      'Twitter DM API is available at the Basic tier ($100/mo) but rate limits are severe. Wire up TWITTER_BEARER_TOKEN and implement adapter when ready.',
  },
]
