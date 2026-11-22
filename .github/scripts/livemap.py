#!/usr/bin/env python3
"""Living map: draws my public GitHub repos as countries on one self-contained SVG.

Every public repo is a country. Territory follows how many commits I made in it, colour follows
its main language, flags show commits pushed in the last 7 days, and the railway links the repos
I pushed to most recently. The coastline and province layout are generated from a fixed seed,
so the continent only changes when the numbers do.

Usage: livemap.py [user] [--cache data.json]   ->  ../../assets/livemap.svg
No dependencies. Uses GITHUB_TOKEN when set (Actions), anonymous otherwise."""
import base64, heapq, json, math, os, random, re, sys, urllib.error, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
USER = next((a for a in sys.argv[1:] if not a.startswith("-") and not a.endswith(".json")), "CaptainPancakeWithBacon")
CACHE = sys.argv[sys.argv.index("--cache") + 1] if "--cache" in sys.argv else None
OUT = HERE.parent.parent / "assets" / "livemap.svg"

# ---------------------------------------------------------------- GitHub data
def api(path):
    headers = {"User-Agent": "livemap-svg", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request("https://api.github.com" + path, headers=headers), timeout=20) as r:
        return json.load(r), r.headers.get("Link", "")

def my_commits(repo):
    """Commits authored by me: ask for one per page and read the last page number from the Link header."""
    try:
        data, link = api(f"/repos/{USER}/{repo}/commits?author={USER}&per_page=1")
    except urllib.error.HTTPError as e:
        if e.code == 409: return 0  # empty repository
        raise
    last = [p for p in link.split(",") if 'rel="last"' in p]
    if last: return int(last[0].split("page=")[-1].split(">")[0])
    return len(data)

def fetch():
    repos, _ = api(f"/users/{USER}/repos?per_page=100&type=owner")
    events = []
    for page in (1, 2, 3):
        chunk, _ = api(f"/users/{USER}/events/public?per_page=100&page={page}")
        events += chunk
        if len(chunk) < 100: break
    now = datetime.now(timezone.utc)
    age = lambda iso: (now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds()
    week = defaultdict(int)
    for e in events:
        if e["type"] == "PushEvent" and age(e["created_at"]) < 7 * 86400:
            week[e["repo"]["name"].split("/")[-1]] += e["payload"].get("size", 1)
    out = []
    for r in repos:
        if r["private"] or r["name"] == USER or r["name"].endswith(".github.io"): continue
        out.append(dict(name=r["name"], lang=r["language"], commits=my_commits(r["name"]), pushed=r["pushed_at"],
                        created=r["created_at"], stars=r["stargazers_count"], fork=r["fork"], week=week.get(r["name"], 0)))
    return dict(repos=out, week=sum(week.values()), updated=now.isoformat(timespec="minutes"))

def load():
    if CACHE and Path(CACHE).exists(): return json.loads(Path(CACHE).read_text())
    data = fetch()
    if CACHE: Path(CACHE).write_text(json.dumps(data))
    return data

# ---------------------------------------------------------------- map generator (noise + Voronoi)
def _h(ix,iy,s):
    n=(ix*374761393+iy*668265263+s*2147483647)&0xFFFFFFFF
    n=((n^(n>>13))*1274126177)&0xFFFFFFFF
    n^=n>>16
    return n/4294967295.0
def vnoise(x,y,s):
    ix=math.floor(x); iy=math.floor(y); fx=x-ix; fy=y-iy
    fx=fx*fx*(3-2*fx); fy=fy*fy*(3-2*fy)
    a=_h(ix,iy,s); b=_h(ix+1,iy,s); c=_h(ix,iy+1,s); d=_h(ix+1,iy+1,s)
    return (a+(b-a)*fx)+((c+(d-c)*fx)-(a+(b-a)*fx))*fy
def fbm(x,y,s,oct=4):
    t=0; amp=.5; f=1; norm=0
    for i in range(oct):
        t+=amp*vnoise(x*f,y*f,s+i*17); norm+=amp; amp*=.5; f*=2
    return t/norm

def clip(poly,p,q):
    mx=(p[0]+q[0])/2; my=(p[1]+q[1])/2; nx=q[0]-p[0]; ny=q[1]-p[1]
    out=[]
    n=len(poly)
    for i in range(n):
        a=poly[i]; b=poly[(i+1)%n]
        fa=(a[0]-mx)*nx+(a[1]-my)*ny; fb=(b[0]-mx)*nx+(b[1]-my)*ny
        if fa<=0: out.append(a)
        if (fa<0 and fb>0) or (fa>0 and fb<0):
            t=fa/(fa-fb); out.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
    return out
def centroid(poly):
    A=0;cx=0;cy=0;n=len(poly)
    for i in range(n):
        x0,y0=poly[i]; x1,y1=poly[(i+1)%n]; k=x0*y1-x1*y0
        A+=k; cx+=(x0+x1)*k; cy+=(y0+y1)*k
    if abs(A)<1e-9: return poly[0]
    return cx/(3*A),cy/(3*A)

def build(MX,MY,MW,MH,seed=5,S=25.0):
    rng=random.Random(seed)
    RX0,RY0,RX1,RY1=MX-70,MY-70,MX+MW+70,MY+MH+70
    pts=[]; y=RY0+S/2; row=0
    while y<RY1:
        x=RX0+S/2+(S/2 if row%2 else 0)
        while x<RX1:
            pts.append((x+rng.uniform(-.38,.38)*S,y+rng.uniform(-.38,.38)*S)); x+=S
        y+=S*0.88; row+=1
    B=S*2
    def cells(pts):
        grid=defaultdict(list)
        for i,p in enumerate(pts): grid[(int(p[0]//B),int(p[1]//B))].append(i)
        out=[]
        for i,p in enumerate(pts):
            gx,gy=int(p[0]//B),int(p[1]//B)
            cand=[j for dx in range(-2,3) for dy in range(-2,3) for j in grid.get((gx+dx,gy+dy),[]) if j!=i]
            cand.sort(key=lambda j:(pts[j][0]-p[0])**2+(pts[j][1]-p[1])**2)
            poly=[(RX0,RY0),(RX1,RY0),(RX1,RY1),(RX0,RY1)]
            maxr=1e9
            for j in cand:
                q=pts[j]; d=math.hypot(q[0]-p[0],q[1]-p[1])
                if d/2>maxr: break
                poly=clip(poly,p,q)
                if not poly: break
                maxr=max(math.hypot(v[0]-p[0],v[1]-p[1]) for v in poly)
            out.append(poly)
        return out
    polys=cells(pts)
    for _ in range(2):
        pts=[centroid(pl) if pl else p for pl,p in zip(polys,pts)]
        polys=cells(pts)
    # canonical vertices
    verts=[]; bucket={}
    def canon(v):
        kx,ky=int(v[0]*8),int(v[1]*8)
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for vid in bucket.get((kx+dx,ky+dy),()):
                    w=verts[vid]
                    if abs(w[0]-v[0])<.03 and abs(w[1]-v[1])<.03: return vid
        verts.append(v); bucket.setdefault((kx,ky),[]).append(len(verts)-1); return len(verts)-1
    cv=[]
    for pl in polys:
        ids=[]
        for v in pl:
            i=canon(v)
            if not ids or ids[-1]!=i: ids.append(i)
        if len(ids)>1 and ids[0]==ids[-1]: ids.pop()
        cv.append(ids)
    edgecells=defaultdict(list)
    for i,ids in enumerate(cv):
        for k in range(len(ids)):
            a,b=ids[k],ids[(k+1)%len(ids)]
            if a!=b: edgecells[(min(a,b),max(a,b))].append(i)
    # land mask
    cx0,cy0=MX+MW/2,MY+MH/2
    def score(x,y):
        u=(x-cx0)/(MW*.5*.93); v=(y-cy0)/(MH*.5*.93)
        d=math.hypot(u,v)
        return (1-d**1.7)*1.1+(fbm(x/115,y/115,3)-.5)*1.0
    inside=lambda p: MX+14<p[0]<MX+MW-14 and MY+14<p[1]<MY+MH-14
    land={i for i,p in enumerate(pts) if inside(p) and score(*p)>.24}
    adj=defaultdict(set)
    for (a,b),cs in edgecells.items():
        if len(cs)==2: adj[cs[0]].add(cs[1]); adj[cs[1]].add(cs[0])
    seen=set(); comps=[]
    for i in sorted(land):
        if i in seen: continue
        st=[i]; comp=[]; seen.add(i)
        while st:
            c=st.pop(); comp.append(c)
            for n in adj[c]:
                if n in land and n not in seen: seen.add(n); st.append(n)
        comps.append(comp)
    comps.sort(key=len,reverse=True)
    keep=set(comps[0])
    for cp in comps[1:]:
        if len(cp)>=5: keep.update(cp)
    land=keep
    return dict(pts=pts,cv=cv,verts=verts,edgecells=edgecells,land=land,adj=adj,score=score,rng=rng,comps=comps)


# ---------------------------------------------------------------- rendering
W, H = 960, 560
MX, MY, MW, MH = 20, 72, 640, 468
INK, GOLD, CREAM, SAND = "#241c14", "#c9a85a", "#f2e7c9", "#cbbf98"
SERIF = "'Noto Serif',Georgia,serif"
SANS = "Inter,'Helvetica Neue',Arial,sans-serif"
# One colour per repo, handed out in creation order so a repo keeps its colour for good.
PALETTE = ["#2a9d8f", "#e07b28", "#7b5fc4", "#c8402f", "#3f7fd0", "#d9a62e", "#d9468c", "#6fa03a", "#a0663c", "#6b7f99", "#3aa6c4", "#a9a14a"]

def font_css():
    def face(file, family, weight, style="normal"):
        b = base64.b64encode((HERE / "fonts" / file).read_bytes()).decode()
        mime = "font/otf" if file.endswith(".otf") else "font/ttf"
        return f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:{style};src:url(data:{mime};base64,{b})}}"
    return "".join([face("NotoSerif-Bold-sub.ttf", "Noto Serif", 700), face("NotoSerif-Italic-sub.ttf", "Noto Serif", 400, "italic"),
                    face("Inter-Regular-sub.otf", "Inter", 400), face("Inter-SemiBold-sub.otf", "Inter", 600)])

def mix(a, b, t):
    A = [int(a[i:i + 2], 16) for i in (1, 3, 5)]; B = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(A, B))
def tint(c, amt):
    return mix(c, "#ffffff", amt) if amt > 0 else mix(c, "#000000", -amt)
def ago(iso, now):
    s = (now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds()
    return "today" if s < 86400 else f"{int(s // 86400)}d ago" if s < 60 * 86400 else f"{int(s // (30 * 86400))} months ago"
def fmt(P, move=True):
    return ("M" if move else "L") + " L".join(f"{x:.1f} {y:.1f}" for x, y in P)

def render(data):
    now = datetime.fromisoformat(data["updated"]).replace(tzinfo=timezone.utc) if "+" not in data["updated"] else datetime.fromisoformat(data["updated"])
    repos = sorted(data["repos"], key=lambda r: (-r["commits"], r["created"]))
    names = [r["name"] for r in repos]
    M = build(MX, MY, MW, MH, seed=5)
    pts, cv, verts, edgecells, land, adj = M["pts"], M["cv"], M["verts"], M["edgecells"], M["land"], M["adj"]
    rng = random.Random(21)
    landl = sorted(land)

    # slots: farthest-point sampling, so the first slots spread wide. Biggest repos take the first slots.
    cell_at = lambda i: pts[i]
    first = min(landl, key=lambda i: (pts[i][0] - (MX + MW * .45)) ** 2 + (pts[i][1] - (MY + MH * .5)) ** 2)
    slots = [first]; dmin = {i: math.dist(pts[i], pts[first]) for i in landl}
    while len(slots) < len(repos):
        nxt = max(landl, key=lambda i: dmin[i]); slots.append(nxt)
        for i in landl: dmin[i] = min(dmin[i], math.dist(pts[i], pts[nxt]))
    seeds = {r["name"]: slots[k] for k, r in enumerate(repos)}
    weight = {r["name"]: 3 + r["commits"] ** .8 for r in repos}
    own, heaps, size = {}, {n: [] for n in names}, {n: 0 for n in names}
    def push(k, c, cost):
        for n in adj[c]:
            if n in land and n not in own:
                heapq.heappush(heaps[k], (cost + math.dist(pts[n], pts[c]) * rng.uniform(.55, 1.7), n))
    for k, s in seeds.items(): own[s] = k; size[k] = 1; push(k, s, 0)
    while True:
        live = [k for k in heaps if heaps[k]]
        if not live: break
        k = min(live, key=lambda z: size[z] / weight[z])
        while heaps[k] and heaps[k][0][1] in own: heapq.heappop(heaps[k])
        if not heaps[k]: continue
        cost, c = heapq.heappop(heaps[k]); own[c] = k; size[k] += 1; push(k, c, cost)
    for c in land:
        if c not in own: own[c] = min(seeds, key=lambda k: math.dist(pts[seeds[k]], pts[c]))
    byc = defaultdict(list)
    for i in land: byc[own[i]].append(i)
    order = {r["name"]: j for j, r in enumerate(sorted(data["repos"], key=lambda r: r["created"]))}
    barcol = lambda n: PALETTE[order[n] % len(PALETTE)]
    COL = {n: mix(barcol(n), SAND, .18) for n in names}
    def hgt(x, y):
        u = (x - (MX + MW / 2)) / (MW * .46); v = (y - (MY + MH / 2)) / (MH * .46)
        return .55 * (1 - min(1, math.hypot(u, v))) + .45 * fbm(x / 95, y / 95, 9)

    # wobbly shared edges
    epoly = {}
    def wig(a, b, amp, depth):
        r = random.Random(a * 100003 + b); P = [verts[a], verts[b]]; f = amp
        for _ in range(depth):
            N = [P[0]]
            for p, q in zip(P, P[1:]):
                dx, dy = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dy)
                off = max(-.28, min(.28, r.gauss(0, 1) * f)) * L
                N.append(((p[0] + q[0]) / 2 - dy / L * off, (p[1] + q[1]) / 2 + dx / L * off)); N.append(q)
            P = N; f *= .62
        return P
    def edge(key, coast):
        if key not in epoly: epoly[key] = wig(key[0], key[1], .30 if coast else .18, 4 if coast else 2)
        return epoly[key]
    def ordered(a, b, coast):
        p = edge((min(a, b), max(a, b)), coast); return p if a < b else p[::-1]
    kinds = {}
    for key, cs in edgecells.items():
        L = [c for c in cs if c in land]
        if not L: continue
        if len(L) == 1: kinds[key] = ("coast", own[L[0]])
        else:
            a, b = own[L[0]], own[L[1]]; kinds[key] = ("inner" if a == b else "border", (a, b))
    def pcell(i):
        ids = cv[i]; P = []
        for k in range(len(ids)):
            a, b = ids[k], ids[(k + 1) % len(ids)]
            if a == b: continue
            seg = ordered(a, b, kinds.get((min(a, b), max(a, b)), ("x",))[0] == "coast"); P.extend(seg if not P else seg[1:])
        return P
    cellP = {i: pcell(i) for i in land}
    coast_d, border_d, inner_d, glow = [], [], [], defaultdict(list)
    for key, (kd, info) in kinds.items():
        d = fmt(edge(key, kd == "coast"))
        if kd == "coast": coast_d.append(d); glow[info].append(d)
        elif kd == "border": border_d.append(d); glow[info[0]].append(d); glow[info[1]].append(d)
        else: inner_d.append(d)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">',
         '<title id="t">A living map of my GitHub projects</title>']
    top = ", ".join(f'{r["name"]} {r["commits"]}' for r in repos[:6])
    o.append(f'<desc id="d">Each public repository is a country sized by my commit count and coloured by language. Most commits: {top}.</desc>')
    o.append(f"<style>{font_css()}</style>")
    defs = ["<defs>", '<radialGradient id="sea" cx="50%" cy="50%" r="75%"><stop offset="0" stop-color="#3a7092"/><stop offset="1" stop-color="#1b3f56"/></radialGradient>',
            '<pattern id="w" width="26" height="16" patternUnits="userSpaceOnUse"><path d="M2 9 q6 -5 11 0 t11 0" fill="none" stroke="#fff" stroke-opacity=".06" stroke-width="1.2"/></pattern>',
            '<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#232c42"/><stop offset="1" stop-color="#161c2c"/></linearGradient>',
            '<linearGradient id="paper" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3ead2"/><stop offset="1" stop-color="#e8dcbd"/></linearGradient>',
            '<radialGradient id="vig" cx="50%" cy="50%" r="72%"><stop offset=".62" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".4"/></radialGradient>',
            f'<clipPath id="mapclip"><rect x="{MX}" y="{MY}" width="{MW}" height="{MH}" rx="3"/></clipPath>']
    cid = {n: f"k{j}" for j, n in enumerate(names)}
    for i in sorted(land): defs.append(f'<path id="p{i}" d="{fmt(cellP[i])}Z"/>')
    for n, cl in byc.items(): defs.append(f'<clipPath id="c_{cid[n]}">' + "".join(f'<use href="#p{i}"/>' for i in cl) + "</clipPath>")
    for n, ds in glow.items(): defs.append(f'<path id="g_{cid[n]}" d="{" ".join(ds)}"/>')
    defs.append("</defs>"); o.append("".join(defs))
    o.append(f'<rect width="{W}" height="{H}" rx="10" fill="#10151f"/><g clip-path="url(#mapclip)">')
    o.append(f'<rect x="{MX}" y="{MY}" width="{MW}" height="{MH}" fill="url(#sea)"/><rect x="{MX}" y="{MY}" width="{MW}" height="{MH}" fill="url(#w)"/>')
    cd = " ".join(coast_d)
    for wdt, op in ((30, .07), (22, .09), (15, .12), (9, .16), (4, .22)):
        o.append(f'<path d="{cd}" fill="none" stroke="#9fd0e2" stroke-opacity="{op}" stroke-width="{wdt}" stroke-linecap="round" stroke-linejoin="round"/>')
    for i in sorted(land):
        c = tint(COL[own[i]], (hgt(*pts[i]) - .5) * .30 + rng.uniform(-.035, .035))
        o.append(f'<use href="#p{i}" fill="{c}" stroke="{c}" stroke-width=".9" stroke-linejoin="round"/>')
    for i in sorted(land, key=lambda i: -hgt(*pts[i]))[:20]:
        x, y = pts[i]
        for dx, dy, s in ((-4, 3, .65), (2, 1, .9), (7, 4, .55)):
            px, py = x + dx, y + dy
            o.append(f'<path d="M{px - 6 * s:.1f} {py + 4 * s:.1f} L{px:.1f} {py - 7 * s:.1f} L{px + 6 * s:.1f} {py + 4 * s:.1f}Z" fill="{INK}" fill-opacity=".24"/>'
                     f'<path d="M{px:.1f} {py - 7 * s:.1f} L{px + 6 * s:.1f} {py + 4 * s:.1f} L{px + 1.5 * s:.1f} {py + 4 * s:.1f}Z" fill="#000" fill-opacity=".22"/>')
    for i in sorted(land):
        x, y = pts[i]
        if fbm(x / 60, y / 60, 31) > .63 and hgt(x, y) < .62:
            for _ in range(3):
                a = rng.uniform(0, 6.28); r = rng.uniform(1, 9)
                o.append(f'<circle cx="{x + math.cos(a) * r:.1f}" cy="{y + math.sin(a) * r:.1f}" r="2.1" fill="#1f4a2c" fill-opacity=".30"/>')
    o.append(f'<path d="{" ".join(inner_d)}" fill="none" stroke="{INK}" stroke-opacity=".20" stroke-width=".8" stroke-linejoin="round"/>')
    for n in glow:
        o.append(f'<g clip-path="url(#c_{cid[n]})" fill="none" stroke-linejoin="round" stroke-linecap="round">'
                 f'<use href="#g_{cid[n]}" stroke="{tint(COL[n], .38)}" stroke-opacity=".55" stroke-width="11"/>'
                 f'<use href="#g_{cid[n]}" stroke="{tint(COL[n], .55)}" stroke-opacity=".55" stroke-width="4.5"/></g>')
    o.append(f'<path d="{" ".join(border_d)}" fill="none" stroke="{INK}" stroke-opacity=".88" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')
    o.append(f'<path d="{cd}" fill="none" stroke="{INK}" stroke-opacity=".92" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>')

    # rivers: walk downhill along province borders
    vadj = defaultdict(set); coastv = set()
    for key, (kd, _) in kinds.items():
        vadj[key[0]].add(key[1]); vadj[key[1]].add(key[0])
        if kd == "coast": coastv.update(key)
    vh = {v: hgt(*verts[v]) for v in vadj}
    rivers, used = [], set()
    for s in sorted((v for v in vadj if v not in coastv), key=lambda v: -vh[v])[:400]:
        if len(rivers) >= 5: break
        if any(math.dist(verts[s], verts[u]) < 115 for u, _ in rivers): continue
        path, seen, cur, ok = [s], {s}, s, False
        while True:
            nb = [n for n in vadj[cur] if n not in seen and n not in used]
            if not nb: break
            n = min(nb, key=lambda z: vh[z] + rng.uniform(0, .01))
            if vh[n] > vh[cur] + .002: break
            path.append(n); seen.add(n); cur = n
            if n in coastv: ok = True; break
        if ok and len(path) >= 7: rivers.append((s, path)); used.update(path)
    for _, path in rivers:
        P = []
        for a, b in zip(path, path[1:]):
            seg = ordered(a, b, kinds[(min(a, b), max(a, b))][0] == "coast"); P.extend(seg if not P else seg[1:])
        d = fmt(P)
        o.append(f'<path d="{d}" fill="none" stroke="#2c6a8a" stroke-opacity=".55" stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round"/>'
                 f'<path d="{d}" fill="none" stroke="#8fd0e6" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>')
    o.append(f'<rect x="{MX}" y="{MY}" width="{MW}" height="{MH}" fill="url(#vig)"/></g>')

    # labels bend along each big country's shape
    def fitlabel(k):
        C = [pts[i] for i in byc[k]]; n = len(C)
        mx = sum(p[0] for p in C) / n; my = sum(p[1] for p in C) / n
        sxx = sum((p[0] - mx) ** 2 for p in C) / n; syy = sum((p[1] - my) ** 2 for p in C) / n; sxy = sum((p[0] - mx) * (p[1] - my) for p in C) / n
        th = max(-.22, min(.22, .5 * math.atan2(2 * sxy, sxx - syy)))
        e1 = (math.cos(th), math.sin(th)); e2 = (-e1[1], e1[0])
        U = [((p[0] - mx) * e1[0] + (p[1] - my) * e1[1], (p[0] - mx) * e2[0] + (p[1] - my) * e2[1]) for p in C]
        us = sorted(u for u, _ in U); lo = us[int(.07 * n)]; hi = us[max(int(.93 * n) - 1, 0)]
        S = [sum(u ** j for u, _ in U) for j in range(5)]; T = [sum(v * u ** j for u, v in U) for j in range(3)]
        A = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]]
        det = lambda m: (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
        D = det(A); co = []
        for j in range(3):
            Aj = [r[:] for r in A]
            for r in range(3): Aj[r][j] = T[r]
            co.append(det(Aj) / D if D else 0)
        return mx, my, e1, e2, lo, hi, max(-.004, min(.004, co[2])), math.sqrt(syy)
    labels = {}
    for k in names:
        if len(byc[k]) < 9: continue
        mx, my, e1, e2, lo, hi, c, sy = fitlabel(k)
        text = k.upper(); L = len(text); ext = hi - lo
        fs = min(25, .84 * ext / (L * .95))
        if fs < (9 if size[k] >= 20 else 11): continue
        my -= sy * (.45 if size[k] > 40 else .15)
        ls = fs * (.24 if L < 9 else .13); ln = L * (fs * .68 + ls); u0 = (lo + hi) / 2 - ln / 2
        P = []
        for t in range(25):
            u = u0 + ln * t / 24; v = c * (u - (lo + hi) / 2) ** 2
            P.append((mx + u * e1[0] + v * e2[0], my + u * e1[1] + v * e2[1]))
        labels[k] = dict(P=P, fs=fs, ls=ls, text=text, sy=sy)
    caps = {}
    for k in names:
        C = [pts[i] for i in byc[k]]; cx_ = sum(p[0] for p in C) / len(C); cy_ = sum(p[1] for p in C) / len(C)
        if k in labels: cx_, cy_ = labels[k]["P"][12][0], labels[k]["P"][12][1] + labels[k]["fs"] * .6 + 34 + labels[k]["sy"] * .5
        caps[k] = pts[min(byc[k], key=lambda i: (pts[i][0] - cx_) ** 2 + (pts[i][1] - cy_) ** 2)]

    # railway through the four repos I pushed to most recently
    recent = [r["name"] for r in sorted(data["repos"], key=lambda r: r["pushed"], reverse=True)[:3]]
    rp = [caps[k] for k in recent]
    if len(rp) >= 2:
        rd = "M" + " L".join(f"{x:.0f} {y:.0f}" for x, y in rp)
        o.append(f'<path d="{rd}" fill="none" stroke="{CREAM}" stroke-width="5.5" stroke-opacity=".95" stroke-linejoin="round" stroke-linecap="round"/>'
                 f'<path d="{rd}" fill="none" stroke="{INK}" stroke-width="2.4" stroke-dasharray="8 6" stroke-linejoin="round"/>')
        j = 1 if len(rp) > 2 else 0
        tx, ty = (rp[j][0] + rp[j + 1][0]) / 2, (rp[j][1] + rp[j + 1][1]) / 2
        ang = math.degrees(math.atan2(rp[j + 1][1] - rp[j][1], rp[j + 1][0] - rp[j][0]))
        o.append(f'<g transform="translate({tx:.0f} {ty:.0f}) rotate({ang:.0f})"><rect x="-22" y="-16" width="28" height="12" rx="3" fill="#c8553d" stroke="{INK}" stroke-width="1.8"/><rect x="-18" y="-13" width="8" height="5" fill="{CREAM}"/><rect x="8" y="-15" width="20" height="11" rx="2" fill="{CREAM}" stroke="{INK}" stroke-width="1.8"/>'
                 + "".join(f'<circle cx="{cx}" cy="-3" r="3" fill="{INK}"/>' for cx in (-14, -2, 14, 24)) + "</g>")
    for k in names:
        x, y = caps[k]; s = 1 if size[k] >= 12 else .75
        o.append(f'<g transform="translate({x:.0f} {y:.0f}) scale({s})"><path d="M-8 6 V-8 h3 v-3 h3.3 v3 h3.4 v-3 h3.3 v3 h3 V6Z" fill="{CREAM}" stroke="{INK}" stroke-width="1.8" stroke-linejoin="round"/><path d="M-2 6 v-6 a2 2 0 0 1 4 0 v6" fill="{INK}"/></g>')
    for i, (k, l) in enumerate(labels.items()):
        o.append(f'<path id="a{i}" d="{fmt(l["P"])}" fill="none"/>')
        st = f'font-family="{SERIF}" font-weight="700" font-size="{l["fs"]:.1f}" letter-spacing="{l["ls"]:.1f}" text-anchor="middle"'
        o.append(f'<text {st} fill="none" stroke="{CREAM}" stroke-opacity=".65" stroke-width="4" stroke-linejoin="round"><textPath href="#a{i}" startOffset="50%">{l["text"]}</textPath></text>')
        o.append(f'<text {st} fill="{INK}"><textPath href="#a{i}" startOffset="50%">{l["text"]}</textPath></text>')
    for r in repos:                                   # flags = commits pushed in the last 7 days
        if r["week"] > 0:
            x, y = caps[r["name"]]; x += 14; y -= 14
            o.append(f'<g transform="translate({x:.0f} {y:.0f})"><rect x="-3" y="-20" width="2.6" height="22" fill="{INK}"/><rect x="-0.4" y="-20" width="19" height="13" rx="1.5" fill="{CREAM}" stroke="{INK}" stroke-width="1.5"/><text x="9.2" y="-10" text-anchor="middle" font-family="{SANS}" font-size="9" font-weight="600" fill="{INK}">{r["week"]}</text></g>')
    cx, cy = MX + MW - 40, MY + MH - 40
    o.append(f'<g><circle cx="{cx}" cy="{cy}" r="26" fill="#10151f" fill-opacity=".65" stroke="{GOLD}" stroke-width="1.5"/><path d="M{cx} {cy - 21} L{cx + 5.5} {cy} L{cx} {cy + 21} L{cx - 5.5} {cy} Z" fill="{CREAM}"/><path d="M{cx - 21} {cy} L{cx} {cy - 5.5} L{cx + 21} {cy} L{cx} {cy + 5.5} Z" fill="{CREAM}" fill-opacity=".45"/><text x="{cx}" y="{cy - 30}" text-anchor="middle" font-family="{SERIF}" font-weight="700" font-size="11" fill="{CREAM}">N</text></g>')
    o.append(f'<rect x="{MX}" y="{MY}" width="{MW}" height="{MH}" rx="3" fill="none" stroke="{GOLD}" stroke-width="3"/>')

    # top bar
    top_n = max(data["repos"], key=lambda r: r["pushed"])["name"]
    o.append(f'<rect x="0" y="0" width="{W}" height="58" rx="10" fill="url(#bar)"/><rect x="0" y="54" width="{W}" height="4" fill="{GOLD}"/><rect x="0" y="54" width="{W}" height="1.2" fill="#fff" fill-opacity=".25"/>')
    crest = [barcol(n) for n in names[:4]]
    o.append(f'<g transform="translate(22 8)"><path d="M0 0 h36 v27 q0 13 -18 19 q-18 -6 -18 -19Z" fill="{crest[0]}" stroke="{GOLD}" stroke-width="2.5"/><path d="M1.2 12 h33.6 v8 h-33.6Z" fill="{crest[1]}"/><path d="M1.2 20 h33.6 v8 q0 1 -.2 2 h-33.2 q-.2 -1 -.2 -2Z" fill="{crest[2]}"/><path d="M5 38 q13 6 26 0 q-3 7 -13 10 q-10 -3 -13 -10Z" fill="{crest[3]}"/></g>')
    o.append(f'<text x="74" y="27" font-family="{SERIF}" font-weight="700" font-size="20" fill="{CREAM}">Gijs</text><text x="74" y="45" font-family="{SERIF}" font-style="italic" font-size="12" fill="{CREAM}" fill-opacity=".7">Middelburg, student of software</text>')
    def stat(x, label, val):
        o.append(f'<text x="{x}" y="26" text-anchor="middle" font-family="{SANS}" font-weight="600" font-size="19" fill="#f3d36b">{val}</text><text x="{x}" y="43" text-anchor="middle" font-family="{SANS}" font-size="11" fill="{CREAM}" fill-opacity=".72">{label}</text>')
    stat(590, "Public repos", len(repos)); stat(720, "Commits", sum(r["commits"] for r in repos)); stat(850, "This week", data["week"])

    # ledger
    LX, LY, LW, LH = 680, 72, 260, 468
    o.append(f'<rect x="{LX}" y="{LY}" width="{LW}" height="{LH}" rx="4" fill="url(#paper)" stroke="{GOLD}" stroke-width="3"/>')
    o.append(f'<text x="{LX + 20}" y="{LY + 34}" font-family="{SERIF}" font-weight="700" font-size="19" fill="{INK}">Projects</text><text x="{LX + 20}" y="{LY + 52}" font-family="{SANS}" font-size="11.5" fill="{INK}" fill-opacity=".62">Commits by me on GitHub</text>')
    o.append(f'<line x1="{LX + 20}" y1="{LY + 64}" x2="{LX + LW - 20}" y2="{LY + 64}" stroke="{INK}" stroke-opacity=".18"/>')
    y = LY + 96; BW = LW - 40; BH = 7; R = 3.5; mxc = max(1, repos[0]["commits"])
    for r in repos[:5]:
        n = r["commits"]; x0 = LX + 20; x1 = x0 + BW * n / mxc; yy = y + 8
        o.append(f'<text x="{x0}" y="{y}" font-family="{SANS}" font-size="13.5" font-weight="600" fill="{INK}">{r["name"]}</text><text x="{LX + LW - 20}" y="{y}" text-anchor="end" font-family="{SANS}" font-size="13.5" font-weight="600" fill="{INK}">{n}</text>')
        o.append(f'<rect x="{x0}" y="{yy}" width="{BW}" height="{BH}" fill="{INK}" fill-opacity=".08"/>')
        o.append(f'<path d="M{x0} {yy} H{x1 - R:.1f} Q{x1:.1f} {yy} {x1:.1f} {yy + R} Q{x1:.1f} {yy + BH} {x1 - R:.1f} {yy + BH} H{x0} Z" fill="{barcol(r["name"])}"/>')
        sub = " · ".join(filter(None, [r["lang"], "fork" if r["fork"] else None, f'pushed {datetime.fromisoformat(r["pushed"].replace("Z", "+00:00")).strftime("%-d %b")}']))
        o.append(f'<text x="{x0}" y="{y + 34}" font-family="{SANS}" font-size="11.5" fill="{INK}" fill-opacity=".7">{sub}</text>')
        y += 66
    o.append(f'<text x="{LX + 20}" y="{LY + LH - 34}" font-family="{SANS}" font-size="11" fill="{INK}" fill-opacity=".6">Bar colours match the countries on the map.</text>')
    o.append(f'<text x="{LX + 20}" y="{LY + LH - 14}" font-family="{SANS}" font-size="10.5" fill="{INK}" fill-opacity=".55">Updated {now.strftime("%-d %b %Y, %H:%M")} UTC</text>')
    o.append("</svg>")
    return "\n".join(o)

def stamp_free(svg):
    return re.sub(r"Updated [^<]*", "", svg)

if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    svg = render(load())
    # Only touch the file when the map itself changed, so the nightly commit stays quiet.
    if OUT.exists() and stamp_free(OUT.read_text()) == stamp_free(svg):
        print("map unchanged")
    else:
        OUT.write_text(svg)
        print("wrote", OUT, OUT.stat().st_size // 1024, "KB")
