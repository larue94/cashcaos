#!/usr/bin/env python3
"""
$CCM Launch OS — Web Platform
21-agent viral launch system with real-time streaming UI
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
    os.system("pip install anthropic flask flask-cors python-dotenv")
    import anthropic

app = Flask(__name__)
CORS(app)

MODEL = "claude-sonnet-4-6"

# ──────────────────────────────────────────────
# AGENT SYSTEM PROMPTS
# ──────────────────────────────────────────────

SYSTEMS = {
    "market": "You are a market research expert specialising in viral content. Find what people genuinely hate, want, and how they talk. Be specific. Quote real patterns. No generic observations.",
    "reddit": "You are a Reddit research expert. Simulate raw, unfiltered thread language — specific frustrations, recurring complaints, the exact words people use when angry at existing solutions.",
    "viral": "You are a viral launch analyst who has studied hundreds of X launches. You know what works NOW vs 2 years ago. You identify novelty gaps and tired positioning.",
    "customer_voice": "You are a customer language specialist. Extract exact words, phrases and metaphors real customers use about their pain. The best marketing mirrors how customers already think and speak.",
    "novelty": "You are a novelty extraction specialist. Find what is GENUINELY new. 'AI-powered' is NOT novel. 'First X that does Y without Z' might be. Be ruthless about weak novelty.",
    "positioning": "You are a positioning strategist behind 30 of the largest X launches. You create BOLD CLAIMS that make products feel inevitable and novel. Think challenger brand. Think counter-positioning.",
    "hook_writer": "You are a viral hook writer for X posts and video scripts. A great hook answers in one sentence: what is this, why does it matter, why has it never existed. Never polite. Never professional. You make people stop scrolling.",
    "hook_critic": "You are a brutal hook critic. Destroy weak hooks. Flag everything that sounds like other launches, uses dead phrases like 'excited to announce', or needs context to understand. Weak hooks kill launches.",
    "hook_rewriter": "You are a hook rewriter. Take weak hooks and make them viral. Best hooks are: specific with numbers, contrarian, urgent, or shocking. Apply critic feedback ruthlessly.",
    "narrative": "You are a narrative structure specialist. Design the story arc: before state → tension → product reveal → proof → future state. Great launches tell a story, not a feature list.",
    "demo_flow": "You are a demo flow specialist. Design the sequence of what gets shown. First 3 seconds: hook. Seconds 5-30: build tension. Then: the magic moment. Find the single most impressive thing and make it the centre.",
    "body_writer": "You are a launch body writer. Every sentence makes the product feel more real, useful, or inevitable. Show don't tell. Proof not adjectives. Never: 'powerful', 'seamless', 'intelligent'. Every line survives a fight.",
    "mom_test": "You are the Mom Test agent — a 61-year-old Facebook user. Flag ANYTHING using jargon, assuming industry knowledge, or that a non-technical person wouldn't understand. If you pass this test, ANYONE can understand it. Maximum views.",
    "novelty_check": "You are the Invention Novelty checker. Score each section 1-10 on whether it makes the product feel like something new exists in the world. Flag anything below 7. Suggest improvements.",
    "intensity_check": "You are the Copy Intensity checker. Score each section 1-10 on whether it makes someone FEEL something. Weak = technically correct but emotionally flat. Strong = urgency, excitement, 'finally' moments. Flag below 7.",
    "filler_cutter": "You are the Filler Cutter. Remove every line that doesn't earn its place. A line earns its place if it: proves the claim, shows the product, creates emotion, or builds urgency. Cut everything else.",
    "assembler": "You are the Final Launch Assembler. You produce the complete, ready-to-use launch package. This goes directly to the founder. Make it clean, structured, and immediately actionable.",
}

AGENT_LIST = [
    ("1", "Market Researcher", "market"),
    ("2", "Reddit Researcher", "reddit"),
    ("3", "Viral Launch Analyzer", "viral"),
    ("4", "Customer Voice", "customer_voice"),
    ("5", "Novelty Extractor", "novelty"),
    ("6", "Positioning Strategist", "positioning"),
    ("7", "Positioning Manager", None),
    ("8", "Hook Writer", "hook_writer"),
    ("9", "Hook Critic", "hook_critic"),
    ("10", "Hook Rewriter", "hook_rewriter"),
    ("11", "Hook Manager", None),
    ("12", "Narrative Planner", "narrative"),
    ("13", "Demo Flow Designer", "demo_flow"),
    ("14", "Body Writer", "body_writer"),
    ("15", "Body Manager", None),
    ("16", "Mom Test", "mom_test"),
    ("17", "Weapons: Novelty Check", "novelty_check"),
    ("18", "Weapons: Intensity Check", "intensity_check"),
    ("19", "Filler Cutter", "filler_cutter"),
    ("20", "Final Manager", None),
    ("21", "Final Assembler", "assembler"),
]


def call_claude(system, prompt, max_tokens=2000):
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return "ERROR: No API key set. Add your ANTHROPIC_API_KEY in Settings."
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def run_manager(work, criteria, context=""):
    system = """You are a strict quality manager for viral launch content. High standards.
If work passes ALL criteria: start with APPROVED
If it fails any: start with REVISE: then list exactly what must change."""
    prompt = f"CRITERIA:\n{criteria}\n\n{'CONTEXT: ' + context + chr(10) + chr(10) if context else ''}WORK:\n{work}\n\nYour verdict:"
    return call_claude(system, prompt, max_tokens=600)


def pipeline(product_info, q):
    R = {}

    def emit(num, name, status, output="", preview=""):
        q.put({"type": "agent", "num": num, "name": name, "status": status,
               "output": output, "preview": preview[:200] if preview else ""})

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
        q.put({"type": "phase", "label": "PHASE 1: DEEP RESEARCH"})

        R["market"] = run("1", "Market Researcher", "market",
            f"Research the market for this product. Find:\n1. Top 3 pain points this solves\n2. What existing solutions frustrate people and why\n3. Emotional language people use when complaining\n4. What has gone viral in this category and why\n5. What the market desperately wants but can't find\n\nPRODUCT:\n{product_info}\n\nBe specific.")

        R["reddit"] = run("2", "Reddit Researcher", "reddit",
            f"Simulate real Reddit thread language about the problem this product solves.\nFind: What do people hate about existing solutions? Exact words? What are they asking for?\n\nPRODUCT: {product_info}\nMARKET: {R['market'][:400]}")

        R["viral"] = run("3", "Viral Launch Analyzer", "viral",
            f"What viral launch patterns apply to this product category?\nWhat hooks work NOW? What claims go viral? What's dead positioning?\n\nPRODUCT: {product_info}")

        R["voice"] = run("4", "Customer Voice", "customer_voice",
            f"Extract the exact emotional language customers use about this problem.\nNot professional language — raw, frustrated, specific.\n\nPRODUCT: {product_info}\nREDDIT: {R['reddit'][:400]}")

        R["novelty"] = run("5", "Novelty Extractor", "novelty",
            f"What is GENUINELY novel about this product? Not features. Not 'AI-powered.'\nThe one thing that has never been combined this way.\n\nPRODUCT: {product_info}\nMARKET: {R['market'][:400]}")

        q.put({"type": "phase", "label": "PHASE 2: BOLD CLAIM"})

        R["positioning"] = run("6", "Positioning Strategist", "positioning",
            f"Create the BOLD CLAIM — the one sentence that defines everything.\nMust be: novel, specific, counterpositioned, immediately understood.\n\nPRODUCT: {product_info}\nMARKET PAINS: {R['market'][:300]}\nNOVEL ANGLE: {R['novelty'][:300]}\nVIRAL PATTERNS: {R['viral'][:300]}\n\nGenerate 5 BOLD CLAIM options ranked best to worst. Explain why each works or fails.",
            max_tokens=1500)

        R["pos_mgr"] = mgr("7", "Positioning Manager", R["positioning"],
            "Novel (not just AI-powered), attacks real pain, specific, exciting, counterpositioned against today's market",
            f"Product: {product_info[:200]}")

        q.put({"type": "phase", "label": "PHASE 3: HOOK WRITING"})

        R["hooks_v1"] = run("8", "Hook Writer", "hook_writer",
            f"Write 10 viral hooks. Mix: bold claim, story, data, contrarian, shocking.\nNo 'excited to announce.' No 'introducing.' No polite hooks.\n\nBOLD CLAIM: {R['positioning'][:600]}\nCUSTOMER LANGUAGE: {R['voice'][:400]}\n\nWrite for both X post AND video opening line.",
            max_tokens=2000)

        R["hook_crit"] = run("9", "Hook Critic", "hook_critic",
            f"Destroy these hooks. Call out every weak one and exactly why it's weak.\n\nHOOKS:\n{R['hooks_v1']}",
            max_tokens=1000)

        R["hooks_v2"] = run("10", "Hook Rewriter", "hook_rewriter",
            f"Rewrite the weak hooks. Keep the strong ones. Produce the final 5 strongest hooks.\n\nORIGINAL: {R['hooks_v1']}\nCRITIQUE: {R['hook_crit']}",
            max_tokens=1500)

        R["hook_mgr"] = mgr("11", "Hook Manager", R["hooks_v2"],
            "Stops scroll in 2 seconds, feels novel, creates 'wait what?' reaction, needs no prior context")

        q.put({"type": "phase", "label": "PHASE 4: NARRATIVE & BODY"})

        R["narrative"] = run("12", "Narrative Planner", "narrative",
            f"Plan the story arc for X thread AND 60-90 sec video script.\nBefore state → tension → reveal → proof → future state.\n\nBOLD CLAIM: {R['positioning'][:300]}\nBEST HOOKS: {R['hooks_v2'][:400]}\nPRODUCT: {product_info}",
            max_tokens=1500)

        R["demo"] = run("13", "Demo Flow Designer", "demo_flow",
            f"Design the demo sequence. What gets shown first? Where is the magic moment?\n\nNARRATIVE: {R['narrative'][:500]}\nPRODUCT: {product_info}",
            max_tokens=1000)

        R["body"] = run("14", "Body Writer", "body_writer",
            f"Write the full launch body for BOTH:\n1. X post thread\n2. Video script (60-90 sec, teleprompter ready)\n\nEvery line proves the claim. No adjectives. No filler.\n\nBEST HOOK: {R['hooks_v2'][:300]}\nNARRATIVE: {R['narrative'][:400]}\nDEMO: {R['demo'][:400]}\nBOLD CLAIM: {R['positioning'][:300]}\nCUSTOMER VOICE: {R['voice'][:300]}",
            max_tokens=2500)

        R["body_mgr"] = mgr("15", "Body Manager", R["body"],
            "Proves hook claim, shows before/after, specific proof not generic claims, zero filler, every line earned")

        q.put({"type": "phase", "label": "PHASE 5: WEAPONS CHECK"})

        R["mom"] = run("16", "Mom Test", "mom_test",
            f"Test this content. Flag everything a 61-year-old Facebook user wouldn't understand.\nSuggest plain English replacements.\n\nCONTENT:\n{R['body']}",
            max_tokens=800)

        R["novelty_chk"] = run("17", "Weapons: Novelty", "novelty_check",
            f"Score each section 1-10 for invention novelty. Flag below 7. Suggest fixes.\n\nCONTENT:\n{R['body']}",
            max_tokens=800)

        R["intensity_chk"] = run("18", "Weapons: Intensity", "intensity_check",
            f"Score each section 1-10 for copy intensity. Flag below 7. Mark filler for cutting.\n\nCONTENT:\n{R['body']}",
            max_tokens=800)

        R["cut"] = run("19", "Filler Cutter", "filler_cutter",
            f"Apply all feedback. Produce the final tightened copy (X post + video script).\n\nORIGINAL:\n{R['body']}\n\nMOM TEST: {R['mom'][:300]}\nNOVELTY: {R['novelty_chk'][:300]}\nINTENSITY: {R['intensity_chk'][:300]}",
            max_tokens=2000)

        R["final_mgr"] = mgr("20", "Final Manager", R["cut"],
            "Killer hook, proven claim, clear demo narrative, no filler, passes mom test, high novelty and intensity")

        q.put({"type": "phase", "label": "PHASE 6: FINAL ASSEMBLY"})

        R["final"] = run("21", "Final Assembler", "assembler",
            f"""Produce the complete ready-to-use launch package.

PRODUCT: {product_info}
BOLD CLAIM OPTIONS: {R['positioning'][:400]}
BEST HOOKS: {R['hooks_v2'][:400]}
REFINED COPY: {R['cut']}
DEMO FLOW: {R['demo'][:400]}
RESEARCH: {R['market'][:200]} | NOVELTY: {R['novelty'][:200]}

OUTPUT:
# BOLD CLAIM
[1 sentence]

# FINAL X POST
[thread format, hook + body + CTA]

# FINAL VIDEO SCRIPT
[60-90 sec, teleprompter ready, with stage directions in brackets]

# 5 ALTERNATIVE HOOKS
[numbered list for A/B testing]

# KEY PROOF POINTS
[3-5 bullets]

# RESEARCH BRIEF
[why this positioning — what we found]""",
            max_tokens=3000)

        q.put({"type": "done", "final": R["final"]})

    except Exception as e:
        q.put({"type": "error", "message": str(e)})


# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────

@app.route('/')
def index():
    return HTML

@app.route('/api/launch', methods=['POST'])
def launch():
    product_info = request.json.get('product_info', '').strip()
    if not product_info:
        return {"error": "No product info provided"}, 400

    q = queue.Queue()
    thread = threading.Thread(target=pipeline, args=(product_info, q), daemon=True)
    thread.start()

    def generate():
        while True:
            try:
                item = q.get(timeout=120)
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Timeout'})}\n\n"
                break

    return Response(stream_with_context(generate()), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    return {"configured": bool(key), "preview": f"sk-ant-...{key[-6:]}" if len(key) > 6 else ""}

@app.route('/api/settings', methods=['POST'])
def save_settings():
    key = request.json.get('api_key', '')
    if key:
        os.environ['ANTHROPIC_API_KEY'] = key
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
:root{--black:#060606;--forest:#1A3C2F;--forest2:#152E24;--white:#fff;--muted:#5a7a6a;--grey2:#0D1D16;--grey3:#162518;--grey4:#1e3228;--green:#00D26A;--red:#FF5F5F;}
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--black);color:var(--white);font-family:'Barlow',sans-serif;min-height:100vh;}

.topbar{background:var(--forest);border-bottom:1px solid rgba(255,255,255,0.1);padding:0 28px;display:flex;align-items:center;height:52px;gap:16px;position:sticky;top:0;z-index:100;}
.brand{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-style:italic;font-size:22px;letter-spacing:-0.03em;text-transform:uppercase;color:var(--white);}
.brand small{font-size:12px;font-weight:400;font-style:normal;color:rgba(255,255,255,0.4);margin-left:8px;font-family:'Barlow',sans-serif;}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:12px;}
.api-dot{width:7px;height:7px;border-radius:50%;background:var(--red);display:inline-block;margin-right:6px;}
.api-dot.on{background:var(--green);animation:pulse 2s infinite;}
.api-label{font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,255,255,0.4);}
.settings-btn{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.55);padding:6px 12px;font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;}
.settings-btn:hover{border-color:var(--white);color:var(--white);}

.main{max-width:1100px;margin:0 auto;padding:32px 24px;}

.hero{text-align:center;padding:40px 0 32px;}
.hero-title{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-style:italic;font-size:52px;text-transform:uppercase;letter-spacing:-0.02em;line-height:1;}
.hero-sub{font-family:'Share Tech Mono',monospace;font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:var(--muted);margin-top:10px;}

.input-card{background:var(--grey2);border:1px solid var(--grey3);border-top:3px solid var(--white);padding:24px;}
.input-label{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);margin-bottom:10px;display:block;}
textarea{width:100%;background:var(--black);border:1px solid var(--grey3);color:var(--white);padding:14px;font-family:'Barlow',sans-serif;font-size:14px;line-height:1.7;resize:vertical;min-height:160px;outline:none;}
textarea:focus{border-color:rgba(255,255,255,0.4);}
textarea::placeholder{color:rgba(255,255,255,0.2);}
.btn{padding:12px 24px;font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:14px;text-transform:uppercase;letter-spacing:0.06em;cursor:pointer;border:none;transition:all 0.15s;display:inline-flex;align-items:center;gap:8px;}
.btn-white{background:var(--white);color:var(--black);}
.btn-white:hover{background:rgba(255,255,255,0.88);}
.btn-white:disabled{opacity:0.4;cursor:not-allowed;}
.btn-row{display:flex;justify-content:flex-end;margin-top:14px;}

.pipeline{margin-top:24px;display:none;}
.pipeline.show{display:block;}

.phase-label{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:11px;text-transform:uppercase;letter-spacing:0.14em;color:var(--muted);padding:16px 0 6px;}

.agent-row{display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04);}
.agent-num{font-family:'Share Tech Mono',monospace;font-size:10px;color:rgba(255,255,255,0.25);min-width:28px;padding-top:2px;}
.agent-name{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:14px;text-transform:uppercase;letter-spacing:0.04em;color:rgba(255,255,255,0.5);min-width:200px;padding-top:1px;}
.agent-name.running{color:var(--white);animation:pulse 1s infinite;}
.agent-name.done,.agent-name.approved{color:var(--green);}
.agent-name.revised{color:rgba(255,200,80,1);}
.agent-status{font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;padding:2px 8px;border-radius:2px;}
.status-waiting{color:rgba(255,255,255,0.15);background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);}
.status-running{color:var(--white);background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.2);}
.status-done,.status-approved{color:var(--green);background:rgba(0,210,106,0.08);border:1px solid rgba(0,210,106,0.2);}
.status-revised{color:rgba(255,200,80,1);background:rgba(255,200,80,0.08);border:1px solid rgba(255,200,80,0.2);}
.agent-preview{font-family:'Barlow',sans-serif;font-size:12px;color:rgba(255,255,255,0.3);line-height:1.5;margin-top:3px;flex:1;}

.progress-bar-wrap{margin:16px 0;height:2px;background:var(--grey4);border-radius:1px;}
.progress-bar{height:100%;background:var(--white);border-radius:1px;transition:width 0.4s ease;width:0%;}

.output-section{margin-top:32px;display:none;}
.output-section.show{display:block;}
.output-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}
.output-title{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:22px;text-transform:uppercase;letter-spacing:0.06em;}
.output-body{background:var(--grey2);border:1px solid var(--grey3);border-left:4px solid var(--white);padding:24px;font-family:'Barlow',sans-serif;font-size:14px;line-height:1.9;color:var(--white);white-space:pre-wrap;max-height:70vh;overflow-y:auto;}
.copy-btn{background:var(--white);color:var(--black);padding:8px 16px;font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;cursor:pointer;border:none;}
.copy-btn:hover{background:rgba(255,255,255,0.88);}

/* SETTINGS PANEL */
.settings-panel{position:fixed;top:52px;right:0;bottom:0;width:320px;background:var(--forest);border-left:1px solid rgba(255,255,255,0.1);z-index:200;padding:24px;display:flex;flex-direction:column;gap:16px;transform:translateX(100%);transition:transform 0.25s ease;}
.settings-panel.open{transform:translateX(0);}
.settings-title{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:16px;text-transform:uppercase;letter-spacing:0.08em;padding-bottom:14px;border-bottom:1px solid rgba(255,255,255,0.1);}
.s-label{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:rgba(255,255,255,0.5);}
.s-note{font-size:11px;color:rgba(255,255,255,0.3);line-height:1.5;}
input[type=password]{width:100%;background:var(--black);border:1px solid var(--grey3);color:var(--white);padding:10px 12px;font-family:'Barlow',sans-serif;font-size:13px;outline:none;}
input[type=password]:focus{border-color:rgba(255,255,255,0.4);}

.toast{position:fixed;bottom:20px;right:20px;background:var(--forest);border:1px solid rgba(255,255,255,0.2);border-left:4px solid var(--white);padding:10px 16px;font-family:'Share Tech Mono',monospace;font-size:11px;letter-spacing:0.1em;text-transform:uppercase;z-index:999;transform:translateY(80px);opacity:0;transition:all 0.3s ease;}
.toast.show{transform:translateY(0);opacity:1;}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
</style>
</head>
<body>

<div class="topbar">
  <div class="brand">$CCM <small>Launch OS</small></div>
  <div class="topbar-right">
    <div class="api-label"><span class="api-dot" id="apiDot"></span><span id="apiText">Checking...</span></div>
    <button class="settings-btn" onclick="toggleSettings()">⚙ Settings</button>
  </div>
</div>

<div class="settings-panel" id="settingsPanel">
  <div class="settings-title">⚙ Settings</div>
  <div class="s-label">Anthropic API Key</div>
  <div class="s-note">Required for all 21 agents. Get it at console.anthropic.com</div>
  <input type="password" id="apiKeyInput" placeholder="sk-ant-api03-..."/>
  <div class="s-note" id="keyStatus"></div>
  <button class="btn btn-white" style="width:100%;justify-content:center;" onclick="saveKey()">Save Key</button>
</div>

<div class="main">
  <div class="hero">
    <div class="hero-title">21-Agent<br>Viral Launch System</div>
    <div class="hero-sub">Research · Positioning · Hooks · Narrative · Weapons Check · Assembly</div>
  </div>

  <div class="input-card">
    <label class="input-label">Describe your product launch</label>
    <textarea id="productInput" placeholder="Include:&#10;• What it is and what it does&#10;• Who it's for&#10;• Key features or capabilities&#10;• Main competitors / existing alternatives&#10;• What makes it different&#10;• Any traction, numbers, social proof"></textarea>
    <div class="btn-row">
      <button class="btn btn-white" id="launchBtn" onclick="startLaunch()">⟶ Run 21 Agents</button>
    </div>
  </div>

  <div class="pipeline" id="pipeline">
    <div class="progress-bar-wrap"><div class="progress-bar" id="progressBar"></div></div>
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
  ["1","Market Researcher"],["2","Reddit Researcher"],["3","Viral Launch Analyzer"],
  ["4","Customer Voice"],["5","Novelty Extractor"],["6","Positioning Strategist"],
  ["7","Positioning Manager"],["8","Hook Writer"],["9","Hook Critic"],
  ["10","Hook Rewriter"],["11","Hook Manager"],["12","Narrative Planner"],
  ["13","Demo Flow Designer"],["14","Body Writer"],["15","Body Manager"],
  ["16","Mom Test"],["17","Weapons: Novelty"],["18","Weapons: Intensity"],
  ["19","Filler Cutter"],["20","Final Manager"],["21","Final Assembler"]
];

window.onload = checkApi;

async function checkApi() {
  try {
    const r = await fetch('/api/settings');
    const d = await r.json();
    document.getElementById('apiDot').className = 'api-dot' + (d.configured ? ' on' : '');
    document.getElementById('apiText').textContent = d.configured ? 'AI Ready' : 'No API Key';
    if (d.configured) document.getElementById('keyStatus').textContent = `Active: ${d.preview}`;
  } catch(e) {
    document.getElementById('apiText').textContent = 'Server offline';
  }
}

function toggleSettings() {
  document.getElementById('settingsPanel').classList.toggle('open');
}

async function saveKey() {
  const key = document.getElementById('apiKeyInput').value.trim();
  if (!key) return;
  await fetch('/api/settings', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})});
  showToast('✓ API key saved');
  checkApi();
  document.getElementById('settingsPanel').classList.remove('open');
}

function buildAgentList() {
  const el = document.getElementById('agentList');
  el.innerHTML = '';
  AGENTS.forEach(([num, name]) => {
    el.innerHTML += `
    <div class="agent-row" id="agent-row-${num}">
      <div class="agent-num">${num}</div>
      <div>
        <div class="agent-name" id="agent-name-${num}">${name}</div>
        <div class="agent-preview" id="agent-preview-${num}"></div>
      </div>
      <div style="margin-left:auto;padding-top:2px;">
        <span class="agent-status status-waiting" id="agent-status-${num}">Waiting</span>
      </div>
    </div>`;
  });
}

function updateAgent(num, status, preview) {
  const nameEl = document.getElementById(`agent-name-${num}`);
  const statusEl = document.getElementById(`agent-status-${num}`);
  const previewEl = document.getElementById(`agent-preview-${num}`);
  if (!nameEl) return;

  nameEl.className = `agent-name ${status}`;
  statusEl.className = `agent-status status-${status}`;
  const labels = {running:'Running…',done:'Done',approved:'Approved',revised:'Revised',waiting:'Waiting'};
  statusEl.textContent = labels[status] || status;
  if (preview) previewEl.textContent = preview;

  // scroll agent into view
  document.getElementById(`agent-row-${num}`)?.scrollIntoView({behavior:'smooth',block:'nearest'});
}

async function startLaunch() {
  const product = document.getElementById('productInput').value.trim();
  if (!product) { showToast('⚠ Enter your product info first'); return; }

  const btn = document.getElementById('launchBtn');
  btn.disabled = true;
  btn.textContent = '⟳ Running…';

  document.getElementById('pipeline').classList.add('show');
  document.getElementById('outputSection').classList.remove('show');
  buildAgentList();

  let completed = 0;

  try {
    const resp = await fetch('/api/launch', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({product_info: product})
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));

          if (data.type === 'phase') {
            const el = document.getElementById('agentList');
            const div = document.createElement('div');
            div.className = 'phase-label';
            div.textContent = data.label;
            el.appendChild(div);

          } else if (data.type === 'agent') {
            updateAgent(data.num, data.status, data.preview);
            if (data.status === 'done' || data.status === 'approved' || data.status === 'revised') {
              completed++;
              document.getElementById('progressBar').style.width = `${(completed/21)*100}%`;
            }

          } else if (data.type === 'done') {
            document.getElementById('progressBar').style.width = '100%';
            document.getElementById('outputBody').textContent = data.final;
            document.getElementById('outputSection').classList.add('show');
            document.getElementById('outputSection').scrollIntoView({behavior:'smooth'});
            showToast('✓ Launch package ready!');

          } else if (data.type === 'error') {
            showToast('⚠ Error: ' + data.message);
          }
        } catch(e) {}
      }
    }
  } catch(e) {
    showToast('⚠ Connection error — is the server running?');
  }

  btn.disabled = false;
  btn.textContent = '⟶ Run 21 Agents';
}

function copyOutput() {
  const text = document.getElementById('outputBody').textContent;
  navigator.clipboard.writeText(text).then(() => showToast('✓ Copied to clipboard!'));
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

document.addEventListener('click', e => {
  const p = document.getElementById('settingsPanel');
  const b = document.querySelector('.settings-btn');
  if (p.classList.contains('open') && !p.contains(e.target) && !b.contains(e.target))
    p.classList.remove('open');
});
</script>
</body>
</html>'''


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"\n{'█'*50}")
    print(f"  $CCM Launch OS — Web Platform")
    print(f"{'█'*50}")
    print(f"  Open: http://localhost:{port}")
    print(f"{'█'*50}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
