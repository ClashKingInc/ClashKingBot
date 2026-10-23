// Signed local Bot interactions -> running local API -> imported PostgreSQL
// history and live player lookup. Intercept Discord delivery; never post there.
import {generateKeyPairSync,sign} from 'node:crypto';
import {inflateSync} from 'node:zlib';
import {writeFileSync} from 'node:fs';
import stringWidth from '../../worker/node_modules/string-width/index.js';
import {bundleWorker} from './bundle-worker.mjs';
import {createRequire} from 'node:module';
import {loadWorkspace} from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
const require=createRequire('/Users/matthewanderson/PycharmProjects/clashking_api/package.json');
const {Miniflare,convertV4MiniflareOptions}=require('miniflare');
const {Client}=require('pg');
const db=new Client({connectionString:'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev'});
await db.connect();
const actor='999999999999998003',guild='999999999999998001',verifiedTag='#PYLQGRC2',unverifiedTag='#PYLQGRC8';let ownsUser=false,ownsServer=false,ownsActivity=false;const contributionTimes=[],unicodeTags=[];
const workspace=loadWorkspace('/Users/matthewanderson/ClashKing');
if(workspace.env.TIMESCALE_HOST!=='127.0.0.1'||workspace.env.TIMESCALE_PORT!=='54330')throw Error('Only local workspace allowed');
const app=workspace.env.DISCORD_CLIENT_ID;
if(app!=='808566437199216691')throw Error('Expected Beta');
const inventoryResponse=await fetch(`https://discord.com/api/v10/applications/${app}/emojis`,{headers:{Authorization:`Bot ${workspace.env.DISCORD_BOT_TOKEN}`}});
if(!inventoryResponse.ok)throw Error('Could not read Beta emoji inventory');
const inventory=await inventoryResponse.json();
const {privateKey,publicKey}=generateKeyPairSync('ed25519');
const bundle=await bundleWorker();
const replies=new Map(),loadedAssetHosts=new Set();let counter=999999999999998100n;
const bot=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{
 name:'legend-history-local-e2e',...bundle,compatibilityDate:'2026-08-22',compatibilityFlags:['nodejs_compat'],
 bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://local-dash.clashk.ing',CLASHKING_API_BASE_URL:'http://127.0.0.1:8787',CLASHKING_API_TOKEN:workspace.env.API_BOT_TOKEN,CLASHOFSTATS_USER_AGENT:workspace.env.CLASHOFSTATS_USER_AGENT??'',DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:`${Buffer.from(app).toString('base64')}.local.token`,DISCORD_PUBLIC_KEY:publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex')},
 outboundService:async request=>{
  const url=new URL(request.url);
  if(url.hostname==='discord.com'){
   if(request.method==='GET'&&url.pathname.endsWith('/emojis'))return Response.json(inventory);
   if(!url.pathname.includes('/webhooks/'))throw Error('Unexpected Discord request');
   if(request.method==='DELETE')return new Response(null,{status:204});
   let payload;
   if(request.headers.get('content-type')?.startsWith('multipart/form-data')){
    const form=await request.formData();payload=JSON.parse(form.get('payload_json'));
    const file=form.get('files[0]');
    if(!file||file.type!=='image/png')throw Error('Expected a directly attached PNG');
    const bytes=new Uint8Array(await file.arrayBuffer());
    if(Buffer.from(bytes.subarray(0,8)).toString('hex')!=='89504e470d0a1a0a'||bytes.length>2_500_000)throw Error('Invalid or oversized chart');
    const image=Buffer.from(bytes);let offset=8;const compressed=[];
    while(offset<image.length){const length=image.readUInt32BE(offset);if(image.toString('ascii',offset+4,offset+8)==='IDAT')compressed.push(image.subarray(offset+8,offset+8+length));offset+=length+12;}
    const channels=image[25]===6?4:3;
    if(image.readUInt32BE(16)!==1600||image.readUInt32BE(20)!==1100||inflateSync(Buffer.concat(compressed)).length!==(1600*channels+1)*1100)throw Error('PNG dimensions or scanlines invalid');
    if(process.env.LEGEND_POSTER_OUTPUT)writeFileSync(process.env.LEGEND_POSTER_OUTPUT,bytes);
    payload.chartBytes=bytes.length;
   }else payload=await request.json();
   replies.set(url.pathname.split('/')[5],payload);return Response.json({id:'999999999999998999'});
  }
  if(request.method==='GET'&&['cdn.discordapp.com','api-assets.clashofclans.com','assets.clashk.ing'].includes(url.hostname)){
   const response=await fetch(request.url,{redirect:'manual'});if(response.ok)loadedAssetHosts.add(url.hostname);return response;
  }
  if(request.method==='GET'&&url.hostname==='api.clashofstats.com'&&url.pathname==='/players/2J8V28GV0/history/clans')return fetch(request.url,{headers:request.headers,redirect:'manual'});
  if(url.origin==='http://127.0.0.1:8787')return fetch(request.url,{method:request.method,headers:Object.fromEntries(request.headers),body:['GET','HEAD'].includes(request.method)?undefined:await request.arrayBuffer()});
  throw Error('Unexpected external request');
 },
}]}));
try{
 const seasonResponse=await fetch('http://127.0.0.1:8787/v2/player/%23LG8Q9QYR/legend/season',{headers:{Authorization:`Bearer ${workspace.env.API_BOT_TOKEN}`}});
 const realSeason=await seasonResponse.json();
 if(!seasonResponse.ok||!realSeason.favoriteTroops?.length||!realSeason.armyGroups?.length||!realSeason.rankPopulation)throw Error('Real season enrichment missing: '+JSON.stringify(realSeason));
 const favoriteCategories=['troop','spell','hero','equipment','pet','siege'];
 if(realSeason.favorites?.length!==6||!favoriteCategories.every(category=>realSeason.favorites.some(item=>item.category===category&&item.id>0&&item.name&&item.attacks>0)))throw Error('Six favorite categories missing');
 const armyRows=(await db.query(`SELECT c.* FROM battles_ranked b JOIN army_compositions c USING(share_code) WHERE b.player_tag='#LG8Q9QYR' AND b.battle_mode=2 AND b.direction=1 AND b.battle_time >= $1 AND b.battle_time < $2`,[realSeason.seasonStart,realSeason.seasonEnd])).rows;
 for(const favorite of realSeason.favorites){
  const contains={troop:row=>row.main_troops.some(item=>item.id===favorite.id),spell:row=>row.spells.some(item=>!item.clanCastle&&item.id===favorite.id),hero:row=>row.heroes.includes(favorite.id),equipment:row=>row.equipment.some(item=>item.equipmentId===favorite.id),pet:row=>row.pet_assignments.some(item=>item.petId===favorite.id),siege:row=>row.siege_machine_id===favorite.id};
  if(armyRows.filter(contains[favorite.category]).length!==favorite.attacks)throw Error('Favorite use count differs from stored armies: '+favorite.category);
 }
 const recorded=await db.query(`SELECT direction,stars,count(*)::int total FROM battles_ranked WHERE player_tag='#LG8Q9QYR' AND battle_mode=2 AND battle_time >= $1 AND battle_time < $2 GROUP BY direction,stars`,[realSeason.seasonStart,realSeason.seasonEnd]);
 for(const row of recorded.rows){const counts=row.direction===1?realSeason.stats.offenseStars:realSeason.stats.defenseStars;if(counts[['zero','one','two','three'][row.stars]]!==row.total)throw Error('Poster stars differ from stored battles');}
 if((await db.query('SELECT user_id FROM auth_users WHERE user_id=$1',[actor])).rowCount||(await db.query('SELECT tag FROM player_links WHERE tag=ANY($1::text[])',[[verifiedTag,unverifiedTag]])).rowCount)throw Error('Synthetic autocomplete records already exist');
 if((await db.query('SELECT id FROM servers WHERE id=$1',[guild])).rowCount)throw Error('Synthetic server already exists');
 await db.query("INSERT INTO servers(id,name,embed_color) VALUES($1,'Legend E2E','#123456')",[guild]);ownsServer=true;
 await db.query("INSERT INTO auth_users(user_id,provider) VALUES($1,'discord')",[actor]);ownsUser=true;
 await db.query("INSERT INTO player_links(tag,user_id,source,is_verified) VALUES($1,$3,'discord',true),($2,$3,'discord',false)",[verifiedTag,unverifiedTag,actor]);
 await db.query("INSERT INTO player_online_events(tag,clan_tag,seen_at) VALUES($1,'#PYLQGRC',now())",[verifiedTag]);ownsActivity=true;
 const identityUrl=`http://127.0.0.1:8787/v2/bot/players/${encodeURIComponent(verifiedTag)}/identity`;
 const identityRead=async suffix=>{const response=await fetch(identityUrl+suffix,{headers:{Authorization:`Bearer ${workspace.env.API_BOT_TOKEN}`}});if(!response.ok)throw Error('Identity route failed '+response.status);return response.json();};
 if((await fetch(identityUrl)).status!==401)throw Error('Identity endpoint is not bot-authenticated');
 if((await fetch(`http://127.0.0.1:8787/v2/bot/players/${encodeURIComponent(verifiedTag)}/clan-history`)).status!==401)throw Error('Clan timeline endpoint is not bot-authenticated');
 const withoutServer=await identityRead('');
 if(withoutServer.link!==null||!withoutServer.lastObservedAt)throw Error('Identity without a server exposed an owner or lost permitted activity');
 const absentMember=await identityRead(`?serverId=${guild}`);
 if(absentMember.link!==null)throw Error('Non-member ownership leaked');
 await db.query('UPDATE player_links SET hidden=true WHERE tag=$1',[verifiedTag]);
 const hidden=await identityRead(`?serverId=${guild}`);
 if(hidden.link!==null||!hidden.lastObservedAt)throw Error('Hidden account exposed its owner or lost permitted game activity');
 await db.query('UPDATE player_links SET hidden=false WHERE tag=$1',[verifiedTag]);
 for(const tag of ['#2J8V28GV0','#LG8Q9QYR',verifiedTag])await db.query("INSERT INTO user_bookmarks(user_id,entity_type,tag) VALUES($1,'player',$2)",[actor,tag]);
 const origin=new URL('/interactions',String(await bot.ready));
 async function interact(data){
  const token=String(counter++),body=JSON.stringify({id:token,application_id:app,guild_id:'999999999999998001',channel_id:'999999999999998002',member:{user:{id:'999999999999998003',username:'Local'},roles:[]},version:1,token,...data});
  const timestamp=String(Math.floor(Date.now()/1000));
  const response=await fetch(origin,{method:'POST',headers:{'Content-Type':'application/json','X-Signature-Timestamp':timestamp,'X-Signature-Ed25519':sign(null,Buffer.from(timestamp+body),privateKey).toString('hex')},body});
  const initial=await response.json();if(!response.ok)throw Error('Bot failed: '+response.status);
  if(![5,6].includes(initial.type))return initial.data;
  for(let attempt=0;attempt<200;attempt++){if(replies.has(token))return replies.get(token);await new Promise(resolve=>setTimeout(resolve,100));}
  throw Error('Deferred response timed out');
 }
 const command=await interact({type:2,data:{name:'legends',options:[{name:'history',type:1,options:[{name:'player',type:3,value:'#2J8V28GV0'}]}]}});
 const button=await interact({type:3,data:{custom_id:'legendhistory:#2J8V28GV0',component_type:2}});
 for(const reply of [command,button]){
  const embed=reply.embeds?.[0];
  if(embed?.color!==0x123456)throw Error('Server embed color was not applied');
  if(!embed?.author?.name.endsWith('Legend History')||!embed.author.icon_url||!embed.author.url)throw Error('Legacy author, Town Hall icon or player link missing: '+JSON.stringify(reply));
  if(!embed.description.includes('🏆= trophies, 🌎= global rank')||!embed.description.includes('[Open in ClashKing]'))throw Error('Legend or in-embed App link missing');
  if(!embed.fields.some(field=>field.name==='Previous Names'))throw Error('Previous names missing');
  const currentName=embed.author.name.replace(/ Legend History$/,'').trim();
  if(embed.fields.filter(field=>field.name==='Previous Names').some(field=>field.value.split(', ').includes(currentName)))throw Error('Current name included in previous names');
  if(!embed.description.includes('https://local-app.clashk.ing/player/'))throw Error('Beta App link points to production');
  if(!embed.fields.some(field=>field.name==='2025'&&field.value.includes('December')&&field.value.includes('5409')))throw Error('Year groups or date parsing incorrect');
  if((reply.components??[]).length)throw Error('Normal history should fit without bottom buttons');
  if(embed.fields.some(field=>field.value.length>1024)||embed.fields.length>25)throw Error('Discord limits exceeded');
 }
 if(JSON.stringify(command.embeds)!==JSON.stringify(button.embeds))throw Error('Slash and legacy button presentations differ');
 const limited=await interact({type:2,data:{name:'legends',options:[{name:'history',type:1,options:[{name:'player',type:3,value:'#2J8V28GV0'},{name:'limit',type:4,value:3}]}]}});
 const finishLines=limited.embeds[0].fields.filter(field=>field.name!=='Previous Names').flatMap(field=>field.value.trim().split('\n'));
 if(finishLines.length!==3)throw Error('History limit did not preserve exactly three season finishes');
 for(const [name,action] of [['legends','player'],['legends','history'],['ranked','player'],['ranked','history']]){
  const missing=await interact({type:2,data:{name,options:[{name:action,type:1}]}});
  if(!missing.content?.includes('Choose a player'))throw Error('Player is not mandatory for '+name+' '+action);
 }
 const choices=async action=>(await interact({type:4,data:{name:'legends',options:[{name:action,type:1,options:[{name:'player',type:3,value:'',focused:true}]}]}})).choices;
 const historyChoices=await choices('history');
 if(!historyChoices.some(choice=>choice.value==='#2J8V28GV0'&&/^\(TH18\) Magic Jr\. \| #2J8V28GV0$/.test(choice.name)))throw Error('Bookmarked player label is incorrect: '+JSON.stringify(historyChoices));
 if(historyChoices.filter(choice=>choice.value===verifiedTag).length!==1||historyChoices.some(choice=>choice.value===unverifiedTag))throw Error('Verified links, unverified exclusion or deduplication failed');
 const statsChoices=await choices('player');
 if(!statsChoices.some(choice=>choice.value==='#LG8Q9QYR')||statsChoices.some(choice=>choice.value===verifiedTag||choice.value===unverifiedTag||choice.value==='#2J8V28GV0'))throw Error('Stats did not restrict choices to current Legend players');
 const season=await interact({type:2,data:{name:'legends',options:[{name:'player',type:1,options:[{name:'player',type:3,value:'#LG8Q9QYR'}]}]}});
 const seasonEmbed=season.embeds?.[0];
 if(seasonEmbed?.title!=='Legend Day'||!seasonEmbed.thumbnail?.url||!seasonEmbed.author?.name.startsWith('Bladerslayer'))throw Error('Day identity missing: '+JSON.stringify(season));
 const validateLegend=reply=>{
  const embed=reply.embeds[0],text=[embed.description,...embed.fields.flatMap(f=>[f.name,f.value])].join('\n');
  if(embed.color!==0x123456||(embed.title==='Legend Day'&&!/^Day \d+\/\d+$/.test(embed.footer?.text))||text.includes('Season balance')||text.includes('triples conceded')||text.includes('Sep 28')||text.includes('Oct 15'))throw Error('Old sections or calendar dates remain');
  if(embed.title==='Legend Season'&&(!embed.footer?.text.includes(' – ')||!embed.footer.text.includes(String(new Date(realSeason.seasonEnd).getUTCFullYear()))||!embed.fields.slice(0,2).every(f=>/^(Attacks|Defenses) \(\d+\/\d+\)$/u.test(f.name)&&f.value.startsWith('-# **'))))throw Error('Season summary styling or date footer missing');
  if(embed.title==='Legend Season'){
   const elapsed=Number(seasonEmbed.footer.text.match(/\d+/u)[0]);
   const duration=Math.round((Date.parse(realSeason.seasonEnd)-Date.parse(realSeason.seasonStart))/86400000);
   const capacity=Math.min(elapsed,duration)*8;
   if(embed.fields[0].name!==`Attacks (${realSeason.stats.attacks}/${capacity})`||embed.fields[1].name!==`Defenses (${realSeason.stats.defenses}/${capacity})`)throw Error('Season capacity does not include all Legend days through today');
  }
  if(text.includes('Daily trophies'))throw Error('Unnecessary table heading remains');
  if(text.includes('automatic defenses estimated')||/[★☆]/u.test(text))throw Error('Removed battle stars or automatic explanation remain');
  if(text.includes('current trophies')||text.includes('Auto estimate')||embed.fields.some(f=>f.name==='Net trophies'))throw Error('Removed labels remain');
  if(embed.fields.filter(f=>/ Offense| Defense(?: |$)/u.test(f.name)).some(f=>f.value.split('\n').length!==2))throw Error('Summary still duplicates triple rates');
  if(embed.title==='Legend Day'&&(!embed.fields.some(f=>/^Attacks \(\d+\/8\)$/u.test(f.name))||!embed.fields.some(f=>/^Defenses \(\d+\/8\)$/u.test(f.name))))throw Error('Plain battle headers with counts missing');
  if(embed.title==='Legend Day'){
   const attackIndex=embed.fields.findIndex(f=>f.name.startsWith('Attacks ('));
   if(attackIndex!==0||!embed.fields[attackIndex+1]?.name.startsWith('Defenses (')||!embed.fields[attackIndex].inline||!embed.fields[attackIndex+1].inline||!embed.fields.slice(0,2).every(f=>/^-# \*\*[+-][\d,]+\*\* \([^)]+ average\)\n[^\n]/u.test(f.value)))throw Error('Compact subtext totals and battle lists are not a single inline pair');
  }
  const battleRows=embed.fields.filter(f=>/Attacks|Defenses/.test(f.name)).map(f=>f.value).join('\n');
  if(/<t:\d+:t>/u.test(battleRows)||(/<t:/u.test(battleRows)&&!/<t:\d+:R>/u.test(battleRows)))throw Error('Battle times are not relative');
  const armyField=embed.fields.find(f=>f.name==='Most used armies · season');
  if(embed.title==='Legend Day'&&armyField)throw Error('Season armies leaked into daily statistics');
  if(embed.title==='Legend Season'&&(!armyField||!realSeason.armyGroups[0].name.split(' / ').every(name=>armyField.value.includes(name))||!/<a?:\w+:\d+>/u.test(armyField.value)))throw Error('Season army summary or troop emojis missing');
  if(!embed.description.match(/<a?:\w+:\d+>/)||!embed.fields.filter(f=>/ Offense| Defense(?: |$)/u.test(f.name)).every(f=>/^<a?:\w+:\d+>/.test(f.name)))throw Error('Clash emojis missing');
  if(embed.title==='Legend Day'&&(!reply.chartBytes||embed.image?.url!=='attachment://legend-season.png'||reply.attachments?.length!==1))throw Error('Day chart attachment missing');
  if(embed.title==='Legend Season'&&(embed.image||reply.chartBytes||!Array.isArray(reply.attachments)||reply.attachments.length))throw Error('Season view retains a graphic');
  if(!embed.url.startsWith('https://local-app.clashk.ing/'))throw Error('Wrong environment link');
  if(embed.fields.some(f=>f.value.length>1024||f.name.length>256)||embed.fields.length>25||text.length+embed.title.length+embed.author.name.length>6000)throw Error('Discord embed limit exceeded');
  if(reply.components.some(row=>row.components.length>5)||reply.components.flatMap(row=>row.components).some(b=>b.custom_id.length>100))throw Error('Discord controls exceed limits');
  const ids=reply.components.flatMap(row=>row.components).map(button=>button.custom_id);
  if(new Set(ids).size!==ids.length)throw Error('Discord rejects duplicate button custom IDs');
  if(reply.components.flatMap(row=>row.components).map(button=>button.label).join(',')!=='Today,Yesterday,Season')throw Error('Unexpected day navigation controls');
 };
 validateLegend(season);
 const dayLabel=seasonEmbed.footer;
 if(!dayLabel?.text.startsWith('Day '))throw Error('Day footer missing');
 const buttons=season.components.flatMap(row=>row.components);
 const seasonPage=await interact({type:3,data:{custom_id:buttons.find(b=>b.label==='Season').custom_id,component_type:2}});
 validateLegend(seasonPage);
 const table=seasonPage.embeds[0].fields.filter(f=>f.value.startsWith('```ansi')).map(f=>f.value).join('\n');
 const plainTable=table.replace(/\x1b\[[0-9;]*m/gu,'');
 if(!table.startsWith('```ansi\n')||!table.includes('\x1b[32m')||!table.includes('\x1b[31m'))throw Error('Season net gains and losses are not ANSI colored');
 if(!plainTable.includes('Day  Off   Def   Net')||plainTable.includes('Finish')||plainTable.split('\n').some(line=>line.length>22))throw Error('Season table is not narrow/day-numbered');
 const previous=buttons.find(b=>b.label==='Yesterday');
 const shared=await interact({type:3,data:{custom_id:buttons.find(b=>b.label==='Season').custom_id.replace(actor,'999999999999998004'),component_type:2}});
 validateLegend(shared);
 if(shared.embeds[0].title!=='Legend Season')throw Error('Public day controls are incorrectly actor-locked');
 if(!previous.disabled){
  const prior=await interact({type:3,data:{custom_id:previous.custom_id,component_type:2}});validateLegend(prior);
  if(prior.embeds[0].footer.text===dayLabel.text)throw Error('Previous day navigation did not change the day');
  const selectedDay=previous.custom_id.split(':')[6];
  const dayResponse=await fetch(`http://127.0.0.1:8787/v2/player/%23LG8Q9QYR/legend/${selectedDay}/battlelog`,{headers:{Authorization:`Bearer ${workspace.env.API_BOT_TOKEN}`}});
  const selectedStats=await dayResponse.json();
  const dayArmy=prior.embeds[0].fields.find(item=>item.name==='Most used army');
  if(selectedStats.topArmy){
   if(selectedStats.topArmy.attacks>selectedStats.attacks.length||!dayArmy||/attacks|triples/u.test(dayArmy.value)||!selectedStats.topArmy.name.split(' / ').every(name=>dayArmy.value.includes(name))||!/<a?:\w+:\d+>/u.test(dayArmy.value))throw Error('Selected-day army name or emojis missing');
  }else if(dayArmy)throw Error('Daily army invented without a recorded composition');
  const signed=value=>(value>=0?'+':'')+value.toLocaleString('en');
  if(!prior.embeds[0].description.includes(`**${signed(selectedStats.trophies)} net**`))throw Error('Selected-day net summary is incorrect');
  for(const [field,total] of [['Attacks',selectedStats.attackTrophies],['Defenses',selectedStats.defenseTrophies]]){
   if(!dayResponse.ok||!prior.embeds[0].fields.find(item=>item.name.includes(field))?.value.split('\n')[0].includes(`**${signed(total)}**`))throw Error('Daily statistics do not match the selected day: '+field);
  }
  const today=await interact({type:3,data:{custom_id:prior.components[0].components.find(b=>b.label==='Today').custom_id,component_type:2}});
  if(today.embeds[0].footer.text!==dayLabel.text)throw Error('Today navigation did not return to current day');
 }
 for(const type of ['cutoffs','buckets','winners','daily']){
  const global=await interact({type:2,data:{name:'legends',options:[{name:'stats',type:1,options:[{name:'type',type:3,value:type}]}]}});
  if(!global.embeds?.[0]||global.embeds[0].color!==0x123456||global.embeds[0].footer)throw Error('Global stats failed for '+type+': '+JSON.stringify(global));
  const controls=global.components.flatMap(row=>row.components);
  if(controls.length===1&&(controls[0].label||!controls[0].emoji))throw Error('Refresh control is not emoji-only');
  if(type==='cutoffs'&&!global.embeds[0].description.includes('Ranking snapshot:'))throw Error('Rank freshness is missing');
  if(type==='cutoffs'){
   const refreshed=await interact({type:3,data:{custom_id:global.components[0].components[0].custom_id,component_type:2}});
   if(refreshed.embeds[0].title!==global.embeds[0].title)throw Error('Global refresh failed');
  }
 }
 const unauthorized=await fetch('http://127.0.0.1:8787/v2/bot/legends/stats');
 if(unauthorized.status!==401)throw Error('Global bot API does not reject unauthenticated requests');
 for(const action of ['location','family']){
  const missing=await interact({type:2,data:{name:'leaderboard',options:[{name:action,type:1}]}});
  if(!missing.content?.includes('Choose'))throw Error('Leaderboard selector is not required: '+action);
 }
 const locationBoard=await interact({type:2,data:{name:'leaderboard',options:[{name:'location',type:1,options:[{name:'location',type:3,value:'global'},{name:'village',type:3,value:'home'},{name:'limit',type:4,value:25}]}]}});
 if(!locationBoard.embeds?.[0]?.title.includes('Global Top')||!locationBoard.embeds[0].description.includes('\u2068')||!locationBoard.embeds[0].description.includes('\u2069')||!locationBoard.embeds[0].description.includes('-# \u2066`#')||/\d\.\dK/u.test(locationBoard.embeds[0].description))throw Error('Legacy leaderboard layout or bidi isolation missing');
 const nextBoard=await interact({type:3,data:{custom_id:locationBoard.components[0].components.find(button=>button.label==='Next').custom_id,component_type:2}});
 if(nextBoard.embeds[0].description===locationBoard.embeds[0].description)throw Error('Leaderboard pagination failed');
 const emptyFamily=await interact({type:2,data:{name:'leaderboard',options:[{name:'family',type:1,options:[{name:'type',type:3,value:'legends'}]}]}});
 if(!emptyFamily.content?.includes('No family clans are linked')||!emptyFamily.content.includes(`/dashboard/clans?guildId=${guild}`)||emptyFamily.flags!==64)throw Error('Unlinked family error is not private with a server Dashboard link');
 const clanView=await interact({type:2,data:{name:'legends',options:[{name:'clan',type:1,options:[{name:'clan',type:3,value:'#8YL9CRJP'}]}]}});
 if(!clanView.embeds?.[0]?.description.includes('tab=competitive')||!clanView.embeds[0].description.includes('net')||!clanView.embeds[0].description.includes('/8)')||clanView.embeds[0].footer.text.includes('entries'))throw Error('Clan current-day presentation missing');
 await db.query('INSERT INTO server_clans(server_id,tag) VALUES($1,$2)',[guild,'#8YL9CRJP']);
 try{
  const familyBoard=await interact({type:2,data:{name:'leaderboard',options:[{name:'family',type:1,options:[{name:'type',type:3,value:'legends'}]}]}});
  if(!familyBoard.embeds?.[0]?.description.includes('\u2068')||familyBoard.embeds[0].description.includes('No recorded'))throw Error('Current Legend tiers missing from family leaderboard');
 }finally{await db.query('DELETE FROM server_clans WHERE server_id=$1 AND tag=$2',[guild,'#8YL9CRJP']);}
 if(!['cdn.discordapp.com','api-assets.clashofclans.com','assets.clashk.ing'].every(host=>loadedAssetHosts.has(host)))throw Error('Poster artwork was not fetched successfully');
 const accounts=await interact({type:2,data:{name:'player',options:[{name:'accounts',type:1}]}});
 const accountRefresh=accounts.components.flatMap(row=>row.components).find(button=>button.custom_id?.startsWith(`ck:page:ac:${actor}:`));
 if(!accountRefresh?.emoji?.id||accounts.embeds[0].fields?.some(field=>field.name==='Combined stats'))throw Error('Account refresh missing or removed combined stats remain');
 const refreshedAccounts=await interact({type:3,data:{custom_id:accountRefresh.custom_id,component_type:2}});
 if(!refreshedAccounts.embeds?.length)throw Error('Account refresh failed');
 const profile=await interact({type:2,data:{name:'player',options:[{name:'lookup',type:1,options:[{name:'player',type:3,value:'#2J8V28GV0'}]}]}});
 if(!profile.embeds[0].thumbnail||!profile.embeds[0].fields.some(field=>field.name==='All time'))throw Error('Detailed player profile missing');
 if(profile.embeds[0].fields.some(field=>['Heroes','Boosted troops','Season events'].includes(field.name)))throw Error('Overview clutter returned');
 const livePlayer=await(await fetch('http://127.0.0.1:8787/v2/bot/clash/players/%232J8V28GV0',{headers:{Authorization:`Bearer ${workspace.env.API_BOT_TOKEN}`}})).json();
 const liveGroup=await(await fetch(`http://127.0.0.1:8787/v2/bot/clash/leaguegroup/${encodeURIComponent(livePlayer.currentLeagueGroupTag)}/${livePlayer.currentLeagueSeasonId}?playerTag=%232J8V28GV0`,{headers:{Authorization:`Bearer ${workspace.env.API_BOT_TOKEN}`}})).json();
 const liveMember=liveGroup.members?.find(member=>member.playerTag==='#2J8V28GV0');
 const tiers=await(await fetch('https://assets.clashk.ing/static_data/league_tiers.json')).json();
 const liveLimit=tiers.items.find(tier=>tier._id===livePlayer.leagueTier.id)?.battle_count;
 if(!liveMember||!profile.embeds[0].fields[0].value.includes(`${liveMember.attackWinCount+liveMember.attackLoseCount}/${liveLimit} attacks`)||!profile.embeds[0].fields[0].value.includes(`${liveMember.defenseWinCount+liveMember.defenseLoseCount}/${liveLimit} defenses`))throw Error('Live ranked counts or metadata limit missing: '+JSON.stringify(profile.embeds[0].fields[0]));
 for(const field of profile.embeds[0].fields){
  if(field.inline)throw Error('Overview must stack on mobile');
  if(field.name==='All time'&&(!field.value.includes('\n')||field.value.includes(' · ')))throw Error('Lifetime metrics must use separate mobile-friendly lines');
 }
 if(!profile.embeds[0].fields.some(field=>field.name==='Season stats')||profile.embeds[0].fields.some(field=>field.name==='Season loot'))throw Error('Season stats must group donations and loot');
 const profilePicker=profile.components[0].components[0];
 if(profilePicker.options.map(option=>option.label).join('|')!=='Overview|Troops|Progress|Clan History')throw Error('Profile pages not configured');
 for(const view of ['troops','upgrades','history','overview']){
  const page=await interact({type:3,data:{custom_id:profilePicker.custom_id,component_type:3,values:[view]}});
  if(!page.embeds?.[0]||(!['troops','history'].includes(view)&&!page.embeds[0].fields?.length)||page.components[0].components[0].options.find(option=>option.value===view)?.default!==true)throw Error('Profile page switch failed: '+view);
  let pageFields=page.embeds[0].fields??[];
  if(view==='history'){
   if(pageFields.length||!page.embeds[0].description.includes('**Top 5 Clans Player has stayed the most:**')||page.embeds[0].footer.text!=='Data from ClashKing')throw Error('ClashKing history must default to legacy text layout');
   const buttons=page.components.flatMap(row=>row.components);
   if(!buttons.find(button=>button.label==='ClashKing')?.disabled)throw Error('ClashKing history should be selected by default');
   const other=await interact({type:3,data:{custom_id:buttons.find(button=>button.label==='Clash of Stats').custom_id,component_type:2}});
   if(other.embeds?.[0]?.footer?.text!=='Data from ClashofStats.com'||other.embeds[0].fields?.length)throw Error('Clash of Stats history switch failed');
   if(!other.embeds[0].description.includes('[Full History]('))throw Error('Clash of Stats must retain direct history link');
   if(!other.components.flatMap(row=>row.components).find(button=>button.label==='Clash of Stats')?.disabled)throw Error('History selection state not updated');
   const back=other.components.flatMap(row=>row.components).find(button=>button.label==='ClashKing');
   const restored=await interact({type:3,data:{custom_id:back.custom_id,component_type:2}});
   if(restored.embeds[0].footer.text!=='Data from ClashKing')throw Error('ClashKing history could not be restored');
  }
  if(view==='upgrades'){
   if(!pageFields.some(field=>field.name==='Overall progress')||!pageFields.some(field=>/<.*> Remaining at TH18/.test(field.name)))throw Error('Progress summaries missing');
   const equipment=pageFields.find(field=>field.name.endsWith(' Equipment'));
   if(!equipment||!/full_shinyore:/.test(equipment.value)||!/full_glowyore:/.test(equipment.value)||!/full_starryore:/.test(equipment.value)||/upgrade work|h remaining/.test(equipment.value))throw Error('Equipment must show corrected ore emojis without time');
   if(pageFields.some(field=>/game max|TH max/.test(field.value))||!pageFields[0].value.includes('to max'))throw Error('Max-TH progress should not duplicate TH and game percentages');
   if(!page.embeds[0].footer.text.includes('Rushed = missing levels from the previous Town Hall')||/Buildings excluded|based on levels|Base values|Unlock costs/.test(JSON.stringify(page.embeds[0])))throw Error('Progress explanation must stay in footer');
   for(const field of pageFields.filter(field=>field.name!=='Overall progress'))if(!field.name.startsWith('<:'))throw Error('Progress category missing header icon');
   if(pageFields.some(field=>/No resource cost|NaN|Infinity|Barbarian|Frozen Arrow/.test(field.value)))throw Error('Invalid or individual-upgrade content in progress summary');
  }
  if(view==='troops'){
   let troopPage=page;const descriptions=[];
   for(let i=0;i<10;i++){
    if(troopPage.embeds[0].fields?.length||troopPage.embeds[0].description.length>4096)throw Error('Troops must use description text within its limit');
    descriptions.push(troopPage.embeds[0].description);
    const next=troopPage.components.flatMap(row=>row.components).find(button=>button.label==='Next'&&!button.disabled);
    if(!next)break;
    troopPage=await interact({type:3,data:{custom_id:next.custom_id,component_type:2}});
    if(i===9)throw Error('Troop pagination did not terminate');
   }
   pageFields=descriptions.flatMap(description=>[...description.matchAll(/\*\*([^*\n]+)\*\*\n([\s\S]*?)(?=\n\n\*\*|$)/g)].map(match=>({name:match[1],value:match[2]})));
   for(const name of ['Elixir troops','Dark Elixir troops','Spells','Heroes','Common equipment','Epic equipment'])if(!pageFields.some(field=>field.name===name))throw Error('Missing troop grouping: '+name);
   for(const field of pageFields.filter(field=>field.name!=='Builder Base')){
    const width=field.name==='Heroes'?7:5;
    const levels=[...field.value.matchAll(/`([^`]+)`/g)].map(match=>match[1]);
    if(!levels.length||levels.some(level=>level.length!==width))throw Error('Uneven level boxes: '+field.name);
    if(levels.some(level=>!/^\u00a0*\d+\/\d+\u00a0*$/.test(level)))throw Error('Level padding must stay outside the number pair: '+field.name);
    if(field.name==='Heroes'&&field.value.split('\n').some(line=>[...line.matchAll(/`([^`]+)`/g)].length>2))throw Error('Too many heroes on a line');
   }
  }
  if(!['troops','history'].includes(view)&&(pageFields.slice(0,-1).some(field=>!field.value.endsWith('\n\u200b'))||pageFields.at(-1).value.endsWith('\n\u200b')))throw Error('Profile spacing must separate fields without bottom padding: '+view);
  if(page.embeds.some(embed=>(embed.fields??[]).some(field=>field.value.length>1024))||page.embeds.reduce((sum,embed)=>sum+(embed.description?.length??0)+(embed.fields??[]).reduce((n,field)=>n+field.name.length+field.value.length,0),0)>5800)throw Error('Profile embed too large');
 }
 const ranked=await interact({type:2,data:{name:'ranked',options:[{name:'player',type:1,options:[{name:'player',type:3,value:'#2J8V28GV0'}]}]}});
 if(!ranked.chartBytes||!ranked.embeds[0].image?.url.includes('ranked-season.png'))throw Error('Ranked PNG missing');
 const groupButton=ranked.components[0].components.find(button=>button.label==='Group');
 const group=await interact({type:3,data:{custom_id:groupButton.custom_id,component_type:2}});
 if(!group.embeds[0].title.endsWith('Group')||group.attachments.length!==0||group.embeds[0].image)throw Error('Group page failed to clear graphic');
 const groupNext=group.components.flatMap(row=>row.components).find(button=>button.label==='Next');
 const groupPage2=await interact({type:3,data:{custom_id:groupNext.custom_id,component_type:2}});
 if(groupPage2.embeds[0].description===group.embeds[0].description)throw Error('Ranked group pagination failed');
 const groupIds=groupPage2.components.flatMap(row=>row.components).map(button=>button.custom_id).filter(Boolean);
 if(new Set(groupIds).size!==groupIds.length)throw Error('Duplicate Ranked component IDs');
 const playerButton=groupPage2.components[0].components.find(button=>button.label==='Player');
 const returnedRanked=await interact({type:3,data:{custom_id:playerButton.custom_id,component_type:2}});
 if(!returnedRanked.chartBytes)throw Error('Ranked player navigation failed');
 const clanTag='#P09LP8CY',clanStatsUrl=`http://127.0.0.1:8787/v2/bot/clans/${encodeURIComponent(clanTag)}/season-stats`;
 if((await fetch(clanStatsUrl)).status!==401)throw Error('Clan stats must require Bot authentication');
 const readClanStats=async season=>{const r=await fetch(clanStatsUrl+(season?`?season=${season}`:''),{headers:{Authorization:`Bearer ${workspace.env.API_BOT_TOKEN}`}});if(!r.ok)throw Error('Clan stats API failed '+r.status);return r.json();};
 const currentStats=await readClanStats(),oldStats=await readClanStats('2026-09');
 if(oldStats.current)throw Error('Historical clan season incorrectly marked current');
 if((await db.query('SELECT 1 FROM player_stat_changes WHERE player_tag=ANY($1::text[])',[[verifiedTag,unverifiedTag]])).rowCount)throw Error('Synthetic contribution tags already have data');
 const currentTime=new Date(Date.now()-60000).toISOString(),oldTime=new Date(Date.parse(oldStats.start)+3600000).toISOString();contributionTimes.push(currentTime,oldTime);
 await db.query("INSERT INTO player_stat_changes(event_time,player_tag,clan_tag,stat_type,previous_value,current_value,delta) VALUES($1,$3,$5,'donated',0,999999,999999),($2,$3,$5,'donated',0,777777,777777),($1,$4,'#PYLQGRC','donated',0,888888,888888)",[currentTime,oldTime,verifiedTag,unverifiedTag,clanTag]);
 const checkedStats=await readClanStats();
 if(checkedStats.items.find(row=>row.tag===verifiedTag)?.donated!==999999||checkedStats.items.some(row=>row.tag===unverifiedTag))throw Error('Clan-attributed former-member donations incorrect');
 const clanCall=async(action,extra=[])=>interact({type:2,data:{name:'clan',options:[{name:action,type:1,options:[{name:'clan',type:3,value:clanTag},...extra]}]}});
 const overview=await clanCall('search');
 if(!overview.embeds?.[0]?.description.includes('Winratio:')||!overview.embeds[0].fields?.some(field=>field.name==='Townhall Composition:'))throw Error('Legacy detailed clan overview missing');
 const overviewButtons=overview.components.flatMap(row=>row.components);
 if(overviewButtons.length!==2||overviewButtons.some(button=>['Overview','Donations'].includes(button.label))||!overviewButtons.some(button=>button.label==='Open In-Game'))throw Error('Clan search must only show refresh and Open In-Game');
 const basic=await clanCall('search',[{name:'type',type:3,value:'b'}]);if(basic.embeds[0].fields?.length||!basic.embeds[0].description.includes('Wars Won:'))throw Error('Basic clan overview incorrect');
 const donations=await clanCall('donations');
 if(!donations.embeds[0].description.includes(verifiedTag)||!donations.embeds[0].description.includes('DON   REC'))throw Error('Default donation board must include former contributors and the legacy table');
 const allButtons=reply=>reply.components.flatMap(row=>row.components),onlyButton=allButtons(donations).find(button=>button.label==='Current members only');
 if(!onlyButton)throw Error('Missing member filter');
 if(donations.components.length!==1||donations.components[0].components.length!==2)throw Error('Donation refresh and member toggle must share one row');
 const onlyMembers=await interact({type:3,data:{custom_id:onlyButton.custom_id,component_type:2}});
 if(onlyMembers.embeds[0].description.includes(verifiedTag))throw Error('Current-member filter kept a former member');
 const includeFormer=allButtons(onlyMembers).find(button=>button.label==='Include former members');
 const restoredDonations=await interact({type:3,data:{custom_id:includeFormer.custom_id,component_type:2}});
 if(!restoredDonations.embeds[0].description.includes(verifiedTag))throw Error('Former-member toggle lost recorded data');
 if(donations.embeds[0].description.split('\n').length!==51||donations.embeds[0].description.length>4096)throw Error('Default donations must fit fifty rows in one embed');
 const shortDonations=await clanCall('donations',[{name:'limit',type:4,value:10}]);
 if(shortDonations.embeds[0].description.split('\n').length!==11)throw Error('Donation limit must reduce rows, not create pages');
 for(const reply of [donations,onlyMembers,restoredDonations,shortDonations])if(allButtons(reply).some(button=>['Next','Previous','Overview','Donations','Open In-Game'].includes(button.label)))throw Error('Donation board has unwanted navigation');
 for(const reply of [overview,basic,donations,onlyMembers,restoredDonations,shortDonations]){const ids=allButtons(reply).flatMap(button=>button.custom_id?[button.custom_id]:[]);if(ids.some(id=>id.length>100)||new Set(ids).size!==ids.length)throw Error('Invalid clan control IDs');}
 const historicalDonations=await clanCall('donations',[{name:'season',type:3,value:'2026-09'}]);
 if(!historicalDonations.embeds[0].description.includes('777.8K')||allButtons(historicalDonations).some(button=>button.label==='Current members only'))throw Error('Historical donations used current data or current-only controls');
 const unicodePlayers=[['#PYLQGR20','漢字漢字漢字漢字'],['#PYLQGR22','👨‍👩‍👧‍👦👨‍👩‍👧‍👦👨‍👩‍👧‍👦X'],['#PYLQGR28','Cafe\u0301Cafe\u0301Cafe\u0301Cafe\u0301'],['#PYLQGR29','العربية'],['#PYLQGR2P','ＡＢＣＤＥＦＧ']];
 if((await db.query('SELECT 1 FROM basic_player WHERE tag=ANY($1::text[])',[unicodePlayers.map(row=>row[0])])).rowCount)throw Error('Unicode fixture tags already exist');
 for(const [i,[tag,name]] of unicodePlayers.entries()){
  await db.query('INSERT INTO basic_player(tag,name,townhall_level) VALUES($1,$2,18)',[tag,name]);unicodeTags.push(tag);
  await db.query("INSERT INTO player_stat_changes(event_time,player_tag,clan_tag,stat_type,previous_value,current_value,delta) VALUES($1,$2,$3,'donated',0,$4,$4)",[currentTime,tag,clanTag,2000000000-i]);
 }
 const unicodeDonations=await clanCall('donations',[{name:'limit',type:4,value:5}]);
 const nameCells=[...unicodeDonations.embeds[0].description.matchAll(/\u2068([^\u2069]*)\u2069/g)].map(match=>match[1]);
 if(nameCells.length!==5||nameCells.some(name=>stringWidth(name)!==13||/\p{Surrogate}/u.test(name)))throw Error('Unicode names lost display-width alignment');
 if(!nameCells[1].includes('👨‍👩‍👧‍👦')||!nameCells[2].includes('e\u0301')||!nameCells[3].includes('العربية'))throw Error('Unicode names were transliterated or split');
 if(/[⁰¹²³⁴⁵⁶⁷⁸⁹]/u.test(unicodeDonations.embeds[0].description)||!unicodeDonations.embeds[0].description.split('\n').slice(1).every(row=>row.slice(0,row.indexOf('\u2068')).endsWith('18 ')))throw Error('Town Hall must use normal digits before the name');
 console.log(JSON.stringify({unicodeDonationNames:'passed',graphemePreservation:'passed'}));
 console.log(JSON.stringify({clanOverview:'passed',clanDonationHistory:'passed',formerMemberToggle:'passed',fiftyDonationRows:'passed',donationLimit:'passed',clanStatsSeason:currentStats.season}));
 console.log(JSON.stringify({accountsRefresh:'passed',playerProfilePages:'passed',hiddenIdentity:'passed',membershipGuard:'passed',rankedPages:'passed',rankedPngBytes:ranked.chartBytes}));
 console.log(JSON.stringify({slashCommand:'passed',leaderboards:'passed',bidiIsolation:'passed',requiredLeaderboardSelectors:'passed',currentLegendTiers:'passed',legacyHistoryButton:'passed',currentAndPreviousDay:'passed',seasonTable:'passed',storedStars:'passed',armyGroups:'passed',relativeTimes:'passed',posterAssets:'passed',pngAttachmentBytes:season.chartBytes,embedAndControlLimits:'passed',controlOwnership:'passed',yearGroups:command.embeds[0].fields.filter(field=>field.name!=='Previous Names').map(field=>field.name),discordNetworkWrites:0}));
}finally{await bot.dispose();if(contributionTimes.length)await db.query('DELETE FROM player_stat_changes WHERE player_tag=ANY($1::text[]) AND event_time=ANY($2::timestamptz[])',[[verifiedTag,unverifiedTag,...unicodeTags],contributionTimes]);if(unicodeTags.length)await db.query('DELETE FROM basic_player WHERE tag=ANY($1::text[])',[unicodeTags]);if(ownsActivity)await db.query('DELETE FROM player_online_events WHERE tag=$1',[verifiedTag]);if(ownsUser){await db.query('DELETE FROM user_bookmarks WHERE user_id=$1',[actor]);await db.query('DELETE FROM player_links WHERE user_id=$1 AND tag=ANY($2::text[])',[actor,[verifiedTag,unverifiedTag]]);await db.query('DELETE FROM auth_users WHERE user_id=$1',[actor]);}if(ownsServer)await db.query('DELETE FROM servers WHERE id=$1',[guild]);await db.end();}
