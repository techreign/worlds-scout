# Worlds 2026 Scout

A daily Worlds companion. Three tabs:

- **Today**: every match on the day with Elo win odds. Tap a team to lock your pick, and track your pick record and streak.
- **Face-off**: pick any two pros or teams and compare them: OVR ratings, radar, champion pools, lane stats, head-to-head meetings, recent form and Bo1/Bo3/Bo5 odds. Every matchup has its own link (`#p48-p123`, `#T1-GEN`).
- **Scout Daily**: a mystery-pro puzzle with a new answer each day, 8 guesses and a shareable result.

Picks, streaks and puzzle stats are saved in the browser's localStorage, so there's no backend.

## Layout

```
pipeline/refresh.py   scrape gol.gg + lolesports + Data Dragon -> data/worlds.json
pipeline/build.py     src/app.html + data -> dist/index.html (site) and dist/artifact.html (claude.ai)
pipeline/og.py        render static/og.png share card (needs local Chrome)
src/app.html          the whole app (HTML/CSS/JS, single source of truth)
site.json             optional site config (copy site.example.json)
```

## Run locally

```
pip install pillow
python pipeline/refresh.py     # ~40s; --offline rebuilds from data/cache only
python pipeline/build.py
start dist/index.html          # or any static server
```

## Deploy (GitHub Pages)

1. Create a repo and push to `main`.
2. Go to Settings → Pages → Source and choose **GitHub Actions**.
3. `.github/workflows/refresh.yml` runs every 3 hours, on push, and when started by hand. Each run:
   - refreshes the data
   - commits `data/worlds.json`
   - deploys `dist/`

   The first run has no page cache, so it fetches everything (about 70 requests). Later runs reuse the cache.
4. For a custom domain:
   - set `siteUrl` in `site.json` (the build writes `CNAME`)
   - point a DNS CNAME at `<user>.github.io`

Vercel and Netlify also work: either run the same two commands and serve `dist/`, or deploy the built `dist/` folder.

## Making money

All of these are off until you set them in `site.json`:

| Key | What it does |
| --- | --- |
| `kofi` | Shows the "Support the site" link in the top bar. A low-friction tip jar that suits a fan site. |
| `sponsor` | HTML for a sponsor strip under the app. Good to sell directly to gaming peripheral, VPN or coaching brands for the length of Worlds. |
| `adsenseClient` + `adsenseSlot` | One AdSense unit. Apply early, since approval takes days. |
| `plausibleDomain` | Privacy-friendly analytics. You need traffic numbers to sell the sponsor slot. |

How to grow traffic:

- Post daily Scout Daily share results on r/leagueoflegends and Discord servers.
- Post Face-off links for each day's big match on X and Reddit. Every link unfurls with `og.png`.

## Legal

This is a fan project under Riot's [Legal Jibber Jabber](https://www.riotgames.com/en/legal) policy. The disclaimer in the footer is required. Rules for monetization:

- Ads, tips and sponsors are allowed.
- Don't paywall Riot IP or stats.
- Don't add betting or gambling links. The odds are labeled "for fun".

Data comes from gol.gg, lolesports.com and Data Dragon. Keep the request rate low; `refresh.py` sleeps between requests.
