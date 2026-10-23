"""Refresh Worlds Scout data: stats + series (gol.gg), Elo, photos/logos + schedule (lolesports), champion art (Data Dragon).

Usage: python pipeline/refresh.py            # refetch live pages, reuse cached history + images
       python pipeline/refresh.py --offline  # rebuild from cache only
Writes data/worlds.json.
"""
import base64, datetime as dt, html as H, io, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"; CACHE.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "data" / "worlds.json"
OFFLINE = "--offline" in sys.argv
UA = {"User-Agent": "Mozilla/5.0 (WorldsScout fan project)"}
LOL_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"  # public key the lolesports.com site itself ships
WORLDS_LEAGUE = "98767975604431411"
TODAY = dt.date.today()

# id on gol.gg, name on gol.gg, short tag, region, lolesports slug, lolesports code
TEAMS = [
    (2848, "Anyone s Legend", "AL", "LPL", "anyones-legend", "AL"), (2849, "Bilibili Gaming", "BLG", "LPL", "bilibili-gaming", "BLG"),
    (2852, "Top Esports", "TES", "LPL", "top-esports", "TES"), (2850, "Invictus Gaming", "IG", "LPL", "invictus-gaming", "IG"),
    (2804, "Gen.G", "GEN", "LCK", "geng", "GEN"), (2805, "Hanwha Life Esports", "HLE", "LCK", "hanwha-life-esports", "HLE"),
    (2809, "T1", "T1", "LCK", "t1", "T1"), (2802, "Dplus KIA", "DK", "LCK", "dwg-kia", "DK"),
    (2897, "G2 Esports", "G2", "LEC", "g2-esports", "G2"), (2900, "Movistar KOI", "MKOI", "LEC", "mad-lions", "MKOI"),
    (2899, "Karmine Corp", "KC", "LEC", "karmine-corp", "KC"), (2813, "Team Liquid", "TL", "LCS", "team-liquid", "TLAW"),
    (2954, "LYON", "LYON", "LCS", "lyon-gaming", "LYON"), (2887, "Team Secret Whales", "TSW", "LCP", "team-secret-whales", "TSW"),
    (2880, "CTBC Flying Oyster", "CFO", "LCP", "ctbc-flying-oyster", "CFO"), (2895, "Los Grandes", "LOS", "CBLOL", "los", "LOS"),
]
DISPLAY = {"Anyone s Legend": "Anyone's Legend", "Los Grandes": "LOS"}
TOURNAMENTS = re.compile(r"^(LCK 2026|LCK Cup 2026|LPL 2026|LEC 2026|LCS 2026|LCP 2026|CBLOL 2026|CBLOL Cup 2026|MSI 2026|2026 First Stand|"
                         r"Esports World Cup 2026|Worlds 2026|Americas Cup 2026|Demacia Cup|KeSPA Cup 2026|EWC 2026|2026 World Star)")
INTL = re.compile(r"MSI|First Stand|Esports World Cup|Worlds|KeSPA|EWC|Demacia|World Star|Americas Cup")
ELO_PRIOR = [("LCK", 1600), ("LPL", 1600), ("LEC", 1500), ("LCS", 1440), ("LCP", 1440), ("CBLOL", 1400)]

def fetch(url, cache_name=None, fresh=False, data=None, headers=None):
    p = CACHE / cache_name if cache_name else None
    if p and p.exists() and (OFFLINE or not fresh):
        return p.read_bytes()
    if OFFLINE:
        raise SystemExit(f"offline and not cached: {url}")
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    for attempt in range(3):
        try:
            body = urllib.request.urlopen(req, timeout=60).read(); break
        except Exception:
            if attempt == 2: raise
            time.sleep(3 * (attempt + 1))
    if p: p.write_bytes(body)
    time.sleep(0.6)
    return body

text = lambda b: b.decode("utf-8", "replace")
def strip(h):
    h = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", h))).replace("\xa0", " ")
def num(s):
    try: return float(s.replace("%", "").replace("+", "").strip())
    except (ValueError, AttributeError): return None
def webp(raw, size, square_top=False, quality=78, rgb=False):
    im = Image.open(io.BytesIO(raw)).convert("RGB" if rgb else "RGBA")
    if square_top:
        w, h = im.size; s = min(w, h); im = im.crop(((w - s) // 2, 0, (w - s) // 2 + s, s))
    im.thumbnail(size if isinstance(size, tuple) else (size, size), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(b.getvalue()).decode()
norm = lambda s: "".join(c for c in s.lower() if c.isalnum())
lol = lambda path: json.loads(text(fetch(f"https://esports-api.lolesports.com/persisted/gw/{path}", headers={"x-api-key": LOL_KEY})))

prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
prev_players = {p["id"]: p for t in prev.get("teams", []) for p in t["roster"]}
prev_teams = {t["short"]: t for t in prev.get("teams", [])}

# ---- tournaments and season player stats (gol.gg)
trlist = json.loads(text(fetch("https://gol.gg/tournament/ajax.trlist.php", "trlist.json", fresh=True, data=b"season=S16&league=")))
ph = text(fetch("https://gol.gg/players/list/season-S16/split-ALL/tournament-ALL/", "players.html", fresh=True))
PKEYS = ["country","games","wr","kda","k","d","a","csm","gpm","kp","dmg","gold","vs","dpm","vspm","wpm","wcpm","vwpm","gd15","csd15","xpd15","fb","fbv","penta","solo"]
pstats = {}
for m in re.finditer(r"<tr><td><a href='\./player-stats/(\d+)/[^']*' title='[^']*'>([^<]+)</a></td>(.*?)</tr>", ph, re.S):
    cells = [strip(c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(3), re.S)]
    if len(cells) >= 24:
        pstats[m.group(1)] = {k: (cells[i] if k == "country" else num(cells[i])) for i, k in enumerate(PKEYS) if i < len(cells)}

# ---- teams, rosters, photos
api_teams = {t["slug"]: t for t in lol("getTeams?hl=en-US")["data"]["teams"]} if not OFFLINE else \
            {t["slug"]: t for t in json.loads((CACHE / "allteams.json").read_text(encoding="utf-8"))["data"]["teams"]}
out = {"teams": [], "series": [], "generated": TODAY.isoformat()}
for tid, name, short, region, slug, code in TEAMS:
    h = text(fetch(f"https://gol.gg/teams/team-stats/{tid}/split-ALL/tournament-ALL/", f"team_{tid}.html", fresh=True))
    t = strip(h)
    grab = lambda label: (lambda m: num(m.group(1)) if m else None)(re.search(re.escape(label) + r"\s*:?\s*([+\-]?[\d.]+)%?", t))
    team = {"id": tid, "name": DISPLAY.get(name, name), "gol": name, "short": short, "code": code, "region": region,
            "gpm": grab("Gold Per Minute:"), "gdm": grab("Gold Differential per Minute:"), "gd15": grab("Gold Differential at 15 min:"),
            "ahead15": grab("Win Rate when ahead at 15 min:"), "ft": grab("First Tower :"), "dpm": grab("Damage Per Minute:"),
            "fbPct": grab("First Blood:"), "kpg": grab("Kills Per Game:"), "dpg": grab("Deaths Per Game:"),
            "drag": grab("Dragons / game:"), "baron": grab("Nashors / game:"), "grubs": grab("Voidgrubs / game:"),
            "vspm": grab("Vision Score Per Minute:")}
    m = re.search(r"Average game duration\s*:\s*([\d:]+)", t); team["dur"] = m.group(1) if m else None
    m = re.search(r"Win Rate\s*:\s*(\d+)W\s*-\s*(\d+)L\s*([\d.]+)%", t)
    if m: team["w"], team["l"], team["wr"] = int(m.group(1)), int(m.group(2)), num(m.group(3))
    at = api_teams[slug]
    pt = prev_teams.get(short)
    team["logo"] = pt["logo"] if pt and "logo" in pt else webp(fetch(at["image"].replace("http://", "https://"), f"logo_{short}.png"), 160)
    byname = {norm(p["summonerName"]): p for p in at["players"]}
    i = h.find("player's stats</caption>")
    roster, sub = [], False
    for row in re.findall(r"<tr>(.*?)</tr>", h[i:h.find("</table>", i)], re.S):
        if "Subs" in row and "colspan" in row: sub = True; continue
        pm, rm = re.search(r"player-stats/(\d+)/[^']*'>([^<]+)</a>", row), re.search(r"role/(\w+)\.png", row)
        if sub or not pm or not rm: continue
        champs = [{"c": c, "wr": num(w), "kda": num(k) if k != "-" else None, "g": int(g)}
                  for c, w, k, g in re.findall(r"<strong>([^<]+)</strong><br/>\s*Winrate : ([\d.]+)%<br/>\s*KDA : ([\d.\-]+)\s*</span>\s*</a><br/>\s*(\d+)", row)]
        p = {"id": pm.group(1), "name": H.unescape(pm.group(2)), "role": rm.group(1), "champs": champs[:8]}
        p.update(pstats.get(p["id"], {}))
        old = prev_players.get(p["id"])
        ap = byname.get(norm(p["name"]))
        if old and old.get("img"):
            p["img"], p["real"] = old["img"], old.get("real")
        elif ap and "default-headshot" not in ap["image"]:
            p["img"] = webp(fetch(ap["image"].replace("http://", "https://"), f"face_{p['id']}.png"), 220, square_top=True)
            p["real"] = f'{ap.get("firstName", "")} {ap.get("lastName", "")}'.strip() or None
        roster.append(p)
    team["roster"] = roster
    out["teams"].append(team)
    print(short, team.get("w"), team.get("l"), [p["name"] for p in roster], flush=True)

# ---- series: refetch tournaments that are still running, reuse finished ones from cache
names = {t[1] for t in TEAMS}
all_rows = []
SERIES_RE = (r"game/stats/(\d+)/page-(?:summary|game)/'[^>]*>[^<]*</a></td><td class='text-right[^']*'>([^<]+)</td><td class='text-center'>(\d+) - (\d+)</td>"
             r"<td class='[^']*'>([^<]+)</td><td class='text-center'>([^<]*)</td><td class='text-center'>[^<]*</td><td class='text-center'>([^<]*)</td>")
for tr in trlist:
    if not TOURNAMENTS.match(tr["trname"]): continue
    live = (TODAY - dt.date.fromisoformat(tr["lastgame"])).days < 3
    h = text(fetch("https://gol.gg/tournament/tournament-matchlist/" + urllib.parse.quote(tr["trname"]) + "/",
                   "ml_" + re.sub(r"\W", "_", tr["trname"]) + ".html", fresh=live))
    for gid, a, sa, sb, b, rnd, date in re.findall(SERIES_RE, h):
        a, b = H.unescape(a), H.unescape(b)
        row = {"g": int(gid), "a": a, "b": b, "sa": int(sa), "sb": int(sb), "t": tr["trname"], "r": rnd, "d": date}
        all_rows.append(row)
        if a in names or b in names: out["series"].append(row)

# ---- Elo: league priors, one chronological pass, international games weigh double
R = {}
for r in all_rows:
    for lg, v in ELO_PRIOR:
        if r["t"].startswith(lg + " "):
            R.setdefault(r["a"], v); R.setdefault(r["b"], v)
for r in sorted(all_rows, key=lambda r: (r["d"], r["g"])):
    ra, rb, K = R.get(r["a"], 1500), R.get(r["b"], 1500), 32 if INTL.search(r["t"]) else 16
    for won in [1] * r["sa"] + [0] * r["sb"]:
        e = 1 / (1 + 10 ** ((rb - ra) / 400)); ra += K * (won - e); rb -= K * (won - e)
    R[r["a"]], R[r["b"]] = ra, rb
for t in out["teams"]: t["elo"] = round(R.get(t["gol"], 1500))
out["seriesCount"] = f"{len({r['g'] for r in all_rows}):,}"

# ---- champion icons + signature splash (Data Dragon)
ver = json.loads(text(fetch("https://ddragon.leagueoflegends.com/api/versions.json", "dd_versions.json", fresh=True)))[0]
champs = json.loads(text(fetch(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json", f"dd_champions_{ver}.json")))["data"]
key = {norm(v["name"]): k for k, v in champs.items()}; key.update({norm(k): k for k in champs})
icons, splash = dict(prev.get("champIcons", {})), dict(prev.get("splash", {}))
for t in out["teams"]:
    for p in t["roster"]:
        for i, c in enumerate(p["champs"]):
            k = key.get(norm(c["c"]))
            if not k: continue
            if c["c"] not in icons:
                icons[c["c"]] = webp(fetch(f"https://ddragon.leagueoflegends.com/cdn/{ver}/img/champion/{k}.png", f"icon_{k}.png"), 64, rgb=True, quality=80)
            if i == 0 and c["c"] not in splash:
                splash[c["c"]] = webp(fetch(f"https://ddragon.leagueoflegends.com/cdn/img/champion/centered/{k}_0.jpg", f"splash_{k}.jpg"), (720, 405), rgb=True, quality=58)
used = {c["c"] for t in out["teams"] for p in t["roster"] for c in p["champs"]}
out["champIcons"] = {k: v for k, v in icons.items() if k in used}
out["splash"] = {k: v for k, v in splash.items() if k in used}

# ---- Worlds schedule + results (lolesports)
code2short = {t[5]: t[2] for t in TEAMS}
try:
    events = lol(f"getSchedule?hl=en-US&leagueId={WORLDS_LEAGUE}")["data"]["schedule"]["events"]
    sched = []
    for e in events:
        m = e.get("match") or {}
        ts = m.get("teams") or []
        if len(ts) != 2 or not e["startTime"].startswith("2026"): continue
        res = [(t.get("result") or {}) for t in ts]
        sched.append({"time": e["startTime"], "state": e["state"], "block": e.get("blockName") or "", "bo": (m.get("strategy") or {}).get("count", 1),
                      "a": code2short.get(ts[0]["code"], ts[0]["code"]), "b": code2short.get(ts[1]["code"], ts[1]["code"]),
                      "sa": res[0].get("gameWins"), "sb": res[1].get("gameWins"), "id": m.get("id")})
    out["schedule"] = sched
except Exception as e:  # schedule is a bonus; keep the last good copy
    print("schedule fetch failed:", e); out["schedule"] = prev.get("schedule", [])

OUT.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes), {len(out['series'])} series, {len(out['schedule'])} scheduled matches, Elo:",
      sorted(((t['short'], t['elo']) for t in out['teams']), key=lambda x: -x[1]))
