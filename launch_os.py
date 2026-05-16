#!/usr/bin/env python3
"""
$CCM Launch OS — 21-Agent Viral Launch System
Based on the framework used for 30+ largest launches on X.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    import anthropic
except ImportError:
    os.system("pip install anthropic python-dotenv")
    import anthropic

client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
MODEL = "claude-sonnet-4-6"


def agent(name, system, prompt, max_tokens=2000):
    print(f"\n{'─'*60}")
    print(f"  🤖  {name}")
    print(f"{'─'*60}")
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    output = response.content[0].text
    preview = output[:250].replace('\n', ' ')
    print(f"  → {preview}...")
    return output


def manager(name, work, criteria, context=""):
    system = """You are a strict quality manager for viral launch content.
Review work against ALL criteria. Be specific.
If it passes ALL criteria: start your response with APPROVED
If it fails any: start with REVISE: and list exactly what must change."""
    prompt = f"""CRITERIA:
{criteria}

{'CONTEXT: ' + context if context else ''}

WORK TO REVIEW:
{work}

Your verdict:"""
    return agent(name, system, prompt, max_tokens=600)


# ──────────────────────────────────────────────────────────────
# AGENT SYSTEM PROMPTS
# ──────────────────────────────────────────────────────────────

SYSTEMS = {
    "market": """You are a market research expert specialising in viral content.
You find what people genuinely hate, what they want, and what language they use.
Be specific. Quote real patterns. No generic observations.""",

    "reddit": """You are a Reddit research expert. You know how communities talk about problems.
Simulate the raw, unfiltered language of Reddit threads — specific frustrations, recurring complaints,
the exact words people use when they're angry at existing solutions.""",

    "viral": """You are a viral launch analyst who has studied hundreds of X launches.
You know what hooks work now (not 2 years ago), what claims go viral, what positioning creates buzz.
You identify novelty gaps and tired positioning that no longer works.""",

    "customer_voice": """You are a customer language specialist.
You extract the exact words, phrases and metaphors real customers use about their pain.
The best marketing mirrors how customers already think and speak. Find that language.""",

    "novelty": """You are a novelty extraction specialist.
Your job: find what is GENUINELY new — what has never been combined this way before.
'AI-powered' is not novel. 'First X that does Y without Z' might be.
Be ruthless about weak novelty.""",

    "positioning": """You are a positioning strategist behind 30 of the largest X launches.
You create BOLD CLAIMS that make products feel inevitable and novel.
Positioning is not about features — it's about defining a new category or attacking an old assumption.
Think challenger brand. Think counter-positioning.""",

    "hook_writer": """You are a viral hook writer for X posts and video scripts.
A great hook answers in one sentence: what is this, why does it matter, why has it never existed.
You write 10+ hooks per session. Never polite. Never professional.
You write hooks that make people stop scrolling mid-thumb.""",

    "hook_critic": """You are a brutal hook critic. You destroy weak hooks.
You flag every hook that: sounds like something else, is too polite, uses dead phrases like
'excited to announce' or 'introducing', needs context, or could be said by any other company.
Weak hooks kill launches. Be harsh.""",

    "hook_rewriter": """You are a hook rewriter. You take weak hooks and make them viral.
The best hooks are: specific (with numbers/names), contrarian, urgent, or shocking.
You apply critic feedback and produce stronger versions. You kill vagueness.""",

    "narrative": """You are a narrative structure specialist for product launches.
You design the story arc: before state → tension → product reveal → proof → future state.
Great launches tell a story, not a feature list.""",

    "demo_flow": """You are a demo flow specialist.
You design the sequence of what gets shown. First 3 seconds: hook.
Seconds 5-30: build tension. Then: the magic moment.
You identify the single most impressive thing the product can show and make that the centre.""",

    "body_writer": """You are a launch body writer. Every sentence must make the product feel more real,
more useful, or more inevitable. You show, don't tell. You use proof, not adjectives.
Never: 'powerful', 'seamless', 'intelligent', 'built for modern teams'.
Every line survives a fight. If it doesn't add something, it gets cut.""",

    "mom_test": """You are the Mom Test agent — a 61-year-old woman who only uses Facebook.
You flag ANYTHING that: uses jargon, assumes industry knowledge, is too abstract to picture,
or would make a non-technical person say 'what does that mean?'
If content passes your test, ANYONE can understand it. Mass market = maximum views.""",

    "novelty_check": """You are the Invention Novelty checker.
Score each line 1-10 on whether it makes the product feel like something new exists in the world.
Flag anything below 7. Suggest how to make it feel more novel.
Look for: category creation language, 'never before' claims, contrast with the old way.""",

    "intensity_check": """You are the Copy Intensity checker.
Score each line 1-10 on whether it makes someone FEEL something.
Weak lines are technically correct but emotionally flat.
Strong lines create urgency, excitement, or 'finally' moments.
Flag anything below 7. Cut filler transitions and over-explanation.""",

    "filler_cutter": """You are the Filler Cutter. Remove every line that doesn't earn its place.
A line earns its place if it does ONE of: proves the claim, shows the product, creates emotion, builds urgency.
Lines that explain without adding value get cut. Lines that restate something already said get cut.
After cutting, the launch feels tighter, sharper, more powerful.""",

    "final_manager": """You are the Final Launch Manager doing the last quality check.
The final launch must have: a killer hook, a proven claim, a clear demo narrative, no filler,
it passes the mom test, high novelty, high intensity.
Either give final approval or list the last things that need to change.""",

    "assembler": """You are the Final Launch Assembler.
You take all research, positioning, hooks, narrative and refined copy and produce the complete launch package.
You are the last agent. Your output goes directly to the founder.""",
}


# ──────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────────────────────

def run(product_info):
    R = {}
    start = datetime.now()

    print("\n" + "█" * 60)
    print("  $CCM LAUNCH OS — 21-AGENT VIRAL LAUNCH SYSTEM")
    print("█" * 60)
    print(f"  Started: {start.strftime('%H:%M:%S')}")
    print("█" * 60)

    # ── PHASE 1: RESEARCH ────────────────────────────────────
    print("\n\n📊  PHASE 1: DEEP RESEARCH  (Agents 1–5)")

    R["market"] = agent(
        "Agent 1 — Market Researcher", SYSTEMS["market"],
        f"""Research the market for this product. Find:
1. Top 3 pain points this solves
2. What existing solutions frustrate people and why
3. The emotional language people use when they complain
4. What has already gone viral in this category and why
5. What the market desperately wants but can't find

PRODUCT:
{product_info}

Be specific. Use real patterns."""
    )

    R["reddit"] = agent(
        "Agent 2 — Reddit Researcher", SYSTEMS["reddit"],
        f"""Simulate real Reddit thread language about the problem this product solves.
Find: What do people hate about existing solutions? What exact words? What are they asking for?

PRODUCT: {product_info}
MARKET CONTEXT: {R['market'][:400]}"""
    )

    R["viral"] = agent(
        "Agent 3 — Viral Launch Analyzer", SYSTEMS["viral"],
        f"""What viral launch patterns apply to this product category?
What hooks work NOW in this space? What claims go viral?
What positioning worked 2 years ago but is now dead?

PRODUCT: {product_info}"""
    )

    R["voice"] = agent(
        "Agent 4 — Customer Voice", SYSTEMS["customer_voice"],
        f"""Extract the exact emotional language customers use about this problem.
The 'I just want X', the frustrations, the specific words — not professional language.

PRODUCT: {product_info}
REDDIT PATTERNS: {R['reddit'][:400]}"""
    )

    R["novelty"] = agent(
        "Agent 5 — Novelty Extractor", SYSTEMS["novelty"],
        f"""What is GENUINELY novel about this product?
Not features. Not 'AI-powered.' The one thing that has never been combined this way.
What category does this create or destroy?

PRODUCT: {product_info}
MARKET: {R['market'][:400]}"""
    )

    # ── PHASE 2: POSITIONING ─────────────────────────────────
    print("\n\n🎯  PHASE 2: BOLD CLAIM  (Agents 6–7)")

    R["positioning"] = agent(
        "Agent 6 — Positioning Strategist", SYSTEMS["positioning"],
        f"""Create the BOLD CLAIM for this launch — the one sentence that defines everything.
Must be: novel, specific, counterpositioned against what exists, immediately understood.

PRODUCT: {product_info}
MARKET PAINS: {R['market'][:300]}
NOVEL ANGLE: {R['novelty'][:300]}
VIRAL PATTERNS: {R['viral'][:300]}

Generate 5 BOLD CLAIM options, ranked best to worst. Explain why each works or fails.""",
        max_tokens=1500
    )

    R["pos_review"] = manager(
        "Agent 7 — Positioning Manager", R["positioning"],
        "Novel (not just AI-powered), attacks real pain, specific, exciting, counterpositioned against today's market",
        f"Product: {product_info[:200]}"
    )

    # ── PHASE 3: HOOKS ───────────────────────────────────────
    print("\n\n🎣  PHASE 3: HOOK WRITING  (Agents 8–11)")

    R["hooks_v1"] = agent(
        "Agent 8 — Hook Writer", SYSTEMS["hook_writer"],
        f"""Write 10 viral hooks for this launch. Mix styles: bold claim, story, data, contrarian, shocking.
No 'excited to announce.' No 'introducing.' No polite hooks.

BOLD CLAIM OPTIONS: {R['positioning'][:600]}
CUSTOMER LANGUAGE: {R['voice'][:400]}

Write hooks for both an X post AND a video opening line.""",
        max_tokens=2000
    )

    R["hook_critique"] = agent(
        "Agent 9 — Hook Critic", SYSTEMS["hook_critic"],
        f"""Destroy these hooks. Call out every weak one and explain exactly why it's weak.

HOOKS:
{R['hooks_v1']}""",
        max_tokens=1000
    )

    R["hooks_v2"] = agent(
        "Agent 10 — Hook Rewriter", SYSTEMS["hook_rewriter"],
        f"""Rewrite the weak hooks. Keep the strong ones. Make weak ones viral.
Produce the final 5 strongest hooks.

ORIGINAL: {R['hooks_v1']}
CRITIQUE: {R['hook_critique']}""",
        max_tokens=1500
    )

    R["hook_review"] = manager(
        "Agent 11 — Hook Manager", R["hooks_v2"],
        "Stops scroll in 2 seconds, makes product feel novel, creates 'wait what?' reaction, no prior context needed, not like any other launch"
    )

    # ── PHASE 4: NARRATIVE & BODY ────────────────────────────
    print("\n\n📖  PHASE 4: NARRATIVE & BODY  (Agents 12–15)")

    R["narrative"] = agent(
        "Agent 12 — Narrative Planner", SYSTEMS["narrative"],
        f"""Plan the story arc for both an X thread and a 60-90 sec video script.
Before state → tension → product reveal → proof → future state.

BOLD CLAIM: {R['positioning'][:300]}
BEST HOOKS: {R['hooks_v2'][:400]}
PRODUCT: {product_info}""",
        max_tokens=1500
    )

    R["demo_flow"] = agent(
        "Agent 13 — Demo Flow Designer", SYSTEMS["demo_flow"],
        f"""Design the demo sequence. What gets shown first? What is the most impressive moment?
How do we build to the magic moment?

NARRATIVE: {R['narrative'][:500]}
PRODUCT: {product_info}""",
        max_tokens=1000
    )

    R["body"] = agent(
        "Agent 14 — Body Writer", SYSTEMS["body_writer"],
        f"""Write the full launch body for BOTH:
1. X post thread (after the hook)
2. Video script (60-90 seconds, teleprompter ready)

Every line proves the claim. No adjectives. No filler. Show, don't tell.

BEST HOOK: {R['hooks_v2'][:300]}
NARRATIVE: {R['narrative'][:400]}
DEMO FLOW: {R['demo_flow'][:400]}
BOLD CLAIM: {R['positioning'][:300]}
CUSTOMER VOICE: {R['voice'][:300]}""",
        max_tokens=2500
    )

    R["body_review"] = manager(
        "Agent 15 — Body Manager", R["body"],
        "Proves hook claim, shows before/after, uses specific proof not generic claims, zero filler, every line earned"
    )

    # ── PHASE 5: QUALITY CHECKS ──────────────────────────────
    print("\n\n🔍  PHASE 5: WEAPONS CHECK  (Agents 16–20)")

    R["mom_test"] = agent(
        "Agent 16 — Mom Test", SYSTEMS["mom_test"],
        f"""Test this launch content. Flag everything my 61-year-old Facebook mom wouldn't understand.
Suggest plain English replacements.

CONTENT:
{R['body']}""",
        max_tokens=800
    )

    R["novelty_check"] = agent(
        "Agent 17 — Weapons: Novelty", SYSTEMS["novelty_check"],
        f"""Score each section 1-10 for invention novelty. Flag anything below 7.
Suggest how to make low-scoring lines feel more novel.

CONTENT:
{R['body']}""",
        max_tokens=800
    )

    R["intensity_check"] = agent(
        "Agent 18 — Weapons: Intensity", SYSTEMS["intensity_check"],
        f"""Score each section 1-10 for copy intensity. Flag anything below 7.
Mark filler lines for cutting.

CONTENT:
{R['body']}""",
        max_tokens=800
    )

    R["filler_cut"] = agent(
        "Agent 19 — Filler Cutter", SYSTEMS["filler_cutter"],
        f"""Apply all feedback and produce the final tightened launch copy (both X post and video script).

ORIGINAL:
{R['body']}

MOM TEST: {R['mom_test'][:300]}
NOVELTY FEEDBACK: {R['novelty_check'][:300]}
INTENSITY FEEDBACK: {R['intensity_check'][:300]}

Output the tightened versions only.""",
        max_tokens=2000
    )

    R["final_check"] = manager(
        "Agent 20 — Final Manager", R["filler_cut"],
        "Killer hook, proven claim, clear demo narrative, no filler, passes mom test, high novelty and intensity"
    )

    # ── PHASE 6: ASSEMBLY ────────────────────────────────────
    print("\n\n🚀  PHASE 6: FINAL ASSEMBLY  (Agent 21)")

    R["final"] = agent(
        "Agent 21 — Final Assembler", SYSTEMS["assembler"],
        f"""Produce the complete, ready-to-use launch package.

PRODUCT: {product_info}
BOLD CLAIM: {R['positioning'][:400]}
BEST HOOKS: {R['hooks_v2'][:400]}
REFINED COPY: {R['filler_cut']}
DEMO FLOW: {R['demo_flow'][:400]}
RESEARCH: Market pain: {R['market'][:200]} | Novelty: {R['novelty'][:200]}

OUTPUT FORMAT:
# BOLD CLAIM
[1 sentence]

# FINAL X POST
[thread format, hook + body + CTA]

# FINAL VIDEO SCRIPT
[60-90 sec, teleprompter ready, with stage directions]

# 5 ALTERNATIVE HOOKS
[numbered, for A/B testing]

# KEY PROOF POINTS
[3-5 bullets]

# RESEARCH BRIEF
[why this positioning — what we found]""",
        max_tokens=3000
    )

    # ── SAVE ─────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"launch_{timestamp}.md"

    with open(filename, "w") as f:
        f.write(f"# $CCM Launch OS — Output\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Product:** {product_info[:200]}\n\n")
        f.write("---\n\n")
        f.write("## FINAL LAUNCH PACKAGE\n\n")
        f.write(R["final"])
        f.write("\n\n---\n\n## FULL RESEARCH TRAIL\n\n")
        for key, value in R.items():
            if key != "final":
                f.write(f"### {key.upper()}\n{value}\n\n")

    elapsed = (datetime.now() - start).seconds
    print("\n\n" + "█" * 60)
    print("  ✅  LAUNCH OS COMPLETE")
    print("█" * 60)
    print(f"  Agents run: 21 | Time: {elapsed}s")
    print(f"  Output saved: {filename}")
    print("█" * 60)
    print("\n\n" + "═" * 60)
    print("  FINAL LAUNCH PACKAGE")
    print("═" * 60)
    print(R["final"])

    return R, filename


# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("  $CCM LAUNCH OS — VIRAL LAUNCH GENERATOR")
    print("█" * 60)
    print("""
Describe your product launch in detail. Include:
- What it is and what it does
- Who it's for
- Key features or capabilities
- Main competitors / existing alternatives
- What makes it different
- Any traction / numbers / social proof

Press Enter twice when done.
""")

    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)

    product_info = "\n".join(lines).strip()

    if not product_info:
        print("No product info provided. Exiting.")
        sys.exit(1)

    run(product_info)
