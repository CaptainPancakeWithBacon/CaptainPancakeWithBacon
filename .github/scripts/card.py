#!/usr/bin/env python3
"""Profile metrics card: one self-contained SVG drawn from my public GitHub activity.

Commit times, weekdays, the isometric calendar and the streaks all come from the commits I authored
in my public repos, so private work (school, internship) never shows up here.

Usage: card.py [user] [--cache data.json]   ->  ../../assets/card.svg
No dependencies. Uses GITHUB_TOKEN when set (Actions), anonymous otherwise."""
import base64, json, math, os, re, sys, urllib.error, urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Amsterdam")

HERE = Path(__file__).parent
USER = next((a for a in sys.argv[1:] if not a.startswith("-") and not a.endswith(".json")), "CaptainPancakeWithBacon")
CACHE = sys.argv[sys.argv.index("--cache") + 1] if "--cache" in sys.argv else None
OUT = HERE.parent.parent / "assets" / "card.svg"

# ------------------------------------------------------------------ data
def request(url):
    headers = {"User-Agent": "profile-card-svg", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN") and "api.github.com" in url:
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
        return json.load(r)

def api(path): return request("https://api.github.com" + path)

def fetch():
    user = api(f"/users/{USER}")
    repos = [r for r in api(f"/users/{USER}/repos?per_page=100&type=owner")
             if not r["private"] and r["name"] != USER and not r["name"].endswith(".github.io")]
    out = []
    for r in repos:
        times, page = [], 1
        while True:
            try: chunk = api(f"/repos/{USER}/{r['name']}/commits?author={USER}&per_page=100&page={page}")
            except urllib.error.HTTPError as e:
                if e.code == 409: chunk = []  # empty repository
                else: raise
            times += [c["commit"]["author"]["date"] for c in chunk]
            if len(chunk) < 100: break
            page += 1
        langs = {} if r["fork"] else api(f"/repos/{USER}/{r['name']}/languages")  # a fork's bytes are mostly upstream's code
        out.append(dict(name=r["name"], fork=r["fork"], stars=r["stargazers_count"], forks=r["forks_count"],
                        pushed=r["pushed_at"], times=times, langs=langs))
    return dict(user={k: user.get(k) for k in ("login", "name", "bio", "location", "created_at", "followers", "public_repos")},
                repos=out,
                updated=datetime.now(timezone.utc).isoformat(timespec="minutes"))

def load():
    if CACHE and Path(CACHE).exists(): return json.loads(Path(CACHE).read_text())
    data = fetch()
    if CACHE: Path(CACHE).write_text(json.dumps(data))
    return data

# ------------------------------------------------------------------ drawing helpers
W, H = 640, 602
BG, BORDER, TEXT, MUTED, BLUE, WHITE = "#0d1117", "#30363d", "#c9d1d9", "#8b949e", "#58a6ff", "#e6edf3"
GREEN, TRACK = "#3fb950", "#21262d"
SANS = "Inter,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
LANG = {"JavaScript": "#f1e05a", "TypeScript": "#3178c6", "QML": "#44a51c", "Swift": "#F05138", "Svelte": "#ff3e00",
        "PHP": "#4F5D95", "Java": "#b07219", "HTML": "#e34c26", "Python": "#3572A5", "CSS": "#563d7c", "Shell": "#89e051",
        "Jupyter Notebook": "#DA5B0B", "Kotlin": "#A97BFF", "Rust": "#dea584", "C": "#555555", "Vue": "#41b883", "Blade": "#f7523f"}

def font_css():
    def face(file, weight):
        b = base64.b64encode((HERE / "fonts" / file).read_bytes()).decode()
        return f"@font-face{{font-family:'Inter';font-weight:{weight};src:url(data:font/otf;base64,{b})}}"
    return face("Inter-Regular-sub.otf", 400) + face("Inter-SemiBold-sub.otf", 600)

def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def t(x, y, s, size=12, weight=400, fill=TEXT, anchor="start", extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SANS}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{esc(s)}</text>'
def title(x, y, s):
    return (f'<rect x="{x}" y="{y - 10}" width="11" height="11" rx="2.5" fill="none" stroke="{BLUE}" stroke-width="1.4"/>'
            f'<rect x="{x + 3}" y="{y - 7}" width="5" height="1.6" fill="{BLUE}"/><rect x="{x + 3}" y="{y - 3.5}" width="5" height="1.6" fill="{BLUE}"/>'
            + t(x + 19, y, s, 13.5, 600, BLUE))
def shade(c, k):
    return "#%02x%02x%02x" % tuple(int(int(c[i:i + 2], 16) * k) for i in (1, 3, 5))
def n(v): return f"{v:,}"

def icon(kind, x, y):
    s = f'fill="none" stroke="{MUTED}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "clock": return f'<g transform="translate({x} {y})" {s}><circle cx="6.5" cy="6.5" r="5.5"/><path d="M6.5 3.5 V6.5 L8.5 8"/></g>'
    if kind == "people": return f'<g transform="translate({x} {y})" {s}><circle cx="5" cy="4.2" r="2.4"/><path d="M1 11.5 c0 -3 8 -3 8 0"/><path d="M9 3 a2.2 2.2 0 0 1 0 4 M10.5 8.5 c1.6 .4 2.4 1.5 2.4 3"/></g>'
    if kind == "repo": return f'<g transform="translate({x} {y})" {s}><path d="M2 2.5 a1.5 1.5 0 0 1 1.5 -1.5 H11 V10.5 H3.5 a1.5 1.5 0 0 0 -1.5 1.5Z M2 12 V2.5"/></g>'
    if kind == "star": return f'<g transform="translate({x} {y})" {s}><path d="M6.5 1 L8.2 4.7 L12.2 5.2 L9.2 7.9 L10 11.9 L6.5 9.9 L3 11.9 L3.8 7.9 L0.8 5.2 L4.8 4.7Z"/></g>'
    if kind == "fork": return f'<g transform="translate({x} {y})" {s}><circle cx="3" cy="2.5" r="1.6"/><circle cx="10" cy="2.5" r="1.6"/><circle cx="6.5" cy="11" r="1.6"/><path d="M3 4.1 V5.5 q0 1.5 3.5 2 q3.5 -.5 3.5 -2 V4.1 M6.5 7.5 V9.4"/></g>'
    if kind == "pin": return f'<g transform="translate({x} {y})" {s}><path d="M6.5 12.5 C3 8.5 2 7 2 5.2 a4.5 4.5 0 0 1 9 0 C11 7 10 8.5 6.5 12.5Z"/><circle cx="6.5" cy="5.2" r="1.6"/></g>'
    if kind == "flame": return f'<g transform="translate({x} {y})" {s}><path d="M6.5 1 C7 4 10.5 5 10.5 8.5 a4 4 0 0 1 -8 0 C2.5 6.5 4 6 4.5 4 C5.5 5 6.5 4 6.5 1Z"/></g>'
    if kind == "graph": return f'<g transform="translate({x} {y})" {s}><path d="M1 1 V12 H12 M3.5 9 L6 6 L8 8 L11.5 3.5"/></g>'
    if kind == "calendar": return f'<g transform="translate({x} {y})" {s}><rect x="1" y="2.5" width="11" height="9.5" rx="1.5"/><path d="M1 5.5 H12 M4 1 V3.5 M9 1 V3.5"/></g>'
    return ""

def bars(x0, base, vals, labels, bw, gap, maxh, label_every=1, count_fs=9):
    out, top = [], max(vals) or 1
    for i, v in enumerate(vals):
        x = x0 + i * (bw + gap); h = max(2, maxh * v / top) if v else 2
        out.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw}" height="{h:.1f}" rx="{min(3, bw / 2):.1f}" fill="{GREEN if v else TRACK}"/>')
        if v: out.append(t(x + bw / 2, base - h - 4, v, count_fs, 400, TEXT, "middle"))
        if i % label_every == 0: out.append(t(x + bw / 2, base + 16, labels[i], 10, 400, MUTED, "middle"))
    return out

def iso_calendar(counts, today, ox, oy, weeks=26, c=9.2):
    ax, ay = c * .866, c * .5
    start = today - timedelta(days=today.weekday() + 7 * (weeks - 1))
    cells = []
    for w in range(weeks):
        for d in range(7):
            day = start + timedelta(days=w * 7 + d)
            if day > today: continue
            cells.append((w + d, w, d, counts.get(day, 0)))
    out = []
    for _, w, d, cnt in sorted(cells):
        X = ox + (w - d) * ax; Y = oy + (w + d) * ay
        level = 0 if cnt == 0 else 1 if cnt == 1 else 2 if cnt <= 3 else 3 if cnt <= 6 else 4
        base = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"][level]
        h = 1.2 if cnt == 0 else 3 + min(cnt, 10) * 2.6
        top = [(X, Y - h), (X + ax, Y + ay - h), (X, Y + 2 * ay - h), (X - ax, Y + ay - h)]
        pt = lambda P: " ".join(f"{px:.1f},{py:.1f}" for px, py in P)
        left = [top[3], top[2], (top[2][0], top[2][1] + h), (top[3][0], top[3][1] + h)]
        right = [top[1], top[2], (top[2][0], top[2][1] + h), (top[1][0], top[1][1] + h)]
        out.append(f'<polygon points="{pt(left)}" fill="{shade(base, .72)}"/><polygon points="{pt(right)}" fill="{shade(base, .52)}"/>'
                   f'<polygon points="{pt(top)}" fill="{base}"' + (f' stroke="#21262d" stroke-width=".5"' if cnt == 0 else "") + "/>")
    return out

# ------------------------------------------------------------------ render
def render(data):
    now = datetime.fromisoformat(data["updated"]); u = data["user"]; repos = data["repos"]
    local = lambda iso: datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
    stamps = [local(x) for r in repos for x in r["times"]]
    today = now.astimezone(TZ).date()
    days = Counter(s.date() for s in stamps)
    hours = [sum(1 for s in stamps if s.hour == h) for h in range(24)]
    wdays = [sum(1 for s in stamps if s.weekday() == d) for d in range(7)]
    cur, d = 0, today if today in days else today - timedelta(days=1)
    while d in days: cur += 1; d -= timedelta(days=1)
    longest = run = 0; prev = None
    for d in sorted(days):
        run = run + 1 if prev and (d - prev).days == 1 else 1; longest = max(longest, run); prev = d
    busy_day, busy_n = max(days.items(), key=lambda kv: kv[1]) if days else (today, 0)
    week_n = sum(v for k, v in days.items() if (today - k).days < 7)
    total = len(stamps)
    lb = Counter()                                    # languages from my own (non-fork) repos
    for r in repos:
        for k, v in r["langs"].items():
            if k != "Jupyter Notebook": lb[k] += v   # notebooks are mostly JSON output, not code I wrote
    lt = sum(lb.values()) or 1
    top_l = lb.most_common(6); rest = lt - sum(v for _, v in top_l)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">',
         f'<title id="t">GitHub activity of {esc(u["login"])}</title>',
         f'<desc id="d">{total} public commits in {len(repos)} repositories. Current streak {cur} days, longest {longest}. Top languages: '
         + ", ".join(f"{k} {100 * v // lt}%" for k, v in top_l[:4]) + ".</desc>",
         f"<style>{font_css()}</style>",
         f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>']
    # header: four numbers
    for i, (val, label) in enumerate(((n(total), "public commits"), (len(repos), "repositories"),
                                      (sum(r["stars"] for r in repos), "stars"), (u["followers"], "followers"))):
        x = 28 + i * 152
        o.append(t(x, 46, val, 22, 600, WHITE) + t(x, 64, label, 11.5, 400, MUTED))
    o.append(f'<line x1="28" y1="82" x2="{W - 28}" y2="82" stroke="{BORDER}"/>')
    # left column
    XL, WL = 28, 288
    o.append(title(XL, 114, "Commits by time of day") + t(XL + WL, 114, "Amsterdam time", 10.5, 400, MUTED, "end"))
    o += bars(XL, 210, hours, [f"{h:02d}" for h in range(24)], 8, 4.35, 76, 3, 8.5)
    o.append(title(XL, 272, "Commits by day of week"))
    o += bars(XL + 2, 360, wdays, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], 28, 14.7, 64, 1, 10)
    o.append(title(XL, 422, "Languages in my own repos"))
    x = XL; segs = list(top_l) + ([("Other", rest)] if rest > 0 else [])
    o.append(f'<clipPath id="lb"><rect x="{XL}" y="436" width="{WL}" height="9" rx="4.5"/></clipPath><g clip-path="url(#lb)">')
    for k, v in segs:
        w = WL * v / lt; o.append(f'<rect x="{x:.1f}" y="436" width="{w + .5:.1f}" height="9" fill="{LANG.get(k, MUTED)}"/>'); x += w
    o.append("</g>")
    for i, (k, v) in enumerate(segs[:8]):
        lx = XL + (i % 2) * 148; ly = 472 + (i // 2) * 21
        o.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="4.5" fill="{LANG.get(k, MUTED)}"/>' + t(lx + 16, ly, k, 12, 400, TEXT) + t(lx + 136, ly, f"{100 * v / lt:.0f}%", 11, 400, MUTED, "end"))
    # right column
    XR, WR = 342, 270
    o.append(title(XR, 114, "Contribution calendar"))
    o += iso_calendar(days, today, XR + 50, 156, c=8.4)
    y = 322
    for k, label, val in (("flame", "Current streak", f"{cur} day" + ("" if cur == 1 else "s")),
                          ("graph", "Longest streak", f"{longest} days"),
                          ("calendar", "Busiest day", f'{busy_n} commits, {busy_day.strftime("%-d %b")}'),
                          ("clock", "This week", f"{week_n} commit" + ("" if week_n == 1 else "s"))):
        o.append(icon(k, XR, y - 10) + t(XR + 20, y, label, 12.5, 400, MUTED) + t(XR + WR, y, val, 12.5, 600, TEXT, "end")); y += 24
    o.append(title(XR, 450, "Most worked on"))
    top_r = sorted(repos, key=lambda r: -len(r["times"]))[:4]; mx = max(1, len(top_r[0]["times"]))
    y = 478
    for r in top_r:
        c = len(r["times"])
        o.append(t(XR, y, r["name"] + (" (fork)" if r["fork"] else ""), 12.5, 600, TEXT) + t(XR + WR, y, c, 12.5, 600, TEXT, "end"))
        o.append(f'<rect x="{XR}" y="{y + 7}" width="{WR}" height="6" rx="3" fill="{TRACK}"/><rect x="{XR}" y="{y + 7}" width="{max(6, WR * c / mx):.1f}" height="6" rx="3" fill="{GREEN}"/>')
        y += 31
    o.append(t(28, H - 16, f'Public commits only. Updated {now.strftime("%-d %b %Y")}', 10.5, 400, MUTED))
    o.append("</svg>")
    return "\n".join(o)

def stamp_free(svg): return re.sub(r"Updated [^<]*", "", svg)

if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    svg = render(load())
    if OUT.exists() and stamp_free(OUT.read_text()) == stamp_free(svg): print("card unchanged")
    else: OUT.write_text(svg); print("wrote", OUT, OUT.stat().st_size // 1024, "KB")
