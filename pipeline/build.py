"""Build the single-file app.

  python pipeline/build.py            -> dist/index.html (public site, uses site.json) + dist/artifact.html (claude.ai artifact)
site.json (optional, next to this repo's README):
  {"siteUrl": "https://worldsscout.gg", "kofi": "https://ko-fi.com/you", "sponsor": "<a href=...>Sponsored by ...</a>",
   "plausibleDomain": "worldsscout.gg", "adsenseClient": "ca-pub-..."}
"""
import json, shutil, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data" / "worlds.json").read_text(encoding="utf-8"))
app = (ROOT / "src" / "app.html").read_text(encoding="utf-8")
cfg_path = ROOT / "site.json"
site = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
page = app.replace("__DATA__", blob)
(ROOT / "dist").mkdir(exist_ok=True)

# claude.ai artifact: the publish skeleton adds doctype/head; config defaults point at the artifact URL
(ROOT / "dist" / "artifact.html").write_text(page, encoding="utf-8")

# public site: full document with share previews, optional analytics/ads, and the site config
url = site.get("siteUrl", "")
title = "Worlds 2026 Scout: daily Worlds picks, pro face-offs and the Scout Daily puzzle"
desc = "Pick every Worlds 2026 match, face off any two pros or teams with real 2026 stats and Elo odds, and guess the daily mystery pro."
head = [
    '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
    f'<meta name="description" content="{desc}">',
    f'<meta property="og:title" content="Worlds 2026 Scout"><meta property="og:description" content="{desc}"><meta property="og:type" content="website">',
    f'<meta property="og:url" content="{url}"><meta property="og:image" content="{url.rstrip("/")}/og.png"><meta name="twitter:card" content="summary_large_image">' if url else "",
    '<link rel="icon" href="favicon.svg" type="image/svg+xml"><meta name="theme-color" content="#070a14">',
    f'<script defer data-domain="{site["plausibleDomain"]}" src="https://plausible.io/js/script.js"></script>' if site.get("plausibleDomain") else "",
    f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={site["adsenseClient"]}" crossorigin="anonymous"></script>' if site.get("adsenseClient") else "",
    "<script>window.SCOUT_CONFIG = " + json.dumps({k: site[k] for k in ("siteUrl", "kofi", "sponsor", "adsenseClient", "adsenseSlot") if k in site}) + ";</script>",
]
doc = ("<!doctype html><html lang=\"en\"><head>" + "".join(h for h in head if h) +
       "<style>html,body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>" + page + "</body></html>")
doc = doc.replace("<title>Worlds 2026 Scout</title>", f"<title>{title}</title>", 1)
(ROOT / "dist" / "index.html").write_text(doc, encoding="utf-8")
(ROOT / "dist" / "favicon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#070a14"/>'
    '<text x="32" y="44" text-anchor="middle" font-family="Impact,Arial Black,sans-serif" font-size="30" font-style="italic" fill="#f0c35b">VS</text></svg>', encoding="utf-8")
for f in (ROOT / "static").glob("*"):  # og.png etc.
    shutil.copy(f, ROOT / "dist" / f.name)
if url:  # custom domain for GitHub Pages
    host = urllib.parse.urlparse(url).netloc
    if not host.endswith("github.io"):
        (ROOT / "dist" / "CNAME").write_text(host, encoding="utf-8")
print("built", len(page), "bytes;", "site config:", sorted(site) or "none (artifact defaults)")
