# $CCM Media OS
## Cash & Caos Media — AI Content System

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
