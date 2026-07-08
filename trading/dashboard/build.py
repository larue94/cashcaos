"""Builds the portfolio metrics dashboard — one self-contained HTML file.

Open the produced file in any browser. No internet needed, nothing tracked.
Colors follow a validated accessible palette (works in light and dark mode
and for color-blind readers; every status flag carries an icon + word, never
color alone).
"""

import html
import json

import pandas as pd

from trading.backtest.metrics import Metric

# Validated reference palette (see dataviz skill references/palette.md).
_CSS = """
:root {
  --surface: #fcfcfb; --page: #f9f9f7; --ink: #0b0b0b; --ink2: #52514e;
  --muted: #898781; --grid: #e1e0d9; --axis: #c3c2b7;
  --series1: #2a78d6; --bench: #898781;
  --good: #0ca30c; --warn: #fab219; --crit: #d03b3b;
  --pos-pole: 42,120,214; --neg-pole: 208,59,59; --mid: #f0efec;
  --border: rgba(11,11,11,0.10);
}
@media (prefers-color-scheme: dark) {
  :root {
    --surface: #1a1a19; --page: #0d0d0d; --ink: #ffffff; --ink2: #c3c2b7;
    --muted: #898781; --grid: #2c2c2a; --axis: #383835;
    --series1: #3987e5; --bench: #898781;
    --pos-pole: 57,135,229; --neg-pole: 230,103,103; --mid: #383835;
    --border: rgba(255,255,255,0.10);
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
       font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
.wrap { max-width: 1060px; margin: 0 auto; padding: 24px 20px 60px; }
h1 { font-size: 26px; margin: 8px 0 2px; }
h2 { font-size: 20px; margin: 36px 0 4px; }
.sub { color: var(--ink2); font-size: 14px; margin: 0 0 12px; }
.banner { border: 1px solid var(--border); border-left: 4px solid var(--warn);
          background: var(--surface); border-radius: 8px; padding: 10px 14px;
          margin: 10px 0; font-size: 14px; color: var(--ink2); }
.banner b { color: var(--ink); }
.banner.crit { border-left-color: var(--crit); }
.card { background: var(--surface); border: 1px solid var(--border);
        border-radius: 10px; padding: 16px 18px; margin: 14px 0; }
table.metrics { width: 100%; border-collapse: collapse; font-size: 14px; }
table.metrics th { text-align: left; color: var(--muted); font-weight: 600;
                   font-size: 12px; padding: 6px 8px;
                   border-bottom: 1px solid var(--grid); }
table.metrics td { padding: 8px; border-bottom: 1px solid var(--grid);
                   vertical-align: top; }
table.metrics tr:last-child td { border-bottom: none; }
.mname { font-weight: 600; }
.mexpl { color: var(--ink2); font-size: 12.5px; margin-top: 2px; }
.mval { font-variant-numeric: tabular-nums; white-space: nowrap; }
.mbench { color: var(--ink2); font-size: 12.5px; }
.chip { display: inline-flex; align-items: center; gap: 5px; font-size: 12px;
        font-weight: 600; padding: 2px 9px; border-radius: 999px;
        border: 1px solid var(--border); white-space: nowrap; }
.chip.green { color: var(--good); } .chip.amber { color: var(--warn); }
.chip.red { color: var(--crit); }  .chip.info { color: var(--muted); }
svg text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
table.grid { border-collapse: collapse; font-size: 12.5px;
             font-variant-numeric: tabular-nums; }
table.grid th, table.grid td { padding: 4px 7px; text-align: right;
                               border: 2px solid var(--surface); }
table.grid th { color: var(--muted); font-weight: 600; }
table.grid td { border-radius: 4px; }
.legend { display: flex; gap: 18px; font-size: 13px; color: var(--ink2);
          margin: 4px 0 8px; }
.legend .sw { display: inline-block; width: 14px; height: 3px;
              border-radius: 2px; vertical-align: middle; margin-right: 6px; }
.tip { position: absolute; pointer-events: none; background: var(--surface);
       border: 1px solid var(--border); border-radius: 6px; padding: 6px 9px;
       font-size: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.12);
       display: none; white-space: nowrap; }
.chartbox { position: relative; }
.scroll { overflow-x: auto; }
"""

_JS = """
document.querySelectorAll('.chartbox').forEach(function (box) {
  var svg = box.querySelector('svg'), tip = box.querySelector('.tip');
  var data = JSON.parse(box.dataset.series);
  var geom = JSON.parse(box.dataset.geom);
  var line = svg.querySelector('.crosshair');
  svg.addEventListener('mousemove', function (ev) {
    var pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
    var loc = pt.matrixTransform(svg.getScreenCTM().inverse());
    var n = data.dates.length;
    var i = Math.round((loc.x - geom.x0) / (geom.x1 - geom.x0) * (n - 1));
    if (i < 0 || i >= n) { tip.style.display = 'none'; line.setAttribute('opacity', 0); return; }
    var x = geom.x0 + (geom.x1 - geom.x0) * i / (n - 1);
    line.setAttribute('x1', x); line.setAttribute('x2', x);
    line.setAttribute('opacity', 1);
    var rows = data.series.map(function (s) {
      return '<span style="color:' + s.color + '">&#9632;</span> ' + s.label +
             ': $' + s.values[i].toFixed(0);
    });
    tip.innerHTML = '<b>' + data.dates[i] + '</b><br>' + rows.join('<br>');
    tip.style.display = 'block';
    var bb = box.getBoundingClientRect();
    var tx = ev.clientX - bb.left + 14, ty = ev.clientY - bb.top - 10;
    if (tx + 180 > bb.width) tx -= 200;
    tip.style.left = tx + 'px'; tip.style.top = ty + 'px';
  });
  svg.addEventListener('mouseleave', function () {
    tip.style.display = 'none'; line.setAttribute('opacity', 0);
  });
});
"""

_CHIP = {"green": ("✓", "good"), "amber": ("!", "watch"),
         "red": ("✕", "poor"), "info": ("·", "info")}


def _metric_rows(metrics: list[Metric]) -> str:
    rows = []
    for m in metrics:
        icon, word = _CHIP[m.rag]
        rows.append(
            f"<tr><td><div class='mname'>{html.escape(m.name)}</div>"
            f"<div class='mexpl'>{html.escape(m.explain)}</div></td>"
            f"<td class='mval'>{html.escape(m.display)}</td>"
            f"<td class='mbench'>{html.escape(m.benchmark)}</td>"
            f"<td><span class='chip {m.rag}'>{icon} {word}</span></td></tr>")
    return ("<table class='metrics'><tr><th>Metric (what it means)</th>"
            "<th>Value</th><th>Institutional benchmark</th><th>Flag</th></tr>"
            + "".join(rows) + "</table>")


def _equity_chart(name: str, returns: pd.Series, spy: pd.Series) -> str:
    """Growth-of-$100 line chart: strategy (blue) vs SPY benchmark (gray)."""
    eq = (1 + returns).cumprod() * 100
    bench = (1 + spy.reindex(returns.index).fillna(0)).cumprod() * 100
    W, H, L, R, T, B = 960, 300, 52, 70, 14, 26
    x0, x1 = L, W - R
    lo = min(float(eq.min()), float(bench.min())) * 0.97
    hi = max(float(eq.max()), float(bench.max())) * 1.03
    n = len(eq)

    def sx(i): return x0 + (x1 - x0) * i / (n - 1)
    def sy(v): return T + (H - T - B) * (1 - (v - lo) / (hi - lo))

    def path(series):
        return " ".join(f"{'M' if i == 0 else 'L'}{sx(i):.1f},{sy(v):.1f}"
                        for i, v in enumerate(series))

    grid, labels = [], []
    step = max(1, round((hi - lo) / 4 / 50) * 50)
    v = (int(lo) // step + 1) * step
    while v < hi:
        y = sy(v)
        grid.append(f"<line x1='{x0}' y1='{y:.1f}' x2='{x1}' y2='{y:.1f}' "
                    "stroke='var(--grid)' stroke-width='1'/>")
        labels.append(f"<text x='{x0 - 8}' y='{y + 4:.1f}' text-anchor='end' "
                      f"font-size='11' fill='var(--muted)'>${v}</text>")
        v += step
    years_seen = set()
    for i, d in enumerate(eq.index):
        if d.year not in years_seen:
            years_seen.add(d.year)
            labels.append(f"<text x='{sx(i):.1f}' y='{H - 8}' font-size='11' "
                          f"fill='var(--muted)'>{d.year}</text>")

    payload = json.dumps({
        "dates": [d.strftime("%Y-%m-%d") for d in eq.index],
        "series": [
            {"label": name, "color": "#2a78d6",
             "values": [round(float(x), 2) for x in eq]},
            {"label": "SPY (buy & hold)", "color": "#898781",
             "values": [round(float(x), 2) for x in bench]},
        ]})
    geom = json.dumps({"x0": x0, "x1": x1})

    return f"""
<div class='legend'>
  <span><span class='sw' style='background:var(--series1)'></span>{html.escape(name)}</span>
  <span><span class='sw' style='background:var(--bench)'></span>SPY (buy &amp; hold)</span>
</div>
<div class='chartbox' data-series='{html.escape(payload)}' data-geom='{html.escape(geom)}'>
<svg viewBox='0 0 {W} {H}' width='100%'>
  {"".join(grid)}
  <line x1='{x0}' y1='{H - B}' x2='{x1}' y2='{H - B}' stroke='var(--axis)' stroke-width='1'/>
  <path d='{path(bench)}' fill='none' stroke='var(--bench)' stroke-width='2'
        stroke-dasharray='5 4'/>
  <path d='{path(eq)}' fill='none' stroke='var(--series1)' stroke-width='2'/>
  <text x='{x1 + 6}' y='{sy(float(eq.iloc[-1])) + 4:.1f}' font-size='11.5'
        font-weight='600' fill='var(--series1)'>${eq.iloc[-1]:.0f}</text>
  <text x='{x1 + 6}' y='{sy(float(bench.iloc[-1])) + 4:.1f}' font-size='11.5'
        fill='var(--muted)'>${bench.iloc[-1]:.0f}</text>
  <line class='crosshair' x1='0' y1='{T}' x2='0' y2='{H - B}'
        stroke='var(--axis)' stroke-width='1' opacity='0'/>
  {"".join(labels)}
</svg>
<div class='tip'></div>
</div>
<p class='sub'>Growth of $100 invested at the start of the out-of-sample test
period, after 0.1% per-trade costs. Hover for exact values.</p>"""


def _monthly_grid(table: pd.DataFrame) -> str:
    """Year x month grid, colored blue (up) / red (down) around a gray zero."""
    header = "<tr><th></th>" + "".join(f"<th>{c}</th>" for c in table.columns) + "</tr>"
    body = []
    for year, row in table.iterrows():
        cells = [f"<th>{year}</th>"]
        for col in table.columns:
            v = row[col]
            if pd.isna(v):
                cells.append("<td style='background:transparent'></td>")
                continue
            alpha = min(abs(v) / 0.08, 1.0) * 0.55
            pole = "var(--pos-pole)" if v > 0 else "var(--neg-pole)"
            bg = f"rgba({'42,120,214' if v > 0 else '208,59,59'},{alpha:.2f})" \
                 if abs(v) >= 0.005 else "var(--mid)"
            cells.append(f"<td style='background:{bg}' "
                         f"title='{col} {year}: {v * 100:+.1f}%'>{v * 100:+.1f}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return ("<div class='scroll'><table class='grid'>" + header + "".join(body)
            + "</table></div><p class='sub'>Monthly returns in % — the classic "
              "PM grid. Blue = up month, red = down month; sign is written in "
              "every cell (color is never the only signal).</p>")


def _decay_table(windows) -> str:
    rows = "".join(
        f"<tr><td>{w.train_start}–{w.test_year - 1}</td><td>{w.test_year}</td>"
        f"<td class='mval'>{json.dumps(w.chosen_params)[1:-1].replace(chr(34), '')}</td>"
        f"<td class='mval'>{w.train_sharpe:.2f}</td>"
        f"<td class='mval'>{w.test_sharpe:.2f}</td>"
        f"<td class='mval'>{w.test_sharpe - w.train_sharpe:+.2f}</td></tr>"
        for w in windows)
    return ("<table class='metrics'><tr><th>Trained on</th><th>Tested on</th>"
            "<th>Settings chosen</th><th>Sharpe in training</th>"
            "<th>Sharpe in test</th><th>Decay</th></tr>" + rows + "</table>"
            "<p class='sub'>Each row: settings tuned on 3 years, then frozen "
            "and run on the following unseen year. 'Decay' is test minus "
            "train — mildly negative is normal and honest; strongly negative "
            "means the tuning memorized flukes.</p>")


def _corr_table(corr: pd.DataFrame) -> str:
    header = "<tr><th></th>" + "".join(f"<th>{c}</th>" for c in corr.columns) + "</tr>"
    body = []
    for name, row in corr.iterrows():
        cells = [f"<th>{name}</th>"]
        for c in corr.columns:
            v = row[c]
            cells.append(f"<td style='background:rgba(42,120,214,{abs(v) * 0.45:.2f})'>"
                         f"{v:.2f}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return ("<table class='grid'>" + header + "".join(body) + "</table>"
            "<p class='sub'>1.00 = the books move in lockstep (no "
            "diversification); near 0 = they zig at different times, which "
            "smooths the whole portfolio.</p>")


def build(path, title: str, banners: list[str], sections: list[dict],
          corr: pd.DataFrame | None, generated_note: str) -> None:
    """sections: [{name, subtitle, metrics, returns, spy, monthly, windows?}]"""
    parts = [f"<!doctype html><html><head><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
             f"<title>{html.escape(title)}</title><style>{_CSS}</style></head>"
             f"<body><div class='wrap'>"
             f"<h1>{html.escape(title)}</h1>"
             f"<p class='sub'>{html.escape(generated_note)}</p>"]
    for b in banners:
        parts.append(f"<div class='banner'>⚠️ {b}</div>")
    parts.append(
        "<div class='card'><b>How to read this page — what the best funds "
        "aim for.</b><p class='sub' style='margin:6px 0 0'>"
        "Maximizing return alone is easy: just take huge risks. The craft "
        "that top funds are judged on is <b>return per unit of risk</b>. "
        "Concretely, an elite track record shows all five at once: "
        "<b>(1) Grow more than the market</b> — the blue line above the gray "
        "SPY line; <b>(2) efficiently</b> — Sharpe above 1 (elite above 2), "
        "Sortino above 2, Calmar above 1; <b>(3) with bounded pain</b> — max "
        "drawdown under 20%, 1-day VaR&nbsp;95% under ~2%, volatility around "
        "10–15%; <b>(4) provably by skill, not luck</b> — Jensen's alpha "
        "positive with p-value under 0.05; <b>(5) not just by riding the "
        "market</b> — beta well under 1 and information ratio above 0.5. "
        "A strategy that maximizes (1) while failing (3) is a rocket with no "
        "seatbelts — the flags below grade every metric against these "
        "targets.</p></div>")
    for s in sections:
        parts.append(f"<h2>{html.escape(s['name'])}</h2>"
                     f"<p class='sub'>{html.escape(s['subtitle'])}</p>")
        parts.append("<div class='card'>"
                     + _equity_chart(s["name"], s["returns"], s["spy"]) + "</div>")
        parts.append("<div class='card'>" + _metric_rows(s["metrics"]) + "</div>")
        parts.append("<div class='card'>" + _monthly_grid(s["monthly"]) + "</div>")
        if s.get("windows"):
            parts.append("<div class='card'><h3 style='margin:2px 0 10px;font-size:15px'>"
                         "Walk-forward honesty check</h3>"
                         + _decay_table(s["windows"]) + "</div>")
    if corr is not None:
        parts.append("<h2>Correlation between strategy books</h2>"
                     "<div class='card'>" + _corr_table(corr) + "</div>")
    parts.append(f"<script>{_JS}</script></div></body></html>")
    path.write_text("".join(parts), encoding="utf-8")
