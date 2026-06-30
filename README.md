# Gojiberry — AI Outbound Sales Platform

A fully-featured, self-hosted outbound sales automation platform with AI-personalized outreach, lead scoring, multichannel sequences, a unified inbox, and analytics.

## Features

- **ICP Builder** — paste your website URL, AI extracts your Ideal Customer Profile
- **Lead Ingestion** — CSV import, manual entry, or webhook
- **Lead Scoring** — transparent 0-100 score (firmographic fit + intent signals), configurable weights, optional LLM rationale
- **Campaigns & Sequences** — multi-step email sequences, Auto or Copilot mode
- **Approval Queue** — review/edit AI-drafted messages before they send
- **Unified Inbox** — all replies in one view, AI reply suggestions
- **Analytics** — funnel charts, daily trend, campaign leaderboard
- **Pluggable integrations** — swap providers via env vars, always has a mock/CSV fallback

## Tech Stack

- **Next.js 14** (App Router) + TypeScript + Tailwind CSS
- **PostgreSQL** via Prisma ORM
- **Redis + BullMQ** for background job queue
- **NextAuth.js** (magic link email + Google OAuth)
- **Anthropic Claude / OpenAI** for AI features

## Quick Start

### 1. Prerequisites

- Node.js 18+
- PostgreSQL
- Redis

### 2. Environment

\`\`\`bash
cp .env.example .env
# Fill in at minimum:
#   DATABASE_URL
#   NEXTAUTH_SECRET  (generate: openssl rand -base64 32)
#   NEXTAUTH_URL
#   REDIS_URL
#   ANTHROPIC_API_KEY  (or OPENAI_API_KEY)
\`\`\`

### 3. Install & Setup

\`\`\`bash
npm install
npx prisma db push      # create tables
npx prisma db seed      # optional: seed demo data
npm run dev             # start Next.js on :3000
npm run worker          # start background worker (separate terminal)
\`\`\`

## Provider Configuration

Set the following env vars to activate real providers (all default to \`mock\`):

| Category    | Env var               | Options                              |
|-------------|----------------------|--------------------------------------|
| Email       | \`EMAIL_PROVIDER\`     | \`mock\` \| \`resend\` \| \`nodemailer\`   |
| Enrichment  | \`ENRICHMENT_PROVIDER\`| \`mock\` \| \`apollo\`                   |
| CRM         | \`CRM_PROVIDER\`       | \`mock\` \| \`hubspot\`                  |
| LLM         | \`LLM_PROVIDER\`       | \`anthropic\` (default) \| \`openai\`    |

See \`.env.example\` for all variables.

## Signal Webhook

POST buying signals from any tool:

\`\`\`bash
POST /api/webhooks/signals
x-webhook-secret: YOUR_WEBHOOK_SIGNAL_SECRET

{
  "email": "lead@company.com",
  "type": "website_visit",
  "source": "your-tool",
  "payload": { "page": "/pricing" },
  "weight": 1.5
}
\`\`\`

## Compliance Notes

- **Never scrapes** people or websites directly — only official APIs or imported data
- Unsubscribe tracking built into the data model (\`Lead.unsubscribed\`)
- GDPR-friendly: delete a lead to cascade-delete all associated data
- All credentials in env vars, never hardcoded

## Social Channels

LinkedIn and Twitter/X are **stubbed** — their official messaging APIs require enterprise partnerships or have severe rate limits. The Settings screen shows the current status.

## License

MIT

---

## Deploy su Railway

1. Fai fork/push di questo repo su GitHub
2. Vai su [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Seleziona questo repo
4. Aggiungi variabile d'ambiente: `ANTHROPIC_API_KEY` = la tua key
5. Deploy automatico — live in 2 minuti

---

## Variabili d'ambiente

| Variabile | Obbligatoria | Descrizione |
|-----------|-------------|-------------|
| `ANTHROPIC_API_KEY` | ✅ Sì | Key da console.anthropic.com |
| `PORT` | Auto | Railway la setta automaticamente |

---

## Features

### 💡 Ideas Feed
- Scraping da HN, TechCrunch, Product Hunt, The Verge
- Analisi AI con virality score (0-100)
- Crosscheck con trending format social
- Voicescript completo da teleprompter in italiano
- One-click → Captions

### 🎬 Video Studio
- Droppa video raw → AI genera titolo, frame text, episode label
- Clip suggestions con timecode e piattaforma target
- Preview frame branded $CCM (Forest style)
- One-click → Captions

### ✍️ Captions Generator
- Input: topic o voicescript
- Output: caption ottimizzate per IG, TikTok, X, LinkedIn, YouTube
- Copy con un click per ogni piattaforma

---

## Stack

- **Backend**: Python + Flask + Gunicorn
- **AI**: Anthropic Claude (claude-sonnet-4-6)
- **Scraping**: BeautifulSoup + RSS feeds
- **Frontend**: Vanilla JS — zero dipendenze
- **Hosting**: Railway.app

---

## Brand

$CCM — Cash & Caos Media  
Forest Green #1A3C2F · White #FFFFFF · Black #060606  
@cash_caos · Est. MMXXVI · Milano / Berlin
