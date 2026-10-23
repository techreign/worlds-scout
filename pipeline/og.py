"""Render the 1200x630 share card to static/og.png with headless Chrome.

  python pipeline/og.py [chrome-path]
"""
import json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = sys.argv[1] if len(sys.argv) > 1 else r"C:\Program Files\Google\Chrome\Application\chrome.exe"
data = json.loads((ROOT / "data" / "worlds.json").read_text(encoding="utf-8"))
teams = {t["short"]: t for t in data["teams"]}

def pro(team, name):
    t = teams[team]
    return t, next(p for p in t["roster"] if p["name"] == name)

(ta, a), (tb, b) = pro("T1", "Faker"), pro("GEN", "Chovy")
side = lambda t, p, color, flip: f"""
  <div class="side" style="--c:{color}">
    <img class="splash" src="{data['splash'].get(p['champs'][0]['c'], '')}" style="{'transform:scaleX(-1)' if flip else ''}">
    <img class="face" src="{p['img']}"><div class="tag"><img src="{t['logo']}"><b>{p['name']}</b></div>
  </div>"""
html = f"""<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@1,900&family=Barlow:wght@600&display=swap">
<style>
html,body{{margin:0;width:1200px;height:630px;overflow:hidden;background:#070a14;font-family:Barlow,sans-serif;color:#fff}}
.wrap{{position:relative;width:1200px;height:630px;display:grid;grid-template-columns:1fr 1fr}}
.side{{position:relative;overflow:hidden;background:linear-gradient(180deg,transparent 40%,color-mix(in srgb,var(--c) 35%,transparent))}}
.splash{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.32;filter:saturate(1.2)}}
.side::after{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,#070a14 0%,transparent 35%,transparent 65%,#070a14 100%),linear-gradient(0deg,#070a14 5%,transparent 50%)}}
.face{{position:absolute;bottom:0;left:50%;transform:translateX(-50%);height:470px;z-index:1;filter:drop-shadow(0 0 40px color-mix(in srgb,var(--c) 70%,transparent))}}
.tag{{position:absolute;z-index:2;bottom:34px;left:0;right:0;display:flex;gap:12px;justify-content:center;align-items:center;font:italic 900 54px 'Barlow Condensed';text-transform:uppercase;text-shadow:0 4px 18px #000}}
.tag img{{height:46px}}
.vs{{position:absolute;z-index:3;left:50%;top:52%;transform:translate(-50%,-50%) skewX(-8deg);font:italic 900 170px/1 'Barlow Condensed';color:#f0c35b;text-shadow:0 0 50px rgba(240,195,91,.6),0 8px 0 #7a5410}}
.title{{position:absolute;z-index:3;top:28px;left:0;right:0;text-align:center;font:italic 900 64px/1 'Barlow Condensed';text-transform:uppercase;letter-spacing:.5px;text-shadow:0 4px 20px #000}}
.title b{{color:#f0c35b}}
.sub{{position:absolute;z-index:3;top:100px;left:0;right:0;text-align:center;font-size:24px;color:#c9d3f0;text-shadow:0 2px 10px #000}}
</style>
<div class="wrap">{side(ta, a, '#3d8bff', False)}{side(tb, b, '#ff4655', True)}
<div class="title">Worlds <b>2026</b> Scout</div><div class="sub">Pick every match · Face off any two pros · Guess the daily mystery pro</div>
<div class="vs">VS</div></div>"""

(ROOT / "static").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    page = Path(tmp) / "og.html"
    page.write_text(html, encoding="utf-8")
    out = ROOT / "static" / "og.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=4000",
                    "--window-size=1200,630", f"--screenshot={out}", page.as_uri()], check=True, capture_output=True)
print("wrote", out, out.stat().st_size, "bytes")
