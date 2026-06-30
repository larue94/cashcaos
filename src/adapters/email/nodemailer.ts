import type { EmailChannel, SendEmailParams, EmailMessage } from '@/types/integrations'
import nodemailer from 'nodemailer'

// SMTP adapter (works with Gmail SMTP, SendGrid SMTP, etc.)
export class NodemailerEmailAdapter implements EmailChannel {
  name = 'nodemailer'
  private transporter: nodemailer.Transporter
  private from: string

  constructor() {
    this.from = process.env.EMAIL_FROM_ADDRESS || process.env.EMAIL_SERVER_USER || ''
    this.transporter = nodemailer.createTransport({
      host:   process.env.EMAIL_SERVER_HOST   || 'smtp.gmail.com',
      port:   Number(process.env.EMAIL_SERVER_PORT) || 587,
      secure: false,
      auth: {
        user: process.env.EMAIL_SERVER_USER     || '',
        pass: process.env.EMAIL_SERVER_PASSWORD || '',
      },
    })
  }

  async send(params: SendEmailParams): Promise<{ messageId: string; threadId?: string }> {
    const info = await this.transporter.sendMail({
      from:        this.from,
      to:          params.to,
      subject:     params.subject,
      html:        params.body,
      replyTo:     params.replyTo,
      references:  params.threadId,
      inReplyTo:   params.messageId,
    })
    return { messageId: info.messageId, threadId: params.threadId || info.messageId }
  }

  async listReplies(_since: Date): Promise<EmailMessage[]> {
    return []
  }
}
