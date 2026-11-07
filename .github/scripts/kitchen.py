#!/usr/bin/env python3
"""Draws the profile README kitchen as one self-contained SVG.
Usage: kitchen.py [user] [--offline]  ->  kitchen.svg next to this file.
Stats come from GitHub's public API (no token), --offline uses sample data."""
import base64, json, os, sys, urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
USER = next((a for a in sys.argv[1:] if not a.startswith("-")), "CaptainPancakeWithBacon")
POTS = ["#e8452f", "#ffc93c", "#6dbb6a", "#8cc7ee"]  # pot colours, in order of rank

SAMPLE = {"langs": [("JavaScript", 4), ("TypeScript", 2), ("HTML", 2), ("Swift", 1)],
          "commits": 23, "prs": 2, "repos": 3, "cooking": "isobar", "last_push": 3600 * 5}


def get(path):
    headers = {"User-Agent": "kitchen-svg"}
    if os.environ.get("GITHUB_TOKEN"):  # Actions runners share an IP, so anonymous calls get rate limited
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request("https://api.github.com" + path, headers=headers)
    return json.load(urllib.request.urlopen(req, timeout=15))


def fetch(user):
    repos = get(f"/users/{user}/repos?per_page=100")
    events = get(f"/users/{user}/events/public?per_page=100")
    now = datetime.now(timezone.utc)
    age = lambda iso: (now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds()
    langs = {}
    for r in repos:
        if r["language"] and age(r["pushed_at"]) < 365 * 86400:
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    week = [e for e in events if age(e["created_at"]) < 7 * 86400]
    pushes = [e for e in week if e["type"] == "PushEvent"]
    latest = max((r for r in repos if r["name"] != user), key=lambda r: r["pushed_at"])  # the profile repo is pushed by the bot every night
    return {"langs": sorted(langs.items(), key=lambda kv: -kv[1])[:4],
            "commits": sum(e["payload"].get("size", 1) for e in pushes),
            "prs": sum(e["type"] == "PullRequestEvent" for e in week),
            "repos": len({e["repo"]["name"] for e in pushes}),
            "cooking": latest["name"], "last_push": age(latest["pushed_at"])}


def ago(s):
    return "just now" if s < 3600 else f"{int(s // 3600)}h ago" if s < 86400 else f"{int(s // 86400)}d ago"


def font(name, family):
    b64 = base64.b64encode((HERE / "fonts" / name).read_bytes()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/ttf;base64,{b64})}}"


def pot(x, rank, lang, n, top):
    fill = 14 + 44 * n / top  # liquid height, px
    c = POTS[rank]
    steam = "".join(f'<path class="steam" style="animation-delay:{i * .7}s" d="M{x - 20 + i * 20} 120 q-8 -12 0 -24 q8 -12 0 -22"/>' for i in range(3))
    body = f"M{x - 46} 134 v48 q0 14 14 14 h64 q14 0 14 -14 v-48 z"
    return f'''<g>{steam}
  <path d="{body}" fill="#7d6f66"/>
  <rect x="{x - 42}" y="{194 - fill}" width="84" height="{fill}" rx="5" fill="{c}" stroke="none"/>
  <path d="{body}" fill="none"/>
  <path d="M{x - 52} 138 h12 M{x + 40} 138 h12"/>
  <text x="{x}" y="246" class="lbl" text-anchor="middle">{escape(lang)}</text>
  <text x="{x}" y="270" class="sm" text-anchor="middle">{n} repo{'s' if n != 1 else ''}</text></g>'''


def render(d):
    top = max(n for _, n in d["langs"])
    pots = "".join(pot(285 + i * 115, i, l, n, top) for i, (l, n) in enumerate(d["langs"]))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 330" width="900" height="330" role="img" aria-label="Kitchen stats">
<title>This week in the kitchen</title>
<defs><style>{font("Chewy-sub.ttf", "Chewy")}{font("PatrickHand-sub.ttf", "Patrick Hand")}
text{{stroke:none!important}}.ink{{stroke:#2a1d17;stroke-width:6;stroke-linejoin:round;stroke-linecap:round}}
.h{{font-family:Chewy,cursive;fill:#2a1d17}} .lbl{{font:25px Chewy,cursive;fill:#2a1d17}}
.sm{{font:18px 'Patrick Hand',cursive;fill:#2a1d17}}
.steam{{fill:none;stroke:#fff;stroke-width:5;stroke-linecap:round;opacity:0;animation:up 2.4s ease-in infinite}}
@keyframes up{{0%{{opacity:0;transform:translateY(10px)}}30%{{opacity:.85}}100%{{opacity:0;transform:translateY(-26px)}}}}
.flip{{transform-origin:808px 150px;animation:flip 2.2s ease-in-out infinite}}
@keyframes flip{{0%,100%{{transform:translateY(0) rotate(0)}}45%{{transform:translateY(-52px) rotate(180deg)}}60%{{transform:translateY(-8px) rotate(360deg)}}}}
@media (prefers-color-scheme:dark){{.dk{{fill:#3a2a22}}.ticket{{fill:#fff1d6}}}}</style>
<filter id="c" filterUnits="userSpaceOnUse" x="0" y="0" width="900" height="330"><feTurbulence type="fractalNoise" baseFrequency=".03" numOctaves="2" seed="4" result="w"/><feDisplacementMap in="SourceGraphic" in2="w" scale="5"/></filter></defs>
<rect width="900" height="330" fill="#9ed3c4"/>
<g filter="url(#c)" class="ink">
 <g fill="#fff1d6" stroke="none" opacity=".5"><rect x="0" y="0" width="900" height="8"/></g>
 <rect x="0" y="206" width="900" height="124" fill="#c98d52"/><path d="M0 206 H900"/>
 <!-- order ticket -->
 <g transform="rotate(-3 90 90)"><rect x="24" y="26" width="150" height="152" rx="6" fill="#fff" class="ticket"/>
  <path d="M24 40 h150" stroke-dasharray="6 6" stroke-width="3"/>
  <text x="38" y="62" class="h" stroke="none" font-size="22">THIS WEEK</text>
  <text x="38" y="102" class="sm" stroke="none">{d["commits"]} commit{"" if d["commits"] == 1 else "s"}</text>
  <text x="38" y="128" class="sm" stroke="none">{d["prs"]} pull request{"" if d["prs"] == 1 else "s"}</text>
  <text x="38" y="154" class="sm" stroke="none">{d["repos"]} repo{"" if d["repos"] == 1 else "s"} stirred</text></g>
 <!-- stove -->
 <rect x="228" y="196" width="470" height="18" rx="8" fill="#2a1d17"/>
 {pots}
 <!-- pan with flipping pancake -->
 <path d="M740 196 h136" /><path d="M744 188 q64 22 128 0" fill="#555"/><path d="M872 190 h26" stroke-width="8"/>
 <g class="flip"><ellipse cx="808" cy="150" rx="46" ry="11" fill="#f2b865"/><path d="M780 150 q28 8 56 0" fill="none" stroke-width="3" stroke="#b5481c"/></g>
 <text x="800" y="246" class="lbl" stroke="none" text-anchor="middle">{escape(d["cooking"])}</text>
 <text x="800" y="270" class="sm" stroke="none" text-anchor="middle">cooking · pushed {ago(d["last_push"])}</text>
</g></svg>'''


if __name__ == "__main__":
    data = SAMPLE if "--offline" in sys.argv else fetch(USER)
    out = HERE.parent.parent / "assets" / "kitchen.svg"
    out.write_text(render(data))
    print(out, out.stat().st_size, "bytes", data)
