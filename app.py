from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os
import anthropic
import time
import re
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

# ── ANTHROPIC CLIENT ──
def get_claude():
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)

# ══════════════════════════════════════════
# SCRAPERS
# ══════════════════════════════════════════

def scrape_hackernews():
    stories = []
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    try:
        r = requests.get('https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=20', headers=headers, timeout=8)
        if r.status_code == 200:
            for h in r.json().get('hits', []):
                if h.get('title'):
                    stories.append({
                        'source': 'Hacker News',
                        'title': h.get('title', ''),
                        'url': h.get('url', f"https://news.ycombinator.com/item?id={h.get('objectID')}"),
                        'score': h.get('points', 0),
                        'comments': h.get('num_comments', 0),
                        'time': h.get('created_at_i', int(time.time()))
                    })
            return stories
    except Exception as e:
        print(f"HN error: {e}")
    return stories

def scrape_producthunt():
    stories = []
    try:
        r = requests.get('https://www.producthunt.com/feed', timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.content, 'xml')
        for item in soup.find_all('item')[:10]:
            title = item.find('title')
            link = item.find('link')
            if title and link:
                stories.append({
                    'source': 'Product Hunt',
                    'title': title.text.strip(),
                    'url': link.text.strip() if link.text else '',
                    'score': 0, 'comments': 0, 'time': int(time.time())
                })
    except Exception as e:
        print(f"PH error: {e}")
    return stories

def scrape_techcrunch():
    stories = []
    try:
        r = requests.get('https://techcrunch.com/feed/', timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.content, 'xml')
        for item in soup.find_all('item')[:10]:
            title = item.find('title')
            link = item.find('link')
            if title and link:
                stories.append({
                    'source': 'TechCrunch',
                    'title': title.text.strip(),
                    'url': link.text.strip() if link.text else '',
                    'score': 0, 'comments': 0, 'time': int(time.time())
                })
    except Exception as e:
        print(f"TC error: {e}")
    return stories

def scrape_the_verge():
    stories = []
    try:
        r = requests.get('https://www.theverge.com/rss/index.xml', timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.content, 'xml')
        for item in soup.find_all('entry')[:10]:
            title = item.find('title')
            link = item.find('link')
            if title:
                stories.append({
                    'source': 'The Verge',
                    'title': title.text.strip(),
                    'url': link.get('href', '') if link else '',
                    'score': 0, 'comments': 0, 'time': int(time.time())
                })
    except Exception as e:
        print(f"Verge error: {e}")
    return stories

def analyze_stories_with_claude(stories, claude_client):
    if not claude_client or not stories:
        return stories

    stories_text = "\n".join([
        f"{i+1}. [{s['source']}] {s['title']} (score: {s.get('score', 0)}, comments: {s.get('comments', 0)})"
        for i, s in enumerate(stories[:20])
    ])

    prompt = f"""Sei il content strategist di Cash & Caos ($CCM) — media brand italiano che porta storie tech/startup/finance OVERLOOKED alle masse italiane.

Brand voice $CCM:
- Diretto, senza filtri, zero bullshit
- Sempre con un numero o fatto scomodo
- Linguaggio accessibile, non tecnico
- Audience: italiani 25-35, curiosi, retail investors

Formati ricorrenti:
- "Offcut della Settimana" (venerdì) — startup overlooked
- "$CCM Take" — opinione forte su notizia del giorno
- "Il Numero Scomodo" — un dato che cambia la prospettiva
- "$CCM Scan" — scrolling notizie commentato

Trending formats social in questo momento:
- "La cosa che nessuno ti dice su X"
- "Mentre tutti parlano di X, sta succedendo Y"
- "Questa startup vale $X miliardi e non ne hai mai sentito parlare"
- "Il CEO di X ha detto una cosa che nessuno ha notato"
- "Il numero scomodo della settimana"

Queste sono le storie di oggi:
{stories_text}

Per OGNUNA delle prime 8 storie più rilevanti per $CCM, rispondi in questo JSON format esatto:
{{
  "analyzed_stories": [
    {{
      "index": 1,
      "relevance": "high/medium/low",
      "ccm_angle": "come la racconteresti per il pubblico italiano — 1 frase",
      "best_format": "quale formato $CCM funziona meglio (Offcut/Take/Numero/Scan)",
      "trending_hook": "quale trending format si applica",
      "virality_score": 85,
      "virality_reasons": ["reason1", "reason2"],
      "italian_relevance": "perché interessa agli italiani specificatamente",
      "voicescript": "Script completo da teleprompter in italiano. Hook forte nei primi 3 secondi con numero o dato scomodo. Struttura: hook → dato/fatto → contesto → conclusione provocatoria → CTA (segui @cash_caos). Max 60 secondi letto ad alta voce (~150 parole). Tono: diretto, come parlare a un amico intelligente."
    }}
  ]
}}

Rispondi SOLO con il JSON, nessun testo aggiuntivo."""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group())
            analyzed = analysis.get('analyzed_stories', [])
            result = []
            for item in analyzed:
                idx = item.get('index', 1) - 1
                if 0 <= idx < len(stories):
                    story = stories[idx].copy()
                    story.update({
                        'relevance': item.get('relevance', 'medium'),
                        'ccm_angle': item.get('ccm_angle', ''),
                        'lfg_angle': item.get('ccm_angle', ''),  # backwards compat
                        'best_format': item.get('best_format', '$CCM Take'),
                        'trending_hook': item.get('trending_hook', ''),
                        'virality_score': item.get('virality_score', 50),
                        'virality_reasons': item.get('virality_reasons', []),
                        'italian_relevance': item.get('italian_relevance', ''),
                        'voicescript': item.get('voicescript', ''),
                        'analyzed': True
                    })
                    result.append(story)
            return result
    except Exception as e:
        print(f"Claude analysis error: {e}")
    return stories

@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    claude_client = get_claude()
    all_stories = []
    all_stories.extend(scrape_hackernews())
    all_stories.extend(scrape_producthunt())
    all_stories.extend(scrape_techcrunch())
    all_stories.extend(scrape_the_verge())
    all_stories.sort(key=lambda x: x.get('score', 0), reverse=True)

    if claude_client:
        analyzed = analyze_stories_with_claude(all_stories, claude_client)
        analyzed.sort(key=lambda x: x.get('virality_score', 0), reverse=True)
        return jsonify({'stories': analyzed, 'ai_powered': True, 'count': len(analyzed)})
    else:
        for s in all_stories[:10]:
            s['virality_score'] = s.get('score', 0) % 100
            s['analyzed'] = False
        return jsonify({'stories': all_stories[:10], 'ai_powered': False, 'count': len(all_stories)})

# ══════════════════════════════════════════
# CAPTIONS
# ══════════════════════════════════════════

@app.route('/api/captions', methods=['POST'])
def generate_captions():
    data = request.json
    custom_input = data.get('custom_input', '') or data.get('topic', '')
    claude_client = get_claude()
    if not claude_client:
        return jsonify({'error': 'API key mancante. Aggiungila nelle Impostazioni.'}), 400

    prompt = f"""Sei il social media manager di Cash & Caos ($CCM) — media brand italiano tech/startup/finance.

Brand voice $CCM:
- Diretto, senza filtri, zero bullshit
- Sempre con un numero o fatto scomodo
- Mai spiegazioni lunghe — il video fa il lavoro
- Firma con @cash_caos o #CasheCaos

Contenuto del video:
{custom_input}

Genera caption OTTIMIZZATE per ogni piattaforma. Ogni caption DIVERSA — adattata al DNA di quella piattaforma.

Rispondi in questo JSON format esatto:
{{
  "instagram": {{
    "caption": "Caption IG. Hook forte prima riga. Poi corpo. Poi hashtag separati. 150-300 chars prima hashtag.",
    "hashtags": ["#CasheCaos", "#Tech", "#Finance"],
    "hook_line": "Prima riga sola",
    "char_count": 280
  }},
  "tiktok": {{
    "caption": "Caption TikTok. Max 150 chars. Energica. Emoji. CTA. Hashtag inline.",
    "hashtags": ["#CasheCaos", "#FinTok"],
    "hook_line": "Prima riga",
    "char_count": 140
  }},
  "x": {{
    "caption": "Tweet. Max 280 chars. Frase più provocatoria. Max 2 hashtag.",
    "hashtags": ["#CasheCaos"],
    "hook_line": "Il tweet stesso",
    "char_count": 260
  }},
  "linkedin": {{
    "caption": "Caption LinkedIn. Più lunga. Professionale ma diretto. Hook → contesto → insight → domanda. 300-500 chars.",
    "hashtags": ["#CasheCaos", "#Tech", "#StartupItalia"],
    "hook_line": "Prima riga",
    "char_count": 420
  }},
  "youtube": {{
    "title": "Titolo YouTube SEO-ready. Max 60 chars. Numero se possibile.",
    "description": "Descrizione breve 100-150 chars.",
    "tags": ["cash caos", "tech italia", "startup"],
    "char_count": 60
  }}
}}

Rispondi SOLO con il JSON."""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            captions = json.loads(json_match.group())
            return jsonify({'captions': captions, 'success': True})
        return jsonify({'error': 'Parsing error'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════
# VIDEO STUDIO
# ══════════════════════════════════════════

@app.route('/api/video/process', methods=['POST'])
def process_video():
    data = request.json
    filename = data.get('filename', '')
    topic = data.get('topic', '')
    claude_client = get_claude()
    if not claude_client:
        return jsonify({'error': 'API key mancante'}), 400

    prompt = f"""Sei il video producer di Cash & Caos ($CCM) — media brand italiano tech/startup/finance.

Video: {filename}
Topic: {topic if topic else 'Analizza dal filename'}

Genera in JSON:
{{
  "suggested_title": "Titolo forte stile $CCM — max 60 chars",
  "youtube_title": "Titolo SEO YouTube con numero se possibile",
  "clip_suggestions": [
    {{
      "clip_num": 1,
      "time_range": "0:00-0:45",
      "hook": "Hook suggerito per questo clip",
      "why": "Perché questo momento è forte",
      "platform_primary": "IG/TikTok/X/YouTube",
      "format": "Offcut/Take/Numero/Scan"
    }}
  ],
  "frame_text": "Testo per frame branded $CCM — max 40 chars, ALL CAPS",
  "episode_label": "Es: $CCM Daily · Ep. 001 oppure Offcut #01",
  "thumbnail_hook": "Frase forte thumbnail — max 6 parole"
}}

Rispondi SOLO con il JSON."""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return jsonify({'result': result, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Processing failed'}), 500

# ══════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════

@app.route('/api/settings', methods=['GET'])
def get_settings():
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    return jsonify({
        'anthropic_configured': bool(api_key),
        'anthropic_key_preview': f"sk-ant-...{api_key[-8:]}" if len(api_key) > 8 else '',
    })

@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.json
    if 'anthropic_key' in data and data['anthropic_key']:
        os.environ['ANTHROPIC_API_KEY'] = data['anthropic_key']
    return jsonify({'success': True})

# ══════════════════════════════════════════
# STATIC + HEALTH
# ══════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'brand': '$CCM', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
