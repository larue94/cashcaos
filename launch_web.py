#!/usr/bin/env python3
"""
$CCM Launch OS — Web Platform
21-agent viral launch system with live research + real-time streaming UI
"""

import os
import json
import queue
import threading
from datetime import datetime
from flask import Flask, Response, request, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

try:
    import anthropic
except ImportError:
    os.system("pip install anthropic flask flask-cors python-dotenv pytrends")
    import anthropic

from research_tools import run_full_research, format_research_for_claude

app = Flask(__name__)
CORS(app)
MODEL = "claude-sonnet-4-6"

# ──────────────────────────────────────────────
# AGENT SYSTEM PROMPTS
# ──────────────────────────────────────────────

SYSTEMS = {
    "market": "You are a market research expert. You receive LIVE data from Google Trends, Reddit, YouTube, LinkedIn and G2 reviews. Synthesise it into sharp insights about what the market actually wants, hates, and talks about. Be specific. Quote real language from the data.",
    "reddit": "You are a Reddit research expert. You receive actual Reddit posts and complaints. Extract the raw emotional language, recurring frustrations, and exact phrases people use. This is gold — mirror this language in the launch.",
    "viral": "You are a viral launch analyst. You receive YouTube data showing what content performs. Find patterns in titles, hooks, and positioning that generate views. What works NOW vs what's dead.",
    "linkedin": "You are a LinkedIn professional discourse analyst. You receive real LinkedIn post data. Extract what professionals in this space publicly complain about, celebrate, and share. This is B2B intent signal.",
    "novelty": "You are a novelty extraction specialist. You see the full market picture. Find what is GENUINELY new — what no one else is doing, what the data shows is missing. 'AI-powered' is NOT novel. Be ruthless.",
    "positioning": "You are a positioning strategist behind 30 of the largest X launches. Create BOLD CLAIMS that make products feel inevitable and novel. Think challenger brand. Think counter-positioning. Use the research data to find real market gaps.",
    "hook_writer": "You are a viral hook writer. You've seen the YouTube titles and Reddit posts that perform — use those patterns. Write hooks that stop scroll. Never polite. Never 'excited to announce.'",
    "hook_critic": "You are a brutal hook critic. Destroy weak hooks. Flag everything that sounds generic, polite, or like it needs context. Weak hooks kill launches.",
    "hook_rewriter": "You are a hook rewriter. Make weak hooks viral. The best hooks are: specific with numbers, contrarian, urgent, or shocking. Kill vagueness.",
    "narrative": "You are a narrative structure specialist. Design the story arc: before state → tension → reveal → proof → future state. Use real customer language from the research data.",
    "demo_flow": "You are a demo flow specialist. Design what gets shown when. First 3 seconds: hook. Then: build tension. Then: the magic moment. Make it feel like a breakthrough.",
    "body_writer": "You are a launch body writer. Use the REAL language from Reddit and G2 reviews — the exact frustrations and desires customers have expressed. Every sentence proves the claim. No adjectives. No filler.",
    "mom_test": "You are the Mom Test agent — a 61-year-old Facebook user. Flag ANYTHING technical or abstract. If you pass this test, anyone understands it. Maximum reach.",
    "novelty_check": "You are the Invention Novelty checker. Score each section 1-10. Flag below 7. Make low scores feel like something new exists in the world.",
    "intensity_check": "You are the Copy Intensity checker. Score each section 1-10 for emotional impact. Flag below 7. Cut emotional filler.",
    "filler_cutter": "You are the Filler Cutter. Remove every line that doesn't earn its place. Tighter = more powerful.",
    "assembler": "You are the Final Launch Assembler. Produce the complete ready-to-use launch package. This goes directly to the founder. Make it clean, structured, immediately actionable.",
}


def call_claude(system, prompt, max_tokens=2000):
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return "ERROR: No API key configured. Add it in Settings."
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text


def run_manager(work, criteria, context=""):
    system = """You are a strict quality manager for viral launch content.
If work passes ALL criteria: start with APPROVED
If it fails any: start with REVISE: and list exactly what must change."""
    prompt = f"CRITERIA:\n{criteria}\n\n{'CONTEXT: ' + context + chr(10) if context else ''}WORK:\n{work}\n\nVerdict:"
    return call_claude(system, prompt, max_tokens=600)


# ──────────────────────────────────────────────
# PIPELINE
# ──────────────────────────────────────────────

def pipeline(product_info, competitors, keywords, youtube_key, q):
    R = {}

    def emit(num, name, status, output="", preview=""):
        q.put({"type": "agent", "num": num, "name": name, "status": status,
               "output": output, "preview": preview[:220] if preview else ""})

    def run(num, name, system_key, prompt, max_tokens=2000):
        emit(num, name, "running")
        out = call_claude(SYSTEMS[system_key], prompt, max_tokens)
        emit(num, name, "done", out, out)
        return out

    def mgr(num, name, work, criteria, context=""):
        emit(num, name, "running")
        out = run_manager(work, criteria, context)
        status = "approved" if out.strip().upper().startswith("APPROVED") else "revised"
        emit(num, name, status, out, out)
        return out

    try:
        # ── LIVE RESEARCH ────────────────────────────
        q.put({"type": "phase", "label": "LIVE RESEARCH — Google · Reddit · G2 · LinkedIn · YouTube"})
        emit("R", "Live Research Engine", "running")
        try:
            kw_list = [k.strip() for k in keywords.split(',') if k.strip()] if keywords else None
            comp_list = [c.strip() for c in competitors.split(',') if c.strip()] if competitors else None
            raw = run_full_research(product_info, comp_list, kw_list, youtube_key or None)
            research_brief = format_research_for_claude(raw)
        except Exception as e:
            research_brief = f"Live research unavailable: {e}. Proceeding with Claude's knowledge."
        emit("R", "Live Research Engine", "done", research_brief, research_brief)
        R["research_brief"] = research_brief

        # ── PHASE 1: RESEARCH ────────────────────────
        q.put({"type": "phase", "label": "PHASE 1: RESEARCH SYNTHESIS  (Agents 1–5)"})

        R["market"] = run("1", "Market Researcher", "market",
            f"""Analyse this LIVE market research data and extract sharp insights.

LIVE DATA:
{R['research_brief']}

PRODUCT:
{product_info}

Extract:
1. Top 3 pain points with real quotes from the data
2. Exact emotional language people use (from Reddit/LinkedIn)
3. What's trending up vs declining (from Google Trends)
4. What competitor reviews reveal people actually hate""")

        R["reddit"] = run("2", "Reddit Researcher", "reddit",
            f"""Extract the raw Reddit signal from this live data.

LIVE REDDIT DATA:
{R['research_brief']}

PRODUCT: {product_info}

Find: The exact frustrated phrases, recurring complaints, and what people wish existed.
These are the words we will mirror in the launch.""")

        R["viral"] = run("3", "Viral Launch Analyzer", "viral",
            f"""Analyse what's working virally in this space using the live YouTube and trend data.

LIVE DATA:
{R['research_brief']}

PRODUCT: {product_info}

Find: What hook styles are performing, what claim types get views, what's overused.""")

        R["linkedin"] = run("4", "LinkedIn Signal Analyst", "linkedin",
            f"""Analyse the LinkedIn professional discourse from the live data.

LIVE LINKEDIN DATA:
{R['research_brief']}

PRODUCT: {product_info}

Extract: What professionals publicly celebrate, complain about, and share in this space.
This is the B2B intent signal.""")

        R["novelty"] = run("5", "Novelty Extractor", "novelty",
            f"""Using the full live research, find what is GENUINELY novel about this product.

LIVE MARKET DATA:
{R['research_brief']}

PRODUCT: {product_info}
MARKET INSIGHTS: {R['market'][:400]}

What gap does the data reveal that this product fills uniquely?""")

        # ── PHASE 2: POSITIONING ─────────────────────
        q.put({"type": "phase", "label": "PHASE 2: BOLD CLAIM  (Agents 6–7)"})

        R["positioning"] = run("6", "Positioning Strategist", "positioning",
            f"""Create the BOLD CLAIM using the real market data we've gathered.

PRODUCT: {product_info}
MARKET PAINS (from live data): {R['market'][:400]}
NOVEL ANGLE: {R['novelty'][:300]}
VIRAL PATTERNS: {R['viral'][:300]}
LINKEDIN SIGNAL: {R['linkedin'][:300]}

Generate 5 BOLD CLAIM options ranked best to worst. Each must be counterpositioned against what the data shows exists today.""",
            max_tokens=1500)

        R["pos_mgr"] = mgr("7", "Positioning Manager", R["positioning"],
            "Novel (not just AI-powered), attacks real pain from the research data, specific, exciting, counterpositioned",
            f"Product: {product_info[:200]}")

        # ── PHASE 3: HOOKS ───────────────────────────
        q.put({"type": "phase", "label": "PHASE 3: HOOK WRITING  (Agents 8–11)"})

        R["hooks_v1"] = run("8", "Hook Writer", "hook_writer",
            f"""Write 10 viral hooks using patterns from the live YouTube and Reddit data.

BOLD CLAIM OPTIONS: {R['positioning'][:600]}
REAL CUSTOMER LANGUAGE (from Reddit/G2): {R['reddit'][:400]}
VIRAL TITLE PATTERNS (from YouTube): {R['viral'][:300]}

Mix styles: bold claim, story, data, contrarian, shocking. No polite hooks.""",
            max_tokens=2000)

        R["hook_crit"] = run("9", "Hook Critic", "hook_critic",
            f"Destroy these hooks. Call out every weak one and exactly why.\n\nHOOKS:\n{R['hooks_v1']}",
            max_tokens=1000)

        R["hooks_v2"] = run("10", "Hook Rewriter", "hook_rewriter",
            f"Rewrite weak hooks. Keep strong ones. Final 5 strongest.\n\nORIGINAL: {R['hooks_v1']}\nCRITIQUE: {R['hook_crit']}",
            max_tokens=1500)

        R["hook_mgr"] = mgr("11", "Hook Manager", R["hooks_v2"],
            "Stops scroll in 2 seconds, feels novel, creates 'wait what?' reaction, no prior context needed")

        # ── PHASE 4: NARRATIVE & BODY ────────────────
        q.put({"type": "phase", "label": "PHASE 4: NARRATIVE & BODY  (Agents 12–15)"})

        R["narrative"] = run("12", "Narrative Planner", "narrative",
            f"""Plan the story arc for X thread AND 60-90 sec video script.
Use the real customer language and pain points from the research data.

BOLD CLAIM: {R['positioning'][:300]}
BEST HOOKS: {R['hooks_v2'][:400]}
REAL CUSTOMER PAIN (from data): {R['market'][:300]}
PRODUCT: {product_info}""",
            max_tokens=1500)

        R["demo"] = run("13", "Demo Flow Designer", "demo_flow",
            f"Design the demo sequence. Magic moment first. What gets shown when.\n\nNARRATIVE: {R['narrative'][:500]}\nPRODUCT: {product_info}",
            max_tokens=1000)

        R["body"] = run("14", "Body Writer", "body_writer",
            f"""Write the full launch body for BOTH:
1. X post thread
2. Video script (60-90 sec, teleprompter ready)

Use REAL language from the research — mirror what customers actually say.

BEST HOOK: {R['hooks_v2'][:300]}
NARRATIVE: {R['narrative'][:400]}
DEMO: {R['demo'][:400]}
BOLD CLAIM: {R['positioning'][:300]}
REAL CUSTOMER LANGUAGE: {R['reddit'][:300]}
LINKEDIN SIGNAL: {R['linkedin'][:200]}""",
            max_tokens=2500)

        R["body_mgr"] = mgr("15", "Body Manager", R["body"],
            "Proves hook claim, uses real customer language, specific proof not generic claims, zero filler, every line earned")

        # ── PHASE 5: WEAPONS CHECK ───────────────────
        q.put({"type": "phase", "label": "PHASE 5: WEAPONS CHECK  (Agents 16–20)"})

        R["mom"] = run("16", "Mom Test", "mom_test",
            f"Flag everything a 61-year-old Facebook user wouldn't understand.\n\nCONTENT:\n{R['body']}",
            max_tokens=800)

        R["novelty_chk"] = run("17", "Weapons: Novelty", "novelty_check",
            f"Score each section 1-10 for invention novelty. Flag below 7.\n\nCONTENT:\n{R['body']}",
            max_tokens=800)

        R["intensity_chk"] = run("18", "Weapons: Intensity", "intensity_check",
            f"Score each section 1-10 for copy intensity. Flag below 7.\n\nCONTENT:\n{R['body']}",
            max_tokens=800)

        R["cut"] = run("19", "Filler Cutter", "filler_cutter",
            f"""Apply all feedback. Final tightened copy (X post + video script).

ORIGINAL:\n{R['body']}
MOM TEST: {R['mom'][:300]}
NOVELTY: {R['novelty_chk'][:300]}
INTENSITY: {R['intensity_chk'][:300]}""",
            max_tokens=2000)

        R["final_mgr"] = mgr("20", "Final Manager", R["cut"],
            "Killer hook, proven claim, clear demo narrative, no filler, passes mom test, high novelty and intensity")

        # ── PHASE 6: ASSEMBLY ────────────────────────
        q.put({"type": "phase", "label": "PHASE 6: FINAL ASSEMBLY  (Agent 21)"})

        R["final"] = run("21", "Final Assembler", "assembler",
            f"""Complete ready-to-use launch package.

PRODUCT: {product_info}
BOLD CLAIM: {R['positioning'][:400]}
BEST HOOKS: {R['hooks_v2'][:400]}
REFINED COPY: {R['cut']}
DEMO FLOW: {R['demo'][:400]}
RESEARCH BRIEF: {R['research_brief'][:500]}

OUTPUT FORMAT:
# BOLD CLAIM
[1 sentence]

# FINAL X POST
[thread format — hook, body, CTA. Ready to paste.]

# FINAL VIDEO SCRIPT
[60-90 sec, teleprompter ready, stage directions in brackets]

# 5 ALTERNATIVE HOOKS
[numbered, for A/B testing]

# KEY PROOF POINTS
[3-5 bullets]

# RESEARCH BRIEF
[Key findings from live data that drove this positioning]""",
            max_tokens=3500)

        q.put({"type": "done", "final": R["final"]})

    except Exception as e:
        import traceback
        q.put({"type": "error", "message": str(e), "trace": traceback.format_exc()})


# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────

@app.route('/')
def index():
    return HTML

@app.route('/api/launch', methods=['POST'])
def launch():
    data = request.json
    product_info = data.get('product_info', '').strip()
    competitors = data.get('competitors', '')
    keywords = data.get('keywords', '')
    youtube_key = data.get('youtube_key', '')

    if not product_info:
        return {"error": "No product info provided"}, 400

    q = queue.Queue()
    t = threading.Thread(
        target=pipeline,
        args=(product_info, competitors, keywords, youtube_key, q),
        daemon=True
    )
    t.start()

    def generate():
        while True:
            try:
                item = q.get(timeout=180)
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Timeout — agents took too long'})}\n\n"
                break

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.route('/api/settings', methods=['GET'])
def get_settings():
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    return {"configured": bool(key), "preview": f"sk-ant-...{key[-6:]}" if len(key) > 6 else ""}

@app.route('/api/settings', methods=['POST'])
def save_settings():
    d = request.json
    if d.get('api_key'):
        os.environ['ANTHROPIC_API_KEY'] = d['api_key']
    return {"success": True}


# ──────────────────────────────────────────────
# FRONTEND
# ──────────────────────────────────────────────

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>$CCM Launch OS</title>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,700;0,900;1,700;1,900&family=Barlow:wght@400;500;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
:root{--black:#060606;--forest:#1A3C2F;--forest2:#152E24;--white:#fff;--muted:#5a7a6a;--grey2:#0D1D16;--grey3:#162518;--grey4:#1e3228;--green:#00D26A;--red:#FF5F5F;--yellow:#FFD04A;}
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--black);color:var(--white);font-family:'Barlow',sans-serif;min-height:100vh;}

.topbar{background:var(--forest);border-bottom:1px solid rgba(255,255,255,0.1);padding:0 28px;display:flex;align-items:center;height:52px;gap:16px;position:sticky;top:0;z-index:100;}
.brand{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-style:italic;font-size:22px;letter-spacing:-0.03em;text-transform:uppercase;}
.brand small{font-size:11px;font-weight:400;font-style:normal;color:rgba(255,255,255,0.4);margin-left:8px;font-family:'Barlow',sans-serif;text-transform:none;}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:12px;}
.api-dot{width:7px;height:7px;border-radius:50%;background:var(--red);display:inline-block;margin-right:6px;flex-shrink:0;}
.api-dot.on{background:var(--green);animation:pulse 2s infinite;}
.api-label{font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,255,255,0.4);display:flex;align-items:center;}
.settings-btn{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.55);padding:6px 12px;font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;}
.settings-btn:hover{border-color:var(--white);color:var(--white);}

.main{max-width:1100px;margin:0 auto;padding:32px 24px;}
.hero{text-align:center;padding:36px 0 28px;}
.hero-title{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-style:italic;font-size:48px;text-transform:uppercase;letter-spacing:-0.02em;line-height:1;}
.hero-sub{font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:0.18em;text-transform:uppercase;color:var(--muted);margin-top:10px;}
.hero-sources{display:flex;gap:8px;justify-content:center;margin-top:14px;flex-wrap:wrap;}
.source-badge{font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;padding:3px 8px;border:1px solid rgba(255,255,255,0.1);color:rgba(255,255,255,0.3);}

.input-card{background:var(--grey2);border:1px solid var(--grey3);border-top:3px solid var(--white);padding:24px;display:flex;flex-direction:column;gap:16px;}
.input-label{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);display:block;margin-bottom:6px;}
textarea,input[type=text],input[type=password]{width:100%;background:var(--black);border:1px solid var(--grey3);color:var(--white);padding:12px;font-family:'Barlow',sans-serif;font-size:13px;line-height:1.7;outline:none;transition:border-color 0.15s;}
textarea{resize:vertical;min-height:140px;}
textarea:focus,input:focus{border-color:rgba(255,255,255,0.4);}
textarea::placeholder,input::placeholder{color:rgba(255,255,255,0.2);}
.input-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.btn{padding:12px 24px;font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:14px;text-transform:uppercase;letter-spacing:0.06em;cursor:pointer;border:none;display:inline-flex;align-items:center;gap:8px;transition:all 0.15s;}
.btn-white{background:var(--white);color:var(--black);}
.btn-white:hover{background:rgba(255,255,255,0.88);}
.btn-white:disabled{opacity:0.4;cursor:not-allowed;}
.btn-row{display:flex;justify-content:flex-end;}

.pipeline{margin-top:24px;display:none;}
.pipeline.show{display:block;}
.phase-label{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:10px;text-transform:uppercase;letter-spacing:0.16em;color:var(--muted);padding:18px 0 5px;}
.progress-wrap{margin:12px 0;height:2px;background:var(--grey4);}
.progress-bar{height:100%;background:var(--white);transition:width 0.4s ease;width:0%;}

.agent-row{display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03);}
.agent-num{font-family:'Share Tech Mono',monospace;font-size:9px;color:rgba(255,255,255,0.2);min-width:24px;padding-top:3px;}
.agent-info{flex:1;min-width:0;}
.agent-name{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;text-transform:uppercase;letter-spacing:0.04em;color:rgba(255,255,255,0.4);}
.agent-name.running{color:var(--white);animation:pulse 1.2s infinite;}
.agent-name.done,.agent-name.approved{color:var(--green);}
.agent-name.revised{color:var(--yellow);}
.agent-preview{font-size:11px;color:rgba(255,255,255,0.25);line-height:1.5;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.agent-status{font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;padding:2px 7px;white-space:nowrap;flex-shrink:0;}
.s-wait{color:rgba(255,255,255,0.12);background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);}
.s-running{color:var(--white);background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.18);}
.s-done,.s-approved{color:var(--green);background:rgba(0,210,106,0.07);border:1px solid rgba(0,210,106,0.18);}
.s-revised{color:var(--yellow);background:rgba(255,208,74,0.07);border:1px solid rgba(255,208,74,0.18);}

.output-section{margin-top:32px;display:none;}
.output-section.show{display:block;}
.output-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;}
.output-title{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:20px;text-transform:uppercase;letter-spacing:0.06em;}
.copy-btn{background:var(--white);color:var(--black);padding:8px 16px;font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:11px;text-transform:uppercase;letter-spacing:0.06em;cursor:pointer;border:none;}
.output-body{background:var(--grey2);border:1px solid var(--grey3);border-left:4px solid var(--white);padding:24px;font-size:13px;line-height:1.9;color:var(--white);white-space:pre-wrap;max-height:72vh;overflow-y:auto;font-family:'Barlow',sans-serif;}

/* SETTINGS */
.settings-panel{position:fixed;top:52px;right:0;bottom:0;width:340px;background:var(--forest2);border-left:1px solid rgba(255,255,255,0.08);z-index:200;padding:24px;display:flex;flex-direction:column;gap:14px;transform:translateX(100%);transition:transform 0.25s ease;overflow-y:auto;}
.settings-panel.open{transform:translateX(0);}
.s-title{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:16px;text-transform:uppercase;letter-spacing:0.08em;padding-bottom:14px;border-bottom:1px solid rgba(255,255,255,0.08);}
.s-label{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:rgba(255,255,255,0.45);}
.s-note{font-size:11px;color:rgba(255,255,255,0.25);line-height:1.5;}

.toast{position:fixed;bottom:20px;right:20px;background:var(--forest);border:1px solid rgba(255,255,255,0.15);border-left:4px solid var(--white);padding:10px 16px;font-family:'Share Tech Mono',monospace;font-size:11px;letter-spacing:0.1em;text-transform:uppercase;z-index:999;transform:translateY(80px);opacity:0;transition:all 0.3s ease;}
.toast.show{transform:translateY(0);opacity:1;}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.35}}
@media(max-width:700px){.input-row{grid-template-columns:1fr;}.hero-title{font-size:36px;}}
</style>
</head>
<body>

<div class="topbar">
  <div class="brand">$CCM <small>Launch OS — 21-Agent System</small></div>
  <div class="topbar-right">
    <div class="api-label"><span class="api-dot" id="apiDot"></span><span id="apiText">Checking...</span></div>
    <button class="settings-btn" onclick="toggleSettings()">⚙ Settings</button>
  </div>
</div>

<div class="settings-panel" id="settingsPanel">
  <div class="s-title">⚙ Settings</div>
  <div class="s-label">Anthropic API Key <span style="color:var(--red)">*</span></div>
  <div class="s-note">Required. Get it at console.anthropic.com</div>
  <input type="password" id="apiKeyInput" placeholder="sk-ant-api03-..."/>
  <div class="s-note" id="keyStatus"></div>
  <div class="s-label" style="margin-top:8px;">YouTube Data API Key <span style="color:var(--muted)">(optional)</span></div>
  <div class="s-note">Free via Google Cloud Console. Enables live YouTube research.</div>
  <input type="password" id="ytKeyInput" placeholder="AIza..."/>
  <button class="btn btn-white" style="width:100%;justify-content:center;margin-top:8px;" onclick="saveSettings()">Save Settings</button>
  <div style="border-top:1px solid rgba(255,255,255,0.08);padding-top:14px;">
    <div class="s-label">LinkedIn Data <span style="color:var(--muted)">(optional upgrade)</span></div>
    <div class="s-note" style="margin-top:6px;">Currently using Google → LinkedIn search (free). For deeper LinkedIn data: <br><br>
    • <strong>Proxycurl</strong> — $49/mo, best quality<br>
    • <strong>Exa.ai</strong> — $10/mo, AI web search<br>
    • <strong>PhantomBuster</strong> — $69/mo
    </div>
  </div>
</div>

<div class="main">
  <div class="hero">
    <div class="hero-title">21-Agent<br>Viral Launch System</div>
    <div class="hero-sub">Live market research → positioning → hooks → weapons check → ready-to-launch</div>
    <div class="hero-sources">
      <span class="source-badge">📈 Google Trends</span>
      <span class="source-badge">🔴 Reddit</span>
      <span class="source-badge">⭐ G2 Reviews</span>
      <span class="source-badge">💼 LinkedIn</span>
      <span class="source-badge">▶️ YouTube</span>
      <span class="source-badge">🤖 21 Claude Agents</span>
    </div>
  </div>

  <div class="input-card">
    <div>
      <label class="input-label">Describe your product launch *</label>
      <textarea id="productInput" placeholder="What it is, who it's for, key features, competitors, what makes it different, any traction or numbers..."></textarea>
    </div>
    <div class="input-row">
      <div>
        <label class="input-label">Main competitors <span style="color:var(--muted)">(optional — improves G2/Capterra research)</span></label>
        <input type="text" id="competitorInput" placeholder="e.g. HubSpot, Salesforce, Notion"/>
      </div>
      <div>
        <label class="input-label">Keywords for trends <span style="color:var(--muted)">(optional)</span></label>
        <input type="text" id="keywordsInput" placeholder="e.g. CRM, sales automation, pipeline"/>
      </div>
    </div>
    <div class="btn-row">
      <button class="btn btn-white" id="launchBtn" onclick="startLaunch()">⟶ Run 21 Agents</button>
    </div>
  </div>

  <div class="pipeline" id="pipeline">
    <div class="progress-wrap"><div class="progress-bar" id="progressBar"></div></div>
    <div id="agentList"></div>
  </div>

  <div class="output-section" id="outputSection">
    <div class="output-header">
      <div class="output-title">🚀 Launch Package</div>
      <button class="copy-btn" onclick="copyOutput()">📋 Copy All</button>
    </div>
    <div class="output-body" id="outputBody"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const AGENTS = [
  ["R","Live Research Engine"],
  ["1","Market Researcher"],["2","Reddit Researcher"],["3","Viral Launch Analyzer"],
  ["4","LinkedIn Signal"],["5","Novelty Extractor"],["6","Positioning Strategist"],
  ["7","Positioning Manager"],["8","Hook Writer"],["9","Hook Critic"],
  ["10","Hook Rewriter"],["11","Hook Manager"],["12","Narrative Planner"],
  ["13","Demo Flow Designer"],["14","Body Writer"],["15","Body Manager"],
  ["16","Mom Test"],["17","Weapons: Novelty"],["18","Weapons: Intensity"],
  ["19","Filler Cutter"],["20","Final Manager"],["21","Final Assembler"]
];

let ytKey = '';
window.onload = checkApi;

async function checkApi() {
  try {
    const r = await fetch('/api/settings');
    const d = await r.json();
    document.getElementById('apiDot').className = 'api-dot' + (d.configured ? ' on' : '');
    document.getElementById('apiText').textContent = d.configured ? 'AI Ready' : 'No API Key';
    if (d.configured) document.getElementById('keyStatus').textContent = `Active: ${d.preview}`;
  } catch(e) { document.getElementById('apiText').textContent = 'Server offline'; }
}

function toggleSettings() { document.getElementById('settingsPanel').classList.toggle('open'); }

async function saveSettings() {
  const key = document.getElementById('apiKeyInput').value.trim();
  ytKey = document.getElementById('ytKeyInput').value.trim();
  if (key) {
    await fetch('/api/settings', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})});
    showToast('✓ Settings saved');
    checkApi();
  } else {
    showToast('✓ YouTube key saved');
  }
  document.getElementById('settingsPanel').classList.remove('open');
}

function buildAgentList() {
  const el = document.getElementById('agentList');
  el.innerHTML = '';
  AGENTS.forEach(([num, name]) => {
    el.innerHTML += `<div class="agent-row" id="ar-${num}">
      <div class="agent-num">${num}</div>
      <div class="agent-info">
        <div class="agent-name" id="an-${num}">${name}</div>
        <div class="agent-preview" id="ap-${num}"></div>
      </div>
      <span class="agent-status s-wait" id="as-${num}">Waiting</span>
    </div>`;
  });
}

function updateAgent(num, status, preview) {
  const n = document.getElementById(`an-${num}`);
  const s = document.getElementById(`as-${num}`);
  const p = document.getElementById(`ap-${num}`);
  if (!n) return;
  n.className = `agent-name ${status}`;
  s.className = `agent-status s-${status}`;
  const labels = {running:'Running…',done:'Done ✓',approved:'Approved ✓',revised:'Revised ↻',waiting:'Waiting'};
  s.textContent = labels[status] || status;
  if (preview) p.textContent = preview;
  document.getElementById(`ar-${num}`)?.scrollIntoView({behavior:'smooth',block:'nearest'});
}

async function startLaunch() {
  const product = document.getElementById('productInput').value.trim();
  if (!product) { showToast('⚠ Enter your product info first'); return; }

  const btn = document.getElementById('launchBtn');
  btn.disabled = true; btn.textContent = '⟳ Running…';
  document.getElementById('pipeline').classList.add('show');
  document.getElementById('outputSection').classList.remove('show');
  buildAgentList();

  let completed = 0;

  try {
    const resp = await fetch('/api/launch', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        product_info: product,
        competitors: document.getElementById('competitorInput').value,
        keywords: document.getElementById('keywordsInput').value,
        youtube_key: ytKey,
      })
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while(true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream:true});
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'phase') {
            const div = document.createElement('div');
            div.className = 'phase-label';
            div.textContent = data.label;
            document.getElementById('agentList').appendChild(div);
          } else if (data.type === 'agent') {
            updateAgent(data.num, data.status, data.preview);
            if (['done','approved','revised'].includes(data.status)) {
              completed++;
              document.getElementById('progressBar').style.width = `${Math.round((completed/22)*100)}%`;
            }
          } else if (data.type === 'done') {
            document.getElementById('progressBar').style.width = '100%';
            document.getElementById('outputBody').textContent = data.final;
            document.getElementById('outputSection').classList.add('show');
            document.getElementById('outputSection').scrollIntoView({behavior:'smooth'});
            showToast('✓ Launch package ready!');
          } else if (data.type === 'error') {
            showToast('⚠ ' + data.message);
          }
        } catch(e) {}
      }
    }
  } catch(e) { showToast('⚠ Connection error'); }

  btn.disabled = false; btn.textContent = '⟶ Run 21 Agents';
}

function copyOutput() {
  navigator.clipboard.writeText(document.getElementById('outputBody').textContent)
    .then(() => showToast('✓ Copied!'));
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

document.addEventListener('click', e => {
  const p = document.getElementById('settingsPanel');
  if (p.classList.contains('open') && !p.contains(e.target) && !document.querySelector('.settings-btn').contains(e.target))
    p.classList.remove('open');
});
</script>
</body>
</html>'''


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"\n{'█'*52}")
    print(f"  $CCM Launch OS")
    print(f"  Open: http://localhost:{port}")
    print(f"{'█'*52}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
