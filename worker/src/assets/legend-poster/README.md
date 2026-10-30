# Legend poster assets

These are runtime copies of assets from `clashking_assets/assets`, not a second
authoring source. Bundling keeps fonts and core artwork available without CDN
requests and lets the Worker render PNGs with no external image service.

- `blogger.ttf`: `fonts/blogger.ttf`
- `clash.ttf`: `fonts/SCmagic.ttf`
- Icons: `bot/icons/clash_sword.png`, `shield.png`, `trophy.png`, `war_star.png`
- Footer heart: `bot/icons/heart.png` (used instead of an unsupported font emoji).
- League: `leagues/league-tier/legend_league.png`
- Town Halls: `buildings/home-village/town_hall/level_1.webp` through `level_18.webp`, converted to PNG.
- `clashking.png`: `logos/crown-white-arrow-dark-bg/FjTEp708170921wcQnjjhKgCZNfLjaMO7uQy3lFnLiwcsjtNluf1CyZ3e7QtL.png`.
- `league-prince.png`: user-selected Supercell Fan Kit `league_prince_pose03`, asset 164945, resized to 800px from the public 2400px PNG at `https://media.ffycdn.net/eu/supercell/MJokfG3oe4vw3f8BRiRQ.png?width=2400`. Downloaded October 15, 2026. Optional original input is the sync script's third argument. The crown is resized to 256px; both exceed their displayed resolution without bundling full export sizes.

Refresh on macOS from the Bot checkout:

```sh
node tooling/sync-legend-poster-assets.mjs /path/to/clashking_assets
```

The script only copies into this directory and does not publish or modify the
source assets. The game artwork and fonts retain their original ownership.
No local-assets host or production asset release is required: these PNGs are
bundled in the local Bot renderer. Country flags, clan badges, and troop emoji
images are fetched from their existing allowlisted HTTPS hosts, with bounded
size/time and no followed redirects. Missing artwork does not block the reply.
