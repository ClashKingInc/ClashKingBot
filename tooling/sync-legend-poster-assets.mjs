// Refresh the Worker's small, self-contained poster artwork from the
// authoritative local assets checkout. Does not publish or edit that checkout.
import { copyFileSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const source=resolve(process.argv[2]??join(root,'../clashking_assets'),'assets');
const target=join(root,'worker/src/assets/legend-poster');
mkdirSync(target,{recursive:true});
for(const [from,to] of [
 ['fonts/blogger.ttf','blogger.ttf'],['fonts/SCmagic.ttf','clash.ttf'],
 ['bot/icons/clash_sword.png','sword.png'],['bot/icons/shield.png','shield.png'],
 ['bot/icons/trophy.png','trophy.png'],['bot/icons/war_star.png','star.png'],
 ['bot/icons/heart.png','heart.png'],
 ['leagues/league-tier/legend_league.png','legend.png'],
 ['logos/crown-white-arrow-dark-bg/FjTEp708170921wcQnjjhKgCZNfLjaMO7uQy3lFnLiwcsjtNluf1CyZ3e7QtL.png','clashking.png'],
])copyFileSync(join(source,from),join(target,to));
execFileSync('sips',['-Z','256',join(target,'clashking.png')],{stdio:'ignore'});
// resvg accepts PNG/JPEG; convert WebP once during asset refresh, not per request.
for(let level=1;level<=18;level++)execFileSync('sips',['-s','format','png',join(source,`buildings/home-village/town_hall/level_${level}.webp`),'--out',join(target,`th${level}.png`)],{stdio:'ignore'});
// Optional original Fan Kit PNG, selected by the user; never fetch signed
// browser URLs or publish assets as a side effect of a local refresh.
if(process.argv[3])execFileSync('sips',['-Z','800',resolve(process.argv[3]),'--out',join(target,'league-prince.png')],{stdio:'ignore'});
console.log('Refreshed bundled Legend poster fonts and artwork; no assets published.');
