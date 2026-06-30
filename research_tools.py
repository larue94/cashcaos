"""
$CCM Launch OS — Live Research Tools
Pulls real market data from:
  - Jina AI  (free, no key — semantic web search + URL reader)
  - Tavily   (free tier 1000/mo — AI search for agents)
  - Google Trends (free, pytrends)
  - Reddit   (free public JSON API)
  - G2 / Capterra (web scraping)
  - YouTube  (scrape or API key)
  - LinkedIn (via Jina/Google search)
"""

import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


# ──────────────────────────────────────────────
# JINA AI  (100% free, no API key)
# Closest open-source-spirit alternative to Exa
# ──────────────────────────────────────────────

def jina_search(query: str, num_results: int = 5) -> dict:
    """
    Semantic web search via Jina AI s.jina.ai — free, no key needed.
    Returns full page content, not just snippets. Great for LinkedIn posts.
    """
    try:
        url = f"https://s.jina.ai/{quote_plus(query)}"
        r = requests.get(url, headers={**HEADERS, 'Accept': 'application/json',
                                        'X-Return-Format': 'json'}, timeout=20)
        if r.status_code == 200:
            try:
                data = r.json()
                results = []
                for item in (data.get('data') or data.get('results') or [])[:num_results]:
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'content': item.get('content', item.get('description', ''))[:600],
                    })
                return {'query': query, 'results': results, 'source': 'Jina AI s.jina.ai'}
            except Exception:
                # Jina also returns markdown — parse it
                lines = r.text.split('\n')
                results = []
                current = {}
                for line in lines:
                    if line.startswith('Title:'):
                        if current:
                            results.append(current)
                        current = {'title': line.replace('Title:', '').strip()}
                    elif line.startswith('URL:'):
                        current['url'] = line.replace('URL:', '').strip()
                    elif line.startswith('Content:') or (current and 'title' in current and 'content' not in current):
                        current['content'] = line[:600]
                if current:
                    results.append(current)
                return {'query': query, 'results': results[:num_results], 'source': 'Jina AI s.jina.ai'}
        return {'error': f'HTTP {r.status_code}', 'query': query}
    except Exception as e:
        return {'error': str(e), 'query': query}


def jina_read_url(url: str) -> dict:
    """
    Read any URL and get clean markdown content via Jina r.jina.ai — free, no key.
    Use this to read specific LinkedIn posts, G2 pages, Reddit threads, etc.
    """
    try:
        read_url = f"https://r.jina.ai/{url}"
        r = requests.get(read_url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return {'url': url, 'content': r.text[:3000], 'source': 'Jina AI r.jina.ai'}
        return {'error': f'HTTP {r.status_code}', 'url': url}
    except Exception as e:
        return {'error': str(e), 'url': url}


def jina_linkedin_search(topic: str) -> dict:
    """Search LinkedIn posts via Jina AI — free semantic search."""
    results = []
    queries = [
        f"site:linkedin.com {topic} problem frustrated",
        f"site:linkedin.com {topic} finally solution",
        f"site:linkedin.com {topic} announcing launched",
    ]
    for q in queries:
        r = jina_search(q, num_results=4)
        for item in r.get('results', []):
            if item.get('content') or item.get('title'):
                results.append(item)
        time.sleep(0.5)
    return {'topic': topic, 'posts': results, 'source': 'Jina AI → LinkedIn'}


# ──────────────────────────────────────────────
# TAVILY  (free tier: 1000 searches/month)
# Best structured AI search for agents
# Sign up free at tavily.com
# ──────────────────────────────────────────────

def tavily_search(query: str, api_key: str, search_depth: str = 'basic',
                  include_domains: list = None, max_results: int = 5) -> dict:
    """
    Tavily AI search — structured results with full content extraction.
    Free tier: 1000 searches/month at tavily.com
    search_depth: 'basic' (fast) or 'advanced' (deeper, uses more credits)
    """
    try:
        payload = {
            'api_key': api_key,
            'query': query,
            'search_depth': search_depth,
            'max_results': max_results,
            'include_answer': True,
            'include_raw_content': False,
        }
        if include_domains:
            payload['include_domains'] = include_domains

        r = requests.post('https://api.tavily.com/search',
                          json=payload, timeout=20)
        if r.status_code == 200:
            data = r.json()
            return {
                'query': query,
                'answer': data.get('answer', ''),
                'results': [
                    {
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'content': item.get('content', '')[:600],
                        'score': item.get('score', 0),
                    }
                    for item in data.get('results', [])
                ],
                'source': 'Tavily',
            }
        return {'error': f'HTTP {r.status_code}: {r.text[:200]}', 'query': query}
    except Exception as e:
        return {'error': str(e), 'query': query}


def tavily_research_pack(topic: str, competitors: list, api_key: str) -> dict:
    """Run a full Tavily research sweep across LinkedIn, Reddit, G2, and industry news."""
    results = {}

    results['linkedin'] = tavily_search(
        f"{topic} professionals frustrated problems LinkedIn",
        api_key, include_domains=['linkedin.com'], max_results=5
    )
    time.sleep(0.3)

    results['reddit'] = tavily_search(
        f"{topic} reddit complaints hate worst alternative",
        api_key, include_domains=['reddit.com'], max_results=5
    )
    time.sleep(0.3)

    results['industry'] = tavily_search(
        f"{topic} market trends 2024 2025 growth problems",
        api_key, max_results=5
    )
    time.sleep(0.3)

    if competitors:
        results['competitor_reviews'] = tavily_search(
            f"{' OR '.join(competitors[:2])} reviews problems users hate",
            api_key, include_domains=['g2.com', 'capterra.com', 'trustpilot.com'], max_results=5
        )

    return results


# ──────────────────────────────────────────────
# GOOGLE TRENDS
# ──────────────────────────────────────────────

def get_google_trends(keywords: list[str]) -> dict:
    """Pull interest over time and related queries from Google Trends."""
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl='en-US', tz=0, timeout=(10, 25))
        kw_list = keywords[:5]
        pt.build_payload(kw_list, timeframe='today 12-m', geo='')
        interest = pt.interest_over_time()
        related = {}
        for kw in kw_list:
            try:
                rq = pt.related_queries()
                top = rq.get(kw, {}).get('top')
                if top is not None and not top.empty:
                    related[kw] = top.head(10).to_dict('records')
            except Exception:
                pass
        trending_now = pt.trending_searches(pn='united_states')
        return {
            "keywords": kw_list,
            "interest_summary": {
                col: {
                    "mean": float(interest[col].mean()),
                    "recent": float(interest[col].tail(4).mean()),
                    "trend": "rising" if interest[col].tail(4).mean() > interest[col].mean() else "declining"
                }
                for col in interest.columns if col != 'isPartial'
            } if not interest.empty else {},
            "related_queries": related,
            "top_trending_us": trending_now.head(10)[0].tolist() if not trending_now.empty else [],
        }
    except Exception as e:
        return {"error": str(e), "note": "Install pytrends: pip install pytrends"}


# ──────────────────────────────────────────────
# REDDIT
# ──────────────────────────────────────────────

def get_reddit_posts(topic: str, limit: int = 20) -> dict:
    """Search Reddit for posts and comments about a topic using public JSON API."""
    try:
        results = []
        # Search across all subreddits
        url = f"https://www.reddit.com/search.json?q={quote_plus(topic)}&sort=relevance&t=year&limit={limit}"
        r = requests.get(url, headers={**HEADERS, 'Accept': 'application/json'}, timeout=10)
        data = r.json()
        posts = data.get('data', {}).get('children', [])

        for post in posts:
            p = post.get('data', {})
            results.append({
                'title': p.get('title', ''),
                'subreddit': p.get('subreddit', ''),
                'score': p.get('score', 0),
                'num_comments': p.get('num_comments', 0),
                'selftext': p.get('selftext', '')[:300],
                'url': f"https://reddit.com{p.get('permalink', '')}",
            })

        # Also search for complaints specifically
        complaint_results = []
        complaint_url = f"https://www.reddit.com/search.json?q={quote_plus(topic + ' problem hate frustrating worst')}&sort=relevance&t=year&limit=10"
        r2 = requests.get(complaint_url, headers={**HEADERS, 'Accept': 'application/json'}, timeout=10)
        data2 = r2.json()
        for post in data2.get('data', {}).get('children', []):
            p = post.get('data', {})
            complaint_results.append({
                'title': p.get('title', ''),
                'subreddit': p.get('subreddit', ''),
                'score': p.get('score', 0),
                'text': p.get('selftext', '')[:300],
            })

        return {
            "topic": topic,
            "posts": results,
            "complaints": complaint_results,
            "top_subreddits": list(set(p['subreddit'] for p in results if p['subreddit']))[:10],
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# G2 REVIEWS
# ──────────────────────────────────────────────

def scrape_g2_reviews(product_name: str) -> dict:
    """Scrape G2 for competitor reviews and common complaints."""
    try:
        results = []
        search_url = f"https://www.g2.com/search?query={quote_plus(product_name)}"
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')

        # Find product listings
        products = soup.select('[data-testid="product-card"], .product-listing, .js-log-click')[:5]

        # Scrape reviews from G2 search results page
        review_snippets = []
        review_els = soup.select('.review-text, .content, [itemprop="reviewBody"]')
        for el in review_els[:15]:
            text = el.get_text(strip=True)
            if len(text) > 50:
                review_snippets.append(text[:300])

        # Get star ratings overview
        ratings = soup.select('.star-rating, [class*="rating"]')

        # Also try to get "what users like/dislike" sections
        pros = []
        cons = []
        for el in soup.select('[class*="pro"], [class*="like"]')[:10]:
            text = el.get_text(strip=True)
            if len(text) > 20:
                pros.append(text[:200])
        for el in soup.select('[class*="con"], [class*="dislike"]')[:10]:
            text = el.get_text(strip=True)
            if len(text) > 20:
                cons.append(text[:200])

        return {
            "product": product_name,
            "review_snippets": review_snippets,
            "pros": pros,
            "cons": cons,
            "source": search_url,
        }
    except Exception as e:
        return {"error": str(e)}


def scrape_capterra_reviews(product_name: str) -> dict:
    """Scrape Capterra for user reviews and complaints."""
    try:
        search_url = f"https://www.capterra.com/search/#q={quote_plus(product_name)}"
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')

        reviews = []
        pros = []
        cons = []

        for el in soup.select('[class*="review-content"], [class*="review-body"], .review')[:10]:
            text = el.get_text(strip=True)
            if len(text) > 50:
                reviews.append(text[:300])

        for el in soup.select('[class*="pros"], [class*="liked"]')[:8]:
            text = el.get_text(strip=True)
            if len(text) > 20:
                pros.append(text[:200])

        for el in soup.select('[class*="cons"], [class*="disliked"]')[:8]:
            text = el.get_text(strip=True)
            if len(text) > 20:
                cons.append(text[:200])

        return {
            "product": product_name,
            "reviews": reviews,
            "pros": pros,
            "cons": cons,
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# LINKEDIN VIA GOOGLE SEARCH
# ──────────────────────────────────────────────

def search_linkedin_via_google(topic: str) -> dict:
    """
    Search Google for public LinkedIn posts about a topic.
    Uses Google's index of LinkedIn to extract real professional discourse.
    """
    try:
        results = []
        queries = [
            f'site:linkedin.com/posts "{topic}"',
            f'site:linkedin.com "{topic}" problem OR frustrated OR broken OR finally',
            f'site:linkedin.com "{topic}" launched OR announcing OR excited',
        ]

        for query in queries:
            url = f"https://www.google.com/search?q={quote_plus(query)}&num=10&hl=en"
            r = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(r.content, 'html.parser')

            # Extract search result snippets
            for result in soup.select('div.g, div[data-sokoban-feature]')[:8]:
                title_el = result.select_one('h3')
                snippet_el = result.select_one('[data-sncf], .VwiC3b, span.aCOpRe')
                link_el = result.select_one('a[href]')

                title = title_el.get_text(strip=True) if title_el else ''
                snippet = snippet_el.get_text(strip=True) if snippet_el else ''
                link = link_el.get('href', '') if link_el else ''

                if title and 'linkedin' in link.lower() and len(snippet) > 30:
                    results.append({
                        'title': title,
                        'snippet': snippet[:400],
                        'url': link,
                        'query': query,
                    })

            time.sleep(1.5)  # be polite to Google

        return {
            "topic": topic,
            "posts": results,
            "note": "Extracted from Google's index of public LinkedIn posts"
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# YOUTUBE
# ──────────────────────────────────────────────

def scrape_youtube_search(topic: str, api_key: str = None) -> dict:
    """
    Search YouTube for relevant videos. Uses official API if key provided,
    otherwise scrapes public search results.
    """
    try:
        if api_key:
            return _youtube_api(topic, api_key)
        else:
            return _youtube_scrape(topic)
    except Exception as e:
        return {"error": str(e)}


def _youtube_api(topic: str, api_key: str) -> dict:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': topic,
        'type': 'video',
        'order': 'viewCount',
        'maxResults': 10,
        'key': api_key,
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    videos = []
    for item in data.get('items', []):
        s = item.get('snippet', {})
        videos.append({
            'title': s.get('title', ''),
            'description': s.get('description', '')[:200],
            'channel': s.get('channelTitle', ''),
            'published': s.get('publishedAt', ''),
        })
    return {"topic": topic, "videos": videos, "source": "YouTube Data API v3"}


def _youtube_scrape(topic: str) -> dict:
    url = f"https://www.youtube.com/results?search_query={quote_plus(topic)}&sp=CAMSAhAB"  # sorted by view count
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.content, 'html.parser')

    videos = []
    # YouTube renders via JS so we parse initial data
    import re
    match = re.search(r'var ytInitialData = ({.*?});', r.text, re.DOTALL)
    if match:
        try:
            yt_data = json.loads(match.group(1))
            contents = (yt_data.get('contents', {})
                        .get('twoColumnSearchResultsRenderer', {})
                        .get('primaryContents', {})
                        .get('sectionListRenderer', {})
                        .get('contents', []))
            for section in contents:
                items = section.get('itemSectionRenderer', {}).get('contents', [])
                for item in items:
                    vid = item.get('videoRenderer', {})
                    if vid:
                        title = vid.get('title', {}).get('runs', [{}])[0].get('text', '')
                        views = vid.get('viewCountText', {}).get('simpleText', '')
                        desc_runs = vid.get('descriptionSnippet', {}).get('runs', [])
                        desc = ''.join(r.get('text', '') for r in desc_runs)
                        channel = vid.get('ownerText', {}).get('runs', [{}])[0].get('text', '')
                        if title:
                            videos.append({
                                'title': title,
                                'views': views,
                                'description': desc[:200],
                                'channel': channel,
                            })
        except Exception:
            pass

    return {"topic": topic, "videos": videos[:10], "source": "YouTube search"}


# ──────────────────────────────────────────────
# MASTER RESEARCH RUNNER
# ──────────────────────────────────────────────

def run_full_research(product_info: str, competitors: list = None,
                      keywords: list = None, youtube_api_key: str = None,
                      tavily_api_key: str = None) -> dict:
    """
    Run all research tools and return a combined data package.
    Priority: Tavily (if key) → Jina AI (always free) → direct scrapers.
    """
    print("  📡  Running live research...")

    if not keywords:
        words = [w.strip('.,!?') for w in product_info.split() if len(w) > 5]
        keywords = list(set(words[:5]))

    topic = product_info[:100]
    data = {}

    # ── Tavily sweep (if key provided) ───────────
    if tavily_api_key:
        print("  🔍  Tavily AI search (LinkedIn, Reddit, G2)...")
        data['tavily'] = tavily_research_pack(topic, competitors or [], tavily_api_key)
    else:
        data['tavily'] = {'note': 'No Tavily key — using Jina AI + direct scrapers'}

    # ── Jina AI LinkedIn search (always free) ────
    print("  💼  LinkedIn via Jina AI (free)...")
    data['linkedin_jina'] = jina_linkedin_search(topic)

    # ── Jina general search ──────────────────────
    print("  🔎  Jina AI semantic search...")
    data['jina_market'] = jina_search(f"{topic} problems users hate complaints 2024", num_results=5)
    data['jina_viral'] = jina_search(f"{topic} viral launch X twitter announcement", num_results=5)

    # ── Google Trends ────────────────────────────
    print("  📈  Google Trends...")
    data['google_trends'] = get_google_trends(keywords)

    # ── Reddit ───────────────────────────────────
    print("  🔴  Reddit...")
    data['reddit'] = get_reddit_posts(topic)

    # ── G2 / Capterra ────────────────────────────
    if competitors:
        print(f"  ⭐  G2/Capterra for {competitors[0]}...")
        data['g2'] = scrape_g2_reviews(competitors[0])
        data['capterra'] = scrape_capterra_reviews(competitors[0])
    else:
        data['g2'] = {'note': 'Add competitor names for G2/Capterra review scraping'}

    # ── YouTube ──────────────────────────────────
    print("  ▶️  YouTube...")
    data['youtube'] = scrape_youtube_search(topic, youtube_api_key)

    print("  ✅  Live research complete.")
    return data


def format_research_for_claude(data: dict) -> str:
    """Format the raw research data into a clean brief for Claude agents."""
    parts = []

    # Tavily AI search results
    tavily = data.get('tavily', {})
    if tavily and not tavily.get('note') and not tavily.get('error'):
        tav_industry = tavily.get('industry', {})
        if tav_industry.get('answer'):
            parts.append("## TAVILY: MARKET INTELLIGENCE")
            parts.append(tav_industry['answer'][:500])
        tav_li = tavily.get('linkedin', {})
        if tav_li.get('results'):
            parts.append("\nLINKEDIN (via Tavily):")
            for r in tav_li['results'][:4]:
                parts.append(f"- {r.get('title', '')} — {r.get('content', '')[:200]}")
        tav_reddit = tavily.get('reddit', {})
        if tav_reddit.get('results'):
            parts.append("\nREDDIT (via Tavily):")
            for r in tav_reddit['results'][:4]:
                parts.append(f"- {r.get('title', '')} — {r.get('content', '')[:200]}")
        tav_reviews = tavily.get('competitor_reviews', {})
        if tav_reviews.get('results'):
            parts.append("\nCOMPETITOR REVIEWS (G2/Capterra via Tavily):")
            for r in tav_reviews['results'][:4]:
                parts.append(f"- {r.get('title', '')} — {r.get('content', '')[:200]}")

    # Jina AI semantic search
    jina_market = data.get('jina_market', {})
    if jina_market.get('results'):
        parts.append("\n## JINA AI: MARKET SIGNALS")
        for r in jina_market['results'][:4]:
            parts.append(f"- {r.get('title', '')} — {r.get('content', '')[:250]}")

    jina_viral = data.get('jina_viral', {})
    if jina_viral.get('results'):
        parts.append("\n## JINA AI: VIRAL PATTERNS")
        for r in jina_viral['results'][:4]:
            parts.append(f"- {r.get('title', '')} — {r.get('content', '')[:250]}")

    # Jina LinkedIn search
    li_jina = data.get('linkedin_jina', {})
    if li_jina.get('posts'):
        parts.append("\n## LINKEDIN PROFESSIONAL DISCOURSE (Jina AI)")
        for post in li_jina['posts'][:6]:
            parts.append(f"- \"{post.get('title', '')}\"")
            if post.get('content'):
                parts.append(f"  → {post['content'][:200]}")

    # Google Trends
    gt = data.get('google_trends', {})
    if not gt.get('error'):
        parts.append("\n## GOOGLE TRENDS")
        for kw, stats in gt.get('interest_summary', {}).items():
            parts.append(f"- {kw}: {stats.get('trend', '?').upper()} (recent avg: {stats.get('recent', 0):.0f}/100)")
        rq = gt.get('related_queries', {})
        for kw, queries in rq.items():
            if queries:
                top_q = [q.get('query', '') for q in queries[:5]]
                parts.append(f"- Related searches for '{kw}': {', '.join(top_q)}")

    # Reddit
    reddit = data.get('reddit', {})
    if not reddit.get('error') and reddit.get('posts'):
        parts.append("\n## REDDIT SIGNAL")
        parts.append(f"Top subreddits discussing this: {', '.join(reddit.get('top_subreddits', [])[:5])}")
        for post in reddit.get('posts', [])[:5]:
            parts.append(f"- [{post.get('score', 0)}↑] r/{post.get('subreddit', '')} — \"{post.get('title', '')}\"")
        parts.append("\nCOMPLAINTS:")
        for post in reddit.get('complaints', [])[:5]:
            parts.append(f"- [{post.get('score', 0)}↑] \"{post.get('title', '')}\"")
            if post.get('text'):
                parts.append(f"  → {post['text'][:150]}")

    # G2 / Capterra
    g2 = data.get('g2', {})
    if not g2.get('error') and not g2.get('note'):
        parts.append("\n## G2 COMPETITOR REVIEWS")
        for pro in g2.get('pros', [])[:5]:
            parts.append(f"✓ {pro}")
        for con in g2.get('cons', [])[:5]:
            parts.append(f"✗ {con}")
        for snippet in g2.get('review_snippets', [])[:3]:
            parts.append(f"Quote: \"{snippet}\"")

    # YouTube
    yt = data.get('youtube', {})
    if not yt.get('error') and yt.get('videos'):
        parts.append("\n## YOUTUBE VIRAL SIGNALS")
        for vid in yt.get('videos', [])[:6]:
            views = vid.get('views', '')
            parts.append(f"- \"{vid.get('title', '')}\" {('(' + views + ')') if views else ''}")
            if vid.get('description'):
                parts.append(f"  → {vid['description'][:150]}")

    return '\n'.join(parts) if parts else "No live research data available."
