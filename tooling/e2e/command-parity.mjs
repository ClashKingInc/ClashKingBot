// Actual workerd -> local API -> local SQL/HTTP provider integration. No Discord network calls.
import { createServer } from 'node:http';
import { bundleWorker } from './bundle-worker.mjs';
import { generateKeyPairSync, randomBytes, sign } from 'node:crypto';
import { readFileSync, mkdtempSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const botRepo=resolve(fileURLToPath(new URL('../../',import.meta.url)));
const apiRepo=resolve(process.env.CLASHKING_E2E_API_REPO??join(botRepo,'../clashking_api'));
const assetsRepo=resolve(process.env.CLASHKING_E2E_ASSETS_REPO??join(botRepo,'../clashking_assets'));
const require=createRequire(join(apiRepo,'package.json'));
const {Client}=require('pg'),{build}=require('esbuild'),{Miniflare,convertV4MiniflareOptions}=require('miniflare');
const database=process.env.CLASHKING_E2E_DATABASE_URL??'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev';
const dbURL=new URL(database);if(dbURL.protocol!=='postgres:'||dbURL.hostname!=='127.0.0.1'||dbURL.pathname!=='/clashking_dev')throw Error('Use the owned loopback clashking_dev database');
const port=Number(process.env.CLASHKING_E2E_API_PORT??8801);if(!Number.isInteger(port)||port<1024||port>65535)throw Error('Invalid local API port');
const {publicKey,privateKey}=generateKeyPairSync('ed25519');
const publicHex=publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex');
const betaInventory=process.env.CLASHKING_E2E_BETA_EMOJIS==='1';
let app='999999999999996501';const actor='999999999999996502',other='999999999999996503';
let emojiItems=[],emojiInventoryRequests=0;
if(betaInventory){
 const {loadLocalBetaDiscordCredentials}=await import(pathToFileURL(join(apiRepo,'scripts/local-api-keychain.mjs')).href);
 const credentials=loadLocalBetaDiscordCredentials();app=credentials.clientId;
 const response=await fetch(`https://discord.com/api/v10/applications/${app}/emojis`,{headers:{Authorization:`Bot ${credentials.botToken}`}});
 if(!response.ok)throw Error(`Read-only Beta emoji inventory HTTP ${response.status}`);
 emojiItems=(await response.json()).items;
 for(const name of ['pekka','war_star','blue_1','th16'])if(!emojiItems.some(item=>item.name===name&&item.available!==false))throw Error(`Missing Beta emoji ${name}`);
}
const tag='#PYLQGRJCUV',group='#PYLQGRJC',currentSeason=1900000000;
const tags=Array.from({length:35},(_,index)=>'#PYLQ'+index.toString(8).replaceAll('1','P').replaceAll('3','Y').replaceAll('4','L').replaceAll('5','Q').replaceAll('6','G').replaceAll('7','R'));
const codes=(JSON.parse(readFileSync(join(assetsRepo,'assets/static_data/league_tiers.json'))).items);
const tier=codes.find(row=>row.name!=='Unranked')?._id??105000001;
const live=[];
let reminderWarActive=true, reminderRaidActive=true, reminderCwl=false, reminderSendFails=false, reminderPreparation=false;
const sentReminders=[];
const provider=createServer(async(req,res)=>{
 let text='';for await(const chunk of req)text+=chunk;
 const url=new URL(req.url,'http://provider');live.push(url.pathname+url.search);res.setHeader('Content-Type','application/json');
 const p=decodeURIComponent(url.pathname),endTime=new Date(Date.now()+3600000).toISOString();
 const startTime=new Date(Date.now()+1800000).toISOString(),warState=reminderPreparation?'preparation':'inWar';
 const own={tag:group,name:'Reminder Clan',stars:5,members:[{tag,name:'Missing Player',townhallLevel:16,attacks:[]},{tag:tags[1],name:'Finished Player',townhallLevel:16,attacks:[{},{}]}]};
 const opponent={tag:'#PYLQGRJJ',name:'Other Clan',stars:3,members:[]};
 if(p===`/v1/clans/${group}/currentwar`)return res.end(JSON.stringify(reminderWarActive&&!reminderCwl?{state:warState,startTime:startTime.replace(/[-:]/g,''),endTime,attacksPerMember:2,clan:own,opponent}:{state:'notInWar'}));
 if(p===`/v1/clans/${group}/currentwar/leaguegroup`)return res.end(JSON.stringify({rounds:reminderCwl?[{warTags:['#PYLQGRJQ']}]:[]}));
 if(p==='/v1/clanwarleagues/wars/#PYLQGRJQ')return res.end(JSON.stringify({state:warState,startTime,endTime,clan:opponent,opponent:own}));
 if(p===`/v1/clans/${group}`)return res.end(JSON.stringify({tag:group,name:'Reminder Clan',memberList:[{tag,name:'Missing Player',townHallLevel:16},{tag:tags[1],name:'Finished Player',townHallLevel:16}]}));
 if(p===`/v1/clans/${group}/capitalraidseasons`)return res.end(JSON.stringify({items:reminderRaidActive?[{state:'ongoing',endTime,members:[{tag:tags[1],attacks:6,attackLimit:5,bonusAttackLimit:1}]}]:[]}));
 if(url.pathname.startsWith('/v1/players/')){const playerTag=decodeURIComponent(url.pathname.split('/').at(-1));return res.end(JSON.stringify({tag:playerTag,name:playerTag===tag?'Current Player':`Account ${tags.indexOf(playerTag)+1}`,townHallLevel:16,trophies:5500,warStars:100,expLevel:250,donations:50,donationsReceived:40,currentLeagueGroupTag:group,currentLeagueSeasonId:currentSeason,leagueTier:{id:tier,name:'Current League'},
 // Deliberately synthetic name input exercises the normal lookup renderer; this is not real player data.
 ...(betaInventory?{heroes:[{name:'P.E.K.K.A.',level:15}]}:{})}));}
 if(url.pathname===`/v1/leaguegroup/${encodeURIComponent(group)}/${currentSeason}`||decodeURIComponent(url.pathname)===`/v1/leaguegroup/${group}/${currentSeason}`){
  if(url.searchParams.get('playerTag')!==tag){res.statusCode=400;return res.end('{}');}
  return res.end(JSON.stringify({members:Array.from({length:35},(_,i)=>({playerTag:i===0?tag:tags[i],playerName:`Current Member ${i+1}`,leagueTrophies:6000-i,attackWinCount:4,attackLoseCount:1,defenseWinCount:2,defenseLoseCount:3,clanName:null,clanTag:null}))}));
 }
 res.statusCode=404;res.end(JSON.stringify({reason:'notFound'}));
});await new Promise(r=>provider.listen(0,'127.0.0.1',r));const providerPort=provider.address().port;
const db=new Client({connectionString:database});await db.connect();
let api,bot,logs='',ownsRecords=false;let counter=999999999999996600n;const replies=new Map();
const keys=Object.fromEntries(['DATA_ENCRYPTION_KEY','JWT_ACCESS_SECRET','JWT_REFRESH_SECRET','API_BOT_TOKEN','AI_USAGE_SECRET','STRIPE_WEBHOOK_SECRET'].map(key=>[key,randomBytes(32).toString('base64url')]));
const directory=mkdtempSync(join(tmpdir(),'ck-command-parity-'));
const wait=async(fn,label)=>{for(let i=0;i<100;i++){const result=await fn();if(result)return result;await new Promise(r=>setTimeout(r,100));}throw Error(`Timeout ${label}: ${logs.slice(-1500)}`);};
const historySeasons=Array.from({length:35},(_,i)=>Math.floor(Date.now()/1000)-86400*(i+1));
try{
 if((await db.query('SELECT user_id FROM auth_users WHERE user_id=ANY($1::text[])',[[actor,other]])).rowCount)throw Error('Synthetic users already exist');
 if((await db.query('SELECT tag FROM player_links WHERE tag=ANY($1::text[])',[tags])).rowCount)throw Error('Synthetic tags already linked');
 if((await db.query('SELECT player_tag FROM ranked_league_group_members WHERE player_tag=$1',[tag])).rowCount)throw Error('Synthetic ranked player already exists');
 await db.query("INSERT INTO auth_users(user_id,provider) VALUES($1,'discord'),($2,'discord')",[actor,other]);
 ownsRecords=true;
 for(const playerTag of tags)await db.query("INSERT INTO player_links(tag,user_id,source) VALUES($1,$2,'discord')",[playerTag,actor]);
 const armies=(await db.query('SELECT share_code FROM army_compositions ORDER BY length(share_code),share_code LIMIT 30')).rows;
 if(armies.length<30)throw Error('Thirty existing local compositions required');
 for(const army of armies)await db.query('INSERT INTO user_saved_armies(user_id,share_code) VALUES($1,$2)',[actor,army.share_code]);
 for(const season of historySeasons)await db.query(`INSERT INTO ranked_league_group_members(season_id,group_tag,league_tier_id,player_tag,player_name,placement,league_trophies,attack_win_count,attack_loss_count,defense_win_count,defense_loss_count,town_hall,maximum_battle_count) VALUES($1,$2,$3,$4,'Historical Player',1,5000,8,1,4,5,16,10)`,[season,group,tier,tag]);
 const env={PATH:process.env.PATH,HOME:process.env.HOME,TMPDIR:process.env.TMPDIR,CLASHKING_PERSISTENT_LOCAL_API:'1',CLASHKING_LOCAL_DATABASE_URL:database,CLASHKING_LOCAL_API_PORT:String(port),CLASHKING_LOCAL_DISCORD_CLIENT_ID:app,CLASHKING_LOCAL_DISCORD_CLIENT_SECRET:'local-only',CLASHKING_LOCAL_DISCORD_PUBLIC_KEY:publicHex,CLASHKING_LOCAL_ARCHIVE_BRIDGE:'0',CLASHKING_LOCAL_CLASH_PROXY_ORIGIN:`http://127.0.0.1:${providerPort}`,CLASHKING_LOCAL_STATIC_ASSETS_ROOT:join(assetsRepo,'assets/static_data'),CLASHKING_LOCAL_STORAGE_ROOT:join(directory,'storage'),...Object.fromEntries(Object.entries(keys).map(([key,value])=>[`CLASHKING_LOCAL_${key}`,value]))};
 api=spawn(process.execPath,['scripts/start-local-rewrite-api.mjs'],{cwd:apiRepo,env,stdio:['ignore','pipe','pipe']});api.stdout.on('data',data=>logs+=data);api.stderr.on('data',data=>logs+=data);
 // Health can become ready before static metadata is seeded. Army previews
 // exercise that metadata, so do not race the real launcher's second phase.
 await wait(async()=>{try{return logs.includes('local_static_assets_seeded')&&(await fetch(`http://127.0.0.1:${port}/v2/health`)).ok;}catch{return false;}},'API and static assets startup');
 const bundle=await bundleWorker();
 bot=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{name:'command-e2e',...bundle,compatibilityDate:'2026-08-22',compatibilityFlags:['nodejs_compat'],
 bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:`http://127.0.0.1:${port}`,CLASHKING_API_TOKEN:keys.API_BOT_TOKEN,DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:`${Buffer.from(app).toString('base64')}.local.token`,DISCORD_PUBLIC_KEY:publicHex},
 outboundService:async request=>{
  const url=new URL(request.url);
  if(url.hostname==='assets.clashk.ing'&&/^\/static_data\/(troops|spells|heroes|pets|equipment|buildings)\.json$/u.test(url.pathname))return new Response(readFileSync(join(assetsRepo,'assets',url.pathname)),{headers:{'Content-Type':'application/json'}});
  if(url.hostname==='discord.com'){
   if(request.method==='GET'&&url.pathname.endsWith('/emojis')){emojiInventoryRequests++;return Response.json({items:emojiItems});}
   if(request.method==='GET'&&url.pathname.includes('/channels/'))return Response.json({id:url.pathname.split('/').at(-1),guild_id:'999999999999996510',type:0});
   if(request.method==='POST'&&url.pathname.endsWith('/messages')){if(reminderSendFails)return Response.json({message:'Missing permissions'},{status:403});sentReminders.push(await request.json());return Response.json({id:'999999999999996999'});}
   const token=url.pathname.split('/')[5];const data=await request.json();replies.set(token,data);return Response.json({id:'999999999999996999'});
  }
  if(url.hostname==='127.0.0.1'&&url.port===String(port))return fetch(request.url,{method:request.method,headers:Object.fromEntries(request.headers),body:['GET','HEAD'].includes(request.method)?undefined:await request.arrayBuffer()});
  throw Error('External request blocked by local integration harness');
 }}]}));
 const origin=new URL('/interactions',String(await bot.ready)).href;
 async function interact(data,who=actor,permissions='0'){const token=String(counter++);const rawBody=JSON.stringify({id:token,application_id:app,guild_id:'999999999999996510',channel_id:'999999999999996511',member:{user:{id:who,username:'Local'},roles:[],permissions},version:1,token,...data});const timestamp=String(Math.floor(Date.now()/1000));const response=await fetch(origin,{method:'POST',headers:{'Content-Type':'application/json','X-Signature-Timestamp':timestamp,'X-Signature-Ed25519':sign(null,Buffer.from(timestamp+rawBody),privateKey).toString('hex')},body:rawBody});const initial=await response.json();if(response.status!==200)throw Error(`Bot HTTP ${response.status}`);const result=[5,6].includes(initial.type)?await wait(()=>replies.get(token),'deferred reply'):initial.data;return result;}
 const command=(name,action,options=[])=>({type:2,data:{name,options:[{name:action,type:1,options}]}});
 const player={name:'player',type:3,value:tag};
 const text=value=>JSON.stringify(value);
 const deniedReminder=await interact({type:2,data:{name:'reminders',options:[{name:'type',type:3,value:'War'},{name:'clan',type:3,value:group}]}});
 if(deniedReminder.flags!==64||!text(deniedReminder).includes('Manage Server permission is required'))throw Error('Manual reminder lost its signed Discord permission gate');
 const remind=(type)=>interact({type:2,data:{name:'reminders',options:[{name:'type',type:3,value:type},{name:'clan',type:3,value:group}]}},actor,'32');
 const warReminder=await remind('War');
 if(warReminder.content!=='Reminder sent.'||sentReminders.length!==1||!sentReminders[0].content.includes('Missing Player')||sentReminders[0].content.includes('Finished Player'))throw Error('One-off war reminder failed '+text(warReminder));
 reminderPreparation=true;const preparation=await remind('War');
 if(preparation.content!=='Reminder sent.'||sentReminders.length!==2||!sentReminders.at(-1).content.includes('War starts <t:')||!sentReminders.at(-1).content.includes('Finished Player')||sentReminders.at(-1).content.includes('War ends'))throw Error('Preparation reminder failed');
 reminderPreparation=false;
 reminderWarActive=false;const inactive=await remind('War');if(!text(inactive).includes('No active war')||sentReminders.length!==2)throw Error('Inactive war claimed success '+text({inactive,sends:sentReminders.length}));
 reminderCwl=true;const cwl=await remind('War');if(cwl.content!=='Reminder sent.'||!sentReminders.at(-1).content.includes('(1/1)'))throw Error('CWL reminder failed');reminderCwl=false;
 reminderCwl=true;reminderPreparation=true;const cwlPrep=await remind('War');
 if(cwlPrep.content!=='Reminder sent.'||!sentReminders.at(-1).content.includes('War starts <t:')||!sentReminders.at(-1).content.includes('(1/1)'))throw Error('CWL preparation reminder failed');
 reminderCwl=false;reminderPreparation=false;
 const raid=await remind('Clan Capital');if(raid.content!=='Reminder sent.'||!sentReminders.at(-1).content.includes('(6/6)'))throw Error('Raid reminder failed');
 reminderRaidActive=false;const noRaid=await remind('Clan Capital');if(!text(noRaid).includes('not ongoing'))throw Error('Inactive raid claimed success');
 reminderWarActive=true;reminderSendFails=true;const failed=await remind('War');if(failed.content==='Reminder sent.')throw Error('Rejected Discord send claimed success');reminderSendFails=false;
 const roster=await remind('roster');if(!text(roster).includes('Choose War'))throw Error('Roster still supported');
 const gamesStats=await fetch(`http://127.0.0.1:${port}/v2/bot/clans/${encodeURIComponent(group)}/clan-games`,{headers:{Authorization:`Bearer ${keys.API_BOT_TOKEN}`}});
 if(!gamesStats.ok||!Array.isArray((await gamesStats.json()).items))throw Error('Clan Games API unavailable');
 const now=new Date(),gamesStart=Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),22,8),gamesEnd=Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),28,8);
 if(Date.now()<gamesStart||Date.now()>=gamesEnd){const games=await remind('Clan Games');if(!text(games).includes('Clan Games is not ongoing'))throw Error('Inactive Clan Games claimed success');}
 console.log(JSON.stringify({manualReminders:'passed',checks:['permission gate','no saved configuration','actual channel send','finished players omitted','regular preparation roster and start time','inactive war','CWL orientation and limit','CWL preparation','raid','inactive raid','Discord rejection','roster removed'],discordWrites:0}));
 if(!process.argv.includes('--reminders-only')){
 const next=value=>value.components?.flatMap(row=>row.components??[]).find(item=>item.label==='Next'&&!item.disabled)?.custom_id;
 const click=(custom_id,who=actor)=>interact({type:3,data:{custom_id,component_type:2}},who);
 if(process.argv.includes('--public-controls-only')){
  const groupBoard=await interact(command('ranked','group',[player]));
  const nextBoard=await click(next(groupBoard),other);
  if(nextBoard.flags===64||!text(nextBoard).includes('Current Member 16'))throw Error('Public pagination is actor-locked');
  const lookup=await interact(command('player','lookup',[player]));
  const select=lookup.components.flatMap(row=>row.components??[]).find(item=>item.type===3);
  if(!select)throw Error('Player page selector missing');
  const troops=await interact({type:3,data:{custom_id:select.custom_id,component_type:3,values:['troops']}},other);
  if(troops.flags===64||!text(troops).includes('Troops'))throw Error('Public player dropdown is actor-locked');
  const back=troops.components.flatMap(row=>row.components??[]).find(item=>item.type===3);
  const overview=await interact({type:3,data:{custom_id:back.custom_id,component_type:3,values:['overview']}},actor);
  if(overview.flags===64||!text(overview).includes('Current Player'))throw Error('Original viewer cannot reuse updated dropdown');
  console.log(JSON.stringify({checks:['other viewer public pagination','other viewer player dropdown','original viewer can reuse updated controls','manual reminder permissions retained'],discordWrites:0}));
 }else{
 const current=await interact(command('ranked','search',[player]));if(!text(current).includes(`Current season ${currentSeason}`)||!text(current).includes('5 attacks'))throw Error('Current tournament selection failed: '+text(current)+' '+logs.slice(-2500));
 const currentGroup=await interact(command('ranked','group',[player]));const groupPage=await click(next(currentGroup));if(!text(groupPage).includes('Current Member 16'))throw Error('Current group pagination failed');
 if(betaInventory){
  const lookup=await interact(command('player','lookup',[player]));
  const resolved={};
  for(const name of ['pekka','war_star','th16','blue_1']){
   const item=emojiItems.find(item=>item.name===name);const rendered=`<${item.animated?'a':''}:${item.name}:${item.id}>`;
   if(!text(name==='blue_1'?currentGroup:lookup).includes(rendered))throw Error(`Actual local command did not emit Beta emoji ${name}`);
   resolved[name]=item.id;
  }
  console.log(JSON.stringify({betaEmojiRouteProof:{applicationId:app,inventoryCount:emojiItems.length,resolved,source:'live read-only application inventory',playerData:'synthetic name-normalization fixture',discordWrites:0,visualRenderingVerified:false}}));
 }
 const sharedGroup=await click(next(currentGroup),other);if(sharedGroup.flags===64||!text(sharedGroup).includes('Current Member 16'))throw Error('Another viewer cannot paginate public rankings');
 const sharedLookup=await interact(command('player','lookup',[player]));
 const sharedSelect=sharedLookup.components.flatMap(row=>row.components??[]).find(item=>item.type===3);
 if(!sharedSelect)throw Error('Player page selector missing');
 const sharedTroops=await interact({type:3,data:{custom_id:sharedSelect.custom_id,component_type:3,values:['troops']}},other);
 if(sharedTroops.flags===64||!text(sharedTroops).includes('Troops'))throw Error('Another viewer cannot select a public player page');
 const history=await interact(command('ranked','history',[player]));const historyPage=await click(next(history));if(text(history)===text(historyPage)||!text(historyPage).includes('Page 2/3'))throw Error('History pagination failed: '+text(history)+' '+text(historyPage));
 const historical=await interact(command('ranked','search',[player,{name:'season',type:3,value:String(historySeasons[0])}]));if(!text(historical).includes('Recorded tournament results')||text(historical).includes(`Current season ${currentSeason}`))throw Error('Explicit historical season selection failed');
 const accounts=await interact(command('player','accounts'));const accountPage=await click(next(accounts));if(!text(accountPage).includes('Page 2/3')||!text(accountPage).includes('Account 16'))throw Error('Linked account pagination failed');
 const library=await interact(command('army','share'));const libraryPage=await click(next(library));if(!text(libraryPage).includes('Page 2/2')||!text(libraryPage).includes('Army 26'))throw Error('Army page 2 missing');
 const select=libraryPage.components[0].components[0];const selected=await interact({type:3,data:{custom_id:select.custom_id,component_type:3,values:[select.options.at(-1).value]}});if(!text(selected).includes('Copy Army'))throw Error('Saved army selection failed');
 if((await db.query('SELECT count(*)::int count FROM user_saved_armies WHERE user_id=$1',[actor])).rows[0].count!==30)throw Error('Pagination duplicated army library');
 // Multiple signed HTTP interactions create different REST clients. The real
 // Worker must reuse its application's inventory, not reload it per command.
 if(emojiInventoryRequests!==1)throw Error(`Expected one inventory read across interactions, got ${emojiInventoryRequests}`);
 console.log(JSON.stringify({emojiCache:{inventoryRequests:emojiInventoryRequests,scope:'one application across signed HTTP interactions',discordWrites:0}}));
 console.log(JSON.stringify({checks:['manual reminder denied without Manage Server','current tournament from official profile and group','current group page2','other viewer public pagination and dropdown','35 retained seasons paginated','explicit historical season preserved','35 accounts paginated','30 saved armies paginated','page2 army selected without duplicate library'],providerRequests:live.length,ports:{api:port,bot:new URL(origin).port}}));
 }
 }
}finally{
 if(bot)await bot.dispose().catch(()=>{});if(api&&api.exitCode===null){api.kill('SIGTERM');await Promise.race([new Promise(r=>api.once('exit',r)),new Promise(r=>setTimeout(r,5000))]);}
 if(ownsRecords){await db.query('DELETE FROM ranked_league_group_members WHERE player_tag=$1',[tag]);await db.query('DELETE FROM player_links WHERE user_id=ANY($1::text[])',[[actor,other]]);await db.query('DELETE FROM auth_users WHERE user_id=ANY($1::text[])',[[actor,other]]);}await db.end();await new Promise(r=>provider.close(r));
}
