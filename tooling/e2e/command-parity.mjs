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
const fixtureNow=Math.floor(Date.now()/1000)*1000,fixtureEnd=new Date(fixtureNow+3600000).toISOString(),fixturePrep=new Date(fixtureNow-86400000).toISOString();
let privateWar=false,opponentNextWar=false,warEnded=false,cwlGap=false;
const posterMode=process.argv.includes("--poster-only");
const memberMode=process.argv.includes("--members-only");
const todoMode=process.argv.includes("--todo-only");let legendFails=false;
const sentReminders=[];
const roleMode=process.argv.includes('--roles-only'),roleServer='999999999999996510';
const botRole='999999999999996520',newRole='999999999999996521',oldRole='999999999999996522',unmanagedRole='999999999999996523';
const memberRoles=new Set([oldRole,unmanagedRole]),roleWrites=[];
let nickname='Original nickname';
const roleDefinitions=[{id:roleServer,name:'@everyone',position:0,permissions:'0'},
 {id:botRole,name:'Bot',position:10,permissions:String((1<<28)+(1<<27))},
 {id:newRole,name:'TH16',position:2,permissions:'0'},
 {id:oldRole,name:'TH15',position:1,permissions:'0'},
 {id:unmanagedRole,name:'Unmanaged',position:3,permissions:'0'}];
const provider=createServer(async(req,res)=>{
 let text='';for await(const chunk of req)text+=chunk;
 const url=new URL(req.url,'http://provider');live.push(url.pathname+url.search);res.setHeader('Content-Type','application/json');
 if(roleMode&&url.pathname===`/api/v10/guilds/${roleServer}`)return res.end(JSON.stringify({id:roleServer,owner_id:other}));
 const p=decodeURIComponent(url.pathname),endTime=fixtureEnd;
 if(memberMode&&(p===`/v1/clans/${group}`||p==='/v1/clans/#PYLQGRJJ'))return res.end(JSON.stringify({tag:p.split('/').at(-1),name:'Report Clan',memberList:[{tag,name:'Member Sixteen',townHallLevel:16,trophies:6000,role:'leader',leagueTier:{name:'Legend I'}},...(p.endsWith(group)?[{tag:tags[1],name:'Member Eighteen',townHallLevel:18,trophies:5000,role:'member',leagueTier:{name:'Legend II'}}]:[])]}));

 const startTime=new Date(Date.now()+1800000).toISOString(),warState=warEnded?'warEnded':reminderPreparation?'preparation':'inWar';
 const own={tag:group,name:'Reminder Clan',stars:5,destructionPercentage:80,members:[{tag,name:'Missing Player',townhallLevel:16,mapPosition:1,attacks:[]},{tag:tags[1],name:'Finished Player',townhallLevel:16,mapPosition:2,attacks:[{attackerTag:tags[1],defenderTag:'#PYLR',stars:3,destructionPercentage:100,order:1},{attackerTag:tags[1],defenderTag:'#PYLQ',stars:2,destructionPercentage:80,order:2}]}]};
 const opponent={tag:'#PYLQGRJJ',name:'Other Clan',stars:3,destructionPercentage:50,members:[]};
 const warBody={state:warState,teamSize:2,preparationStartTime:fixturePrep,startTime:startTime.replace(/[-:]/g,''),endTime,attacksPerMember:2,clan:own,opponent};
 if(p===`/v1/clans/${group}/currentwar`&&privateWar){res.statusCode=403;return res.end('{}');}
 if(p==='/v1/clans/#PYLQGRJJ/currentwar')return res.end(JSON.stringify({...warBody,endTime:opponentNextWar?new Date(fixtureNow+7200000).toISOString():endTime}));
 if(p===`/v1/clans/${group}/currentwar`)return res.end(JSON.stringify(reminderWarActive&&!reminderCwl?warBody:{state:'notInWar'}));
 if(p===`/v1/clans/${group}/currentwar/leaguegroup`||p==='/v1/clans/#PYLQGRJJ/currentwar/leaguegroup')return res.end(JSON.stringify({state:reminderCwl?'inWar':'notInWar',season:new Date().toISOString().slice(0,7),clans:[{tag:group,name:own.name},{tag:opponent.tag,name:opponent.name}],rounds:reminderCwl?[...(cwlGap?[{warTags:['#0']}]:[]),{warTags:['#PYLQGRJQ']}]:[]}));
 if(p==='/v1/clanwarleagues/wars/#PYLQGRJQ')return res.end(JSON.stringify({...warBody,attacksPerMember:1,clan:opponent,opponent:own}));
 if(p==='/v1/clans/#PYLQGRJJ')return res.end(JSON.stringify({tag:opponent.tag,name:opponent.name,warLeague:{id:48000019,name:'Champion League I'},memberList:[]}));
 if(p===`/v1/clans/${group}`)return res.end(JSON.stringify({tag:group,name:'Reminder Clan',warLeague:{id:48000019,name:'Champion League I'},memberList:[{tag,name:'Missing Player',townHallLevel:16},{tag:tags[1],name:'Finished Player',townHallLevel:16}]}));
 if(p===`/v1/clans/${group}/capitalraidseasons`)return res.end(JSON.stringify({items:reminderRaidActive?[{state:'ongoing',endTime,members:[{tag:tags[1],attacks:6,attackLimit:5,bonusAttackLimit:1}]}]:[]}));
 if(url.pathname.startsWith('/v1/players/')){const playerTag=decodeURIComponent(url.pathname.split('/').at(-1));return res.end(JSON.stringify({tag:playerTag,name:playerTag===tag?'Current Player':`Account ${tags.indexOf(playerTag)+1}`,townHallLevel:memberMode&&playerTag===tags[1]?18:16,trophies:5500,warStars:100,expLevel:250,donations:50,donationsReceived:40,currentLeagueGroupTag:group,currentLeagueSeasonId:currentSeason,leagueTier:{id:todoMode&&playerTag===tags[0]?105000036:tier,name:'Current League'},...(todoMode?{clan:{tag:group,name:'Reminder Clan'}}:{}),
 // Deliberately synthetic name input exercises the normal lookup renderer; this is not real player data.
 ...(betaInventory?{heroes:[{name:'P.E.K.K.A.',level:15}]}:{})}));}
 if(url.pathname===`/v1/leaguegroup/${encodeURIComponent(group)}/${currentSeason}`||decodeURIComponent(url.pathname)===`/v1/leaguegroup/${group}/${currentSeason}`){
  if(url.searchParams.get('playerTag')!==tag&&!(todoMode&&tags.includes(url.searchParams.get('playerTag')))){res.statusCode=400;return res.end('{}');}
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
 const env={PATH:process.env.PATH,HOME:process.env.HOME,TMPDIR:process.env.TMPDIR,CLASHKING_PERSISTENT_LOCAL_API:'1',CLASHKING_LOCAL_DATABASE_URL:database,CLASHKING_LOCAL_API_PORT:String(port),CLASHKING_LOCAL_DISCORD_CLIENT_ID:app,CLASHKING_LOCAL_DISCORD_TEST_ORIGIN:`http://127.0.0.1:${providerPort}`,CLASHKING_LOCAL_DISCORD_CLIENT_SECRET:'local-only',CLASHKING_LOCAL_DISCORD_PUBLIC_KEY:publicHex,CLASHKING_LOCAL_ARCHIVE_BRIDGE:'0',CLASHKING_LOCAL_CLASH_PROXY_ORIGIN:`http://127.0.0.1:${providerPort}`,CLASHKING_LOCAL_STATIC_ASSETS_ROOT:join(assetsRepo,'assets/static_data'),CLASHKING_LOCAL_STORAGE_ROOT:join(directory,'storage'),...Object.fromEntries(Object.entries(keys).map(([key,value])=>[`CLASHKING_LOCAL_${key}`,value]))};
 api=spawn(process.execPath,['scripts/start-local-rewrite-api.mjs'],{cwd:apiRepo,env,stdio:['ignore','pipe','pipe']});api.stdout.on('data',data=>logs+=data);api.stderr.on('data',data=>logs+=data);
 // Health can become ready before static metadata is seeded. Army previews
 // exercise that metadata, so do not race the real launcher's second phase.
 await wait(async()=>{try{return logs.includes('local_static_assets_seeded')&&(await fetch(`http://127.0.0.1:${port}/v2/health`)).ok;}catch{return false;}},'API and static assets startup');
 const bundle=await bundleWorker();
 if(roleMode){
  const entry=bundle.modules[0],name=/([a-zA-Z0-9_]+) as default/.exec(entry.contents)?.[1];
  if(!name)throw Error('Cannot identify compiled worker export');
  entry.contents+=`\nconst originalScheduled = ${name}.scheduled; ${name}.scheduled = async (controller, env, context) => { try { return await originalScheduled(controller, env, { waitUntil(promise) { context.waitUntil(promise.catch(error => { console.error("scheduled_test_error",error.name,error.message); throw error; })); } }); } catch(error) { console.error("scheduled_test_error",error.name,error.message); throw error; } };`;
 }

 bot=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{name:'command-e2e',...bundle,compatibilityDate:'2026-08-22',compatibilityFlags:['nodejs_compat'],
 bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:`http://127.0.0.1:${port}`,CLASHKING_API_TOKEN:keys.API_BOT_TOKEN,DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:`${Buffer.from(app).toString('base64')}.local.token`,DISCORD_PUBLIC_KEY:publicHex},
 outboundService:async request=>{
  const url=new URL(request.url);
  if(url.hostname==='cdn.discordapp.com'&&url.pathname==='/attachments/local/evidence.png')return new Response(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aXZkAAAAASUVORK5CYII=','base64'),{headers:{'Content-Type':'image/png'}});
  if(url.hostname==='assets.clashk.ing'&&/^\/static_data\/(troops|spells|heroes|pets|equipment|buildings|league_tiers)\.json$/u.test(url.pathname))return new Response(readFileSync(join(assetsRepo,'assets',url.pathname)),{headers:{'Content-Type':'application/json'}});
  if(url.hostname==='discord.com'){
   if(roleMode){
    if(url.pathname==='/api/v10/users/@me')return Response.json({id:app});
    if(url.pathname===`/api/v10/guilds/${roleServer}`)return Response.json({id:roleServer,owner_id:other});
    if(url.pathname===`/api/v10/guilds/${roleServer}/roles`)return Response.json(roleDefinitions);
    if(url.pathname===`/api/v10/guilds/${roleServer}/members/${app}`)return Response.json({user:{id:app,bot:true},roles:[botRole]});
    if(url.pathname===`/api/v10/guilds/${roleServer}/members/${actor}`){
     if(request.method==='GET')return Response.json({user:{id:actor,username:'Local'},nick:nickname,roles:[...memberRoles]});
     if(request.method==='PATCH'){nickname=(await request.json()).nick;roleWrites.push({kind:'nickname',value:nickname});return Response.json({});}
    }
    const change=new RegExp(`/guilds/${roleServer}/members/${actor}/roles/([0-9]+)$`).exec(url.pathname);
    if(change){if(request.method==='PUT')memberRoles.add(change[1]);else if(request.method==='DELETE')memberRoles.delete(change[1]);else throw Error('Unexpected role method');roleWrites.push({kind:request.method,role:change[1]});return new Response(null,{status:204});}
   }
   if(request.method==='GET'&&url.pathname.endsWith('/emojis')){emojiInventoryRequests++;return Response.json({items:emojiItems});}
   if(request.method==='GET'&&url.pathname.includes('/channels/'))return Response.json({id:url.pathname.split('/').at(-1),guild_id:'999999999999996510',type:0});
   if(request.method==='POST'&&url.pathname.endsWith('/messages')){if(reminderSendFails)return Response.json({message:'Missing permissions'},{status:403});sentReminders.push(await request.json());return Response.json({id:'999999999999996999'});}
   const token=url.pathname.split('/')[5];let data;
   if(request.headers.get('content-type')?.startsWith('multipart/form-data')){
    const form=await request.formData();data=JSON.parse(form.get('payload_json'));
    const file=form.get('files[0]');if(!file)throw Error('Missing poster attachment');
    const bytes=Buffer.from(await file.arrayBuffer());
    if(bytes.subarray(0,8).toString('hex')!=='89504e470d0a1a0a'||bytes.readUInt32BE(16)!==1600||bytes.readUInt32BE(20)!==1100)throw Error('Invalid poster PNG');
    data.posterBytes=bytes.length;
   }else data=await request.json();replies.set(token,data);return Response.json({id:'999999999999996999'});
  }
  // Keep the actual cron consumer from claiming other development users' jobs.
  // Only the local harness adds this existing API filter; production code is unchanged.
  if(roleMode&&url.hostname==='127.0.0.1'&&url.pathname==='/v2/bot/role-refresh/claim'){
   const body=await request.json();body.serverId=roleServer;
   const headers=new Headers(request.headers);headers.delete('content-length');
   return fetch(request.url,{method:'POST',headers,body:JSON.stringify(body)});
  }
  if(todoMode&&legendFails&&url.pathname==='/v2/legends/days')return Response.json({message:'Temporarily unavailable'},{status:503});
  if(url.hostname==='127.0.0.1'&&url.port===String(port))return fetch(request.url,{method:request.method,headers:Object.fromEntries(request.headers),body:['GET','HEAD'].includes(request.method)?undefined:await request.arrayBuffer()});
  throw Error('External request blocked by local integration harness');
 }}]}));
 const origin=new URL('/interactions',String(await bot.ready)).href;
 async function interact(data,who=actor,permissions='0'){const token=String(counter++);const rawBody=JSON.stringify({id:token,application_id:app,guild_id:'999999999999996510',channel_id:'999999999999996511',member:{user:{id:who,username:'Local'},roles:[],permissions},version:1,token,...data});const timestamp=String(Math.floor(Date.now()/1000));const response=await fetch(origin,{method:'POST',headers:{'Content-Type':'application/json','X-Signature-Timestamp':timestamp,'X-Signature-Ed25519':sign(null,Buffer.from(timestamp+rawBody),privateKey).toString('hex')},body:rawBody});const initial=await response.json();if(response.status!==200)throw Error(`Bot HTTP ${response.status}`);const result=[5,6].includes(initial.type)?await wait(()=>replies.get(token),'deferred reply'):initial.data;return result;}
 const command=(name,action,options=[])=>({type:2,data:{name,options:[{name:action,type:1,options}]}});
 const player={name:'player',type:3,value:tag};
 const text=value=>JSON.stringify(value);
 if(posterMode){
  if((await db.query('SELECT 1 FROM battles_ranked WHERE player_tag=$1',[tag])).rowCount)throw Error('Synthetic Legend rows already exist');
  try{
   const missing=await interact(command('legends','poster',[player]));
   if(!text(missing).includes('No recorded Legend battles'))throw Error('Missing history did not return a clear status '+text(missing));
   await db.query("INSERT INTO battles_ranked(player_tag,opponent_tag,battle_time,direction,battle_mode,player_town_hall,opponent_town_hall,stars,destruction_percentage,duration_seconds,looted_resources) VALUES($1,'#PYLQGRJ',now(),1,2,18,18,3,100,90,'{}')",[tag]);
   const poster=await interact(command('legends','poster',[player]));
   if(!poster.posterBytes||poster.embeds?.length)throw Error('Expected standalone poster '+text(poster));
   const refresh=poster.components[0].components[0].custom_id;
   if(!refresh.includes(':today:'))throw Error('Default poster date was pinned');
   const updated=await interact({type:3,data:{custom_id:refresh,component_type:2}},other);
   if(!updated.posterBytes)throw Error('Public poster refresh failed '+text(updated));
   const selectedDay=new Date(Date.now()-(5*60+10)*60000).toISOString().slice(0,10);
   const dated=await interact(command('legends','poster',[player,{name:'day',type:3,value:selectedDay}]));
   if(!dated.components[0].components[0].custom_id.includes(`:${selectedDay}:`))throw Error('Explicit date lost from refresh');
   const datedRefresh=await interact({type:3,data:{custom_id:dated.components[0].components[0].custom_id,component_type:2}},other);
   if(!datedRefresh.posterBytes)throw Error('Explicit-date refresh failed');
   const standard=await interact(command('legends','player',[player]));
   if(!standard.posterBytes||!standard.embeds?.some(embed=>embed.title==='Legend Day'))throw Error('Existing player day view regressed '+text(standard));
   const bad=await interact(command('legends','poster',[player,{name:'day',type:3,value:'2026-02-31'}]));
   if(!text(bad).includes('Choose a day in the current Legend season'))throw Error('Invalid date was accepted');
   console.log(JSON.stringify({poster:'passed',checks:['empty history status','actual API and SQL Legend series','WASM PNG 1600x1100','standalone image','public refresh','explicit date retained','existing player day view','invalid date rejected'],visualInspection:false,externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM battles_ranked WHERE player_tag=$1',[tag]);}
 }else if(memberMode){
  const server='999999999999996510';
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']])).rowCount)throw Error('Synthetic member report data exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Member reports')",[server]);
  try{
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Report Clan',true,0,2,'',0,0),('#PYLQGRJJ','Second Report',true,0,1,'',0,0)",[group]);
   await db.query("INSERT INTO server_clans(tag,server_id) VALUES($1,$2),('#PYLQGRJJ',$2)",[group,server]);
   const clanOption={name:'clan',type:3,value:group};
   const composition=await interact(command('clan','compo',[clanOption]));
   if(!text(composition).includes('TH18')||!text(composition).includes('TH16'))throw Error('Clan composition failed');
   const family=await interact(command('family','compo'));
   if(!text(family).includes('2 members'))throw Error('Family duplicated a player appearing in two clan snapshots');
   const sorted=await interact(command('clan','sorted',[clanOption,{name:'sort_by',type:3,value:'townhall'},{name:'sort_order',type:3,value:'asc'},{name:'limit',type:4,value:1}]));
   if(!text(sorted).includes('Member Sixteen')||text(sorted).includes('Member Eighteen'))throw Error('Sort direction/limit failed');
   const filtered=await interact(command('family','sorted',[{name:'sort_by',type:3,value:'war_stars'},{name:'townhall',type:4,value:18}]));
   if(!text(filtered).includes('100')||!text(filtered).includes('1/1 players'))throw Error('Full-profile statistic or Town Hall filter failed');
   const id=sorted.components[0].components[0].custom_id;
   const refreshed=await interact({type:3,data:{custom_id:id,component_type:2}},other);
   if(!text(refreshed).includes('Member Sixteen'))throw Error('Member report refresh failed');
   console.log(JSON.stringify({memberReports:'passed',checks:['clan composition','deduplicated family composition','ascending sort and limit','live-profile metric','Town Hall filter','public refresh'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']]);}
 }else if(todoMode){
  if((await db.query('SELECT 1 FROM player_stat_changes WHERE player_tag=ANY($1::text[])',[tags])).rowCount)throw Error('Synthetic task stats already exist');
  try{
   const now=new Date(),gamesAt=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),22,9));
   await db.query("INSERT INTO player_stat_changes(player_tag,event_time,stat_type,previous_value,current_value,delta) VALUES($1,date_trunc('month',now())+interval '1 hour','season_pass',0,1200,1200),($1,date_trunc('month',now())-interval '1 day','season_pass',0,999,999),($2,date_trunc('month',now())+interval '1 hour','season_pass',0,4000,4000),($1,$3,'clan_games',0,1500,1500),($1,now()-interval '2 days','capital_gold_donated',0,100,100)",[tags[0],tags[1],gamesAt]);
   const response=await fetch(`http://127.0.0.1:${port}/v2/bot/players/task-progress`,{method:'POST',headers:{Authorization:`Bearer ${keys.API_BOT_TOKEN}`,'Content-Type':'application/json'},body:JSON.stringify({tags:[tags[0],tags[2]]})});
   const progress=await response.json();if(!response.ok||progress.items[0].seasonPoints!==1200||progress.items[1].seasonPoints!==null)throw Error('Calendar task progress failed '+text(progress));
   if(gamesAt<now&&progress.items[0].clanGamesPoints!==1500)throw Error('Clan Games calendar window failed');
   const todo=await interact(command('player','to-do',[{name:'season_goal',type:4,value:2000}]));
   if(!text(todo).includes('1200/2000 observed points')||!text(todo).includes('Ranked attacks left')||!text(todo).includes('Legend attacks left')||!text(todo).includes('Last recorded capital donation'))throw Error('Expanded to-do failed '+text(todo));
   const completed=await interact(command('player','to-do',[{name:'season_goal',type:4,value:2000},{name:'show_completed',type:5,value:true}]));
   if(!text(completed).includes('0/2 war/CWL attacks left')||!text(completed).includes('0/6 raid attacks left')||!text(completed).includes('4000/2000 observed points'))throw Error('Completed goals were not retained when requested');
   const next=todo.components.flatMap(row=>row.components??[]).find(item=>item.label==='Next'&&!item.disabled);
   if(!next||!next.custom_id.includes(':2000:'))throw Error('To-do goal lost from controls');
   await interact({type:3,data:{custom_id:next.custom_id,component_type:2}});
   legendFails=true;
   const degraded=await interact(command('player','to-do',[{name:'season_goal',type:4,value:2000}]));
   if(!text(degraded).includes('Legend attacks unavailable')||!text(degraded).includes('raid attacks left')||!text(degraded).includes('1200/2000 observed points'))throw Error('Legend failure erased other tasks');
   console.log(JSON.stringify({todo:'passed',checks:['calendar season points exclude earlier month','missing observations stay unknown','daily Legend vs weekly Ranked','explicit season target','capital donation age','goal survives pagination','Legend failure preserves other tasks'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM player_stat_changes WHERE player_tag=ANY($1::text[])',[tags]);}
 }else if(process.argv.includes('--wars-only')){
  const clan={name:'clan',type:3,value:group};
  const search=(name,opts=[])=>interact(command(name,'search',[clan,...opts]));
  const regular=await search('war');if(!text(regular).includes('Reminder Clan vs Other Clan')||!text(regular).includes('2/4'))throw Error('Regular war overview failed '+text(regular));
  const roster=await search('war',[{name:'view',type:3,value:'roster'}]);if(!text(roster).includes('Missing Player'))throw Error('War roster failed');
  const attacks=await search('war',[{name:'view',type:3,value:'attacks'}]);if(!text(attacks).includes('No attacks used')||!text(attacks).includes('100%'))throw Error('War attacks failed');
  const refresh=regular.components[0].components[0].custom_id;
  const refreshed=await interact({type:3,data:{custom_id:refresh,component_type:2}},other);if(!text(refreshed).includes('Reminder Clan'))throw Error('Public war refresh failed');
  if((await db.query('SELECT 1 FROM war_schedule WHERE source_clan_tag=$1 OR opponent_tag=$1',[group])).rowCount)throw Error('Synthetic war pointer already exists');
  try{
   await db.query("INSERT INTO war_schedule(schedule_key,source_clan_tag,opponent_tag,prep_time,end_time,next_run_at,war_type) VALUES('test-war-command',$1,'#PYLQGRJJ',$2,$3,now(),'random')",[group,fixturePrep,fixtureEnd]);
   privateWar=true;
   const discovered=await search('war');if(!text(discovered).includes('Reminder Clan vs Other Clan'))throw Error('Exact opponent discovery failed');
   opponentNextWar=true;
   const rejected=await search('war');if(!text(rejected).includes('war log is private'))throw Error('Stale opponent war was accepted');
  }finally{await db.query("DELETE FROM war_schedule WHERE schedule_key='test-war-command'");}
  reminderCwl=true;
  const cwl=await search('war');if(!text(cwl).includes('CWL')||!text(cwl).includes('2/2'))throw Error('Private regular war blocked CWL '+text(cwl));
  warEnded=true;
  const standings=await search('cwl');if(!text(standings).includes('15')||!text(standings).includes('Other Clan'))throw Error('CWL win bonus/standings failed '+text(standings));
  const round=await search('cwl',[{name:'round',type:4,value:1}]);if(!text(round).includes('Round 1'))throw Error('CWL round selection failed');
  cwlGap=true;
  const unavailable=await search('cwl',[{name:'round',type:4,value:1}]);if(!text(unavailable).includes('not available yet'))throw Error('Missing CWL round shifted numbering');
  const secondRound=await search('cwl',[{name:'round',type:4,value:2}]);if(!text(secondRound).includes('Round 2'))throw Error('CWL round 2 was lost');
  const oldEnd=new Date(fixtureNow-2*86400000).toISOString(),oldStart=new Date(fixtureNow-3*86400000).toISOString(),oldPrep=new Date(fixtureNow-4*86400000).toISOString();
  const archivedSide=(sideTag,name,stars)=>({tag:sideTag,name,badgeToken:'',clanLevel:1,attacks:0,stars,destructionPercentage:stars?100:0,members:[]});
  const archived={state:'warEnded',teamSize:2,attacksPerMember:2,preparationStartTime:oldPrep,startTime:oldStart,endTime:oldEnd,battleModifier:'none',clan:archivedSide(group,'Archived Clan',6),opponent:archivedSide('#PYLQGRJJ','Archived Opponent',0)};
  const row=(await db.query("INSERT INTO wars(clan_tag,opponent_tag,prep_time,start_time,end_time,size,war_type,state) VALUES($1,'#PYLQGRJJ',$2,$3,$4,2,'random','warEnded') RETURNING war_id",[group,oldPrep,oldStart,oldEnd])).rows[0];
  try{
   await db.query('INSERT INTO war_archive_pending(war_id,end_time,payload) VALUES($1,$2,$3)',[row.war_id,oldEnd,JSON.stringify(archived)]);
   const endCode=oldEnd.replace(/[-:]/g,'');
   const history=await search('war',[{name:'war_end',type:3,value:endCode}]);
   if(!text(history).includes('Archived Clan vs Archived Opponent'))throw Error('Explicit archived war did not load');
   const suggestions=await interact({type:4,data:{name:'war',options:[{name:'search',type:1,options:[clan,{name:'war_end',type:3,value:'',focused:true}]}]}});
   if(!suggestions.choices.some(choice=>choice.value===endCode))throw Error('Archived war autocomplete missing');
   const missingSeason=await search('cwl',[{name:'season',type:3,value:'2000-01'}]);
   if(!text(missingSeason).includes('No Clan War League group'))throw Error('Historical CWL silently selected current season');
  }finally{await db.query('DELETE FROM wars WHERE war_id=$1 AND end_time=$2',[row.war_id,oldEnd]);}
  const familyServer='999999999999996510';
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[familyServer])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']])).rowCount)throw Error('Synthetic family records exist');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'CWL family test')",[familyServer]);
  try{
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Reminder Clan',false,0,0,'',0,0),('#PYLQGRJJ','Other Clan',true,0,0,'',0,0)",[group]);
   await db.query("INSERT INTO server_clans(tag,server_id) VALUES($1,$2),('#PYLQGRJJ',$2)",[group,familyServer]);
   cwlGap=false;
   const countWars=()=>live.filter(path=>path.includes('/clanwarleagues/wars/')).length;
   const before=countWars();
   const familyRanks=await interact(command('cwl','rankings'));
   if(!text(familyRanks).includes('Group rank #1')||!text(familyRanks).includes('Group rank #2')||!text(familyRanks).includes('2/2 clans'))throw Error('Family CWL rankings failed '+text(familyRanks));
   if(countWars()-before!==1)throw Error('Family clans duplicated shared CWL war fetches');
   const beforeStatus=countWars(),status=await interact(command('cwl','status'));
   if(!text(status).includes('In war')||countWars()!==beforeStatus)throw Error('Family status fetched unnecessary wars');
   const control=status.components[0].components[0].custom_id;
   const reloaded=await interact({type:3,data:{custom_id:control,component_type:2}},other);
   if(!text(reloaded).includes('Family CWL status'))throw Error('Family CWL refresh failed');
  }finally{await db.query('DELETE FROM servers WHERE id=$1',[familyServer]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']]);}
  console.log(JSON.stringify({warCommands:'passed',checks:['regular overview','roster and attacks','public refresh','private exact opponent discovery','stale opponent rejected','CWL despite private regular war','CWL win bonus and round selection','family CWL rankings/status and refresh','shared group fetched once','missing CWL round preserves numbering','stored war and autocomplete','explicit historical CWL never falls back to current'],externalDiscordWrites:0}));
 }else if(roleMode){
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[roleServer])).rowCount)throw Error('Synthetic role server exists');
  if((await db.query('SELECT 1 FROM discord_cache.gateway_shards WHERE application_id=$1',[app])).rowCount)throw Error('Synthetic role application exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Role refresh integration')",[roleServer]);
  try{
   const generation=randomBytes(16).toString('hex');
   await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
   await db.query('INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,$2,$3,0,$4,true,true,true)',[roleServer,JSON.stringify({owner_id:other}),app,generation]);
   await db.query('INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,$3)',[roleServer,actor,JSON.stringify({user:{id:actor},roles:[]})]);
   await db.query("INSERT INTO server_roles(server_id,type,option,role_id) VALUES($1,'townhall','16',$2),($1,'townhall','15',$3)",[roleServer,newRole,oldRole]);
   const preview=await interact({type:2,data:{name:'refresh',options:[{name:'test',type:5,value:true}]}});
   if(!text(preview).includes('1/1 refreshes completed')||roleWrites.length)throw Error('Refresh preview failed: '+text(preview));
   const applied=await interact({type:2,data:{name:'refresh'}});
   if(!text(applied).includes('1/1 refreshes completed')||!memberRoles.has(newRole)||memberRoles.has(oldRole)||!memberRoles.has(unmanagedRole)||nickname==='Original nickname')throw Error('Role/nickname application failed: '+text(applied));
   const before=roleWrites.length;
   const again=await interact({type:2,data:{name:'refresh'}});
   if(!text(again).includes('1/1 refreshes completed')||roleWrites.length!==before)throw Error('Repeated refresh changed unchanged roles');
   // A stale configured role above the bot is reported, never applied.
   roleDefinitions.find(role=>role.id===newRole).position=12;memberRoles.delete(newRole);
   const blocked=await interact({type:2,data:{name:'refresh'}});
   if(!text(blocked).includes('blocked change')||memberRoles.has(newRole))throw Error('Role hierarchy was bypassed');
   roleDefinitions.find(role=>role.id===newRole).position=2;
   memberRoles.add(oldRole);
   await db.query('UPDATE servers SET autoeval_enabled=true,auto_eval_nickname=false WHERE id=$1',[roleServer]);
   const jobId=`auto:${roleServer}:${actor}`;
   await db.query('INSERT INTO role_refresh_jobs(id,server_id,user_id) VALUES($1,$2,$3)',[jobId,roleServer,actor]);
   const scheduled=await (await bot.getWorker()).scheduled({cron:'* * * * *'});
   console.log('Scheduled response',scheduled);
   await wait(async()=>Boolean((await db.query('SELECT completed_at FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0]?.completed_at),'automatic refresh completion').catch(async error=>{console.log('Synthetic job status',(await db.query('SELECT attempts,completed_at,result,due_at FROM role_refresh_jobs WHERE id=$1',[jobId])).rows);throw error;});
   if(!memberRoles.has(newRole)||memberRoles.has(oldRole)||scheduled.outcome!=='ok')throw Error('Scheduled role refresh failed');
   console.log(JSON.stringify({roleRefresh:'passed',checks:['actual signed command/API/SQL flow','null nickname defaults','preview performs no Discord edits','role add/remove preserves unmanaged role','repeat no-op','role hierarchy protection','scheduled automatic job completion'],externalDiscordWrites:0,localProviderWrites:roleWrites.length}));
  }finally{
   await db.query('DELETE FROM servers WHERE id=$1',[roleServer]);
   await db.query('DELETE FROM discord_cache.members WHERE guild_id=$1',[roleServer]);
   await db.query('DELETE FROM discord_cache.guilds WHERE id=$1',[roleServer]);
   await db.query('DELETE FROM discord_cache.gateway_shards WHERE application_id=$1',[app]);
  }
 }else if(process.argv.includes('--moderation-only')){
  const server='999999999999996510';
  if((await db.query('SELECT player_tag FROM server_bans WHERE server_id=$1 UNION ALL SELECT tag FROM strikes WHERE server_id=$1',[server])).rowCount)throw Error('Synthetic moderation server already has records');
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount)throw Error('Synthetic moderation server already exists');
  await db.query('INSERT INTO servers(id,name) VALUES($1,$2)',[server,'Local moderation integration']);
  try{
   const reason={name:'reason',type:3,value:'Local moderation integration check'};
   const denied=await interact(command('ban','add',[player,reason]));
   if(!text(denied).includes('Manage Server permission is required'))throw Error('Moderation permission gate failed');
   const attachment={id:'999999999999996599',filename:'evidence.png',content_type:'image/png',size:68,url:'https://cdn.discordapp.com/attachments/local/evidence.png'};
   const add=command('ban','add',[player,reason,{name:'image',type:11,value:attachment.id}]);add.data.resolved={attachments:{[attachment.id]:attachment}};
   const saved=await interact(add,actor,'32');
   if(!text(saved).includes('Ban record saved'))throw Error('Ban save failed: '+text(saved));
   const row=(await db.query('SELECT reason,added_by,image FROM server_bans WHERE server_id=$1 AND player_tag=$2',[server,tag])).rows[0];
   if(row?.reason!==reason.value||row.added_by!==actor||!row.image?.startsWith(`http://127.0.0.1:${port}/v2/media/`))throw Error('Ban record or durable evidence not saved');
   const media=await fetch(row.image);if(!media.ok||(await media.arrayBuffer()).byteLength!==68)throw Error('Durable evidence unavailable');
   const updatedBan=await interact(command('ban','add',[player,reason]),actor,'32');
   if(!text(updatedBan).includes('Ban record saved')||(await db.query('SELECT image FROM server_bans WHERE server_id=$1 AND player_tag=$2',[server,tag])).rows[0]?.image!==row.image)throw Error('Ban edit discarded evidence');
   const list=await interact(command('ban','list'),actor,'32');
   const refresh=list.components?.[0]?.components?.[0]?.custom_id;
   if(!refresh||!text(list).includes(reason.value)||list.flags!==64)throw Error('Private ban list failed');
   const otherClick=await interact({type:3,data:{custom_id:refresh,component_type:2}},other,'32');
   if(!text(otherClick).includes('belongs to another user'))throw Error('Private moderation control crossed users');
   const updated=await interact({type:3,data:{custom_id:refresh,component_type:2}},actor,'32');
   if(!text(updated).includes(reason.value))throw Error('Moderation refresh failed');
   await interact(command('ban','remove',[player]),actor,'32');
   if((await db.query('SELECT 1 FROM server_bans WHERE server_id=$1',[server])).rowCount)throw Error('Ban was not removed');
   const strike=await interact(command('strike','add',[player,reason,{name:'weight',type:4,value:3},{name:'expires_in',type:4,value:2}]),actor,'32');
   const strikeRow=(await db.query('SELECT id,strike_weight,rollover_date FROM strikes WHERE server_id=$1',[server])).rows[0];
   if(!text(strike).includes('Strike added')||strikeRow?.strike_weight!==3||!strikeRow.rollover_date)throw Error('Weighted expiring strike failed: '+text(strike));
   await interact(command('strike','remove',[{name:'strike_id',type:3,value:strikeRow.id}]),actor,'32');
   if((await db.query('SELECT 1 FROM strikes WHERE server_id=$1',[server])).rowCount)throw Error('Strike was not removed');
   const links=await interact(command('link','list'));
   if(!text(links).includes('Account'))throw Error('Grouped link list failed: '+text(links));
   const modal=await interact(command('link','add'));
   // interact returns response data; a modal has a custom_id instead of a message.
   if(modal.custom_id!=='ck:link:submit')throw Error('Link add did not open modal');
   await interact(command('link','remove',[player]));
   if((await db.query('SELECT 1 FROM player_links WHERE user_id=$1 AND tag=$2',[actor,tag])).rowCount)throw Error('Grouped link removal did not unlink account');
   console.log(JSON.stringify({moderation:'passed',checks:['signed permission gate','ban create/list/refresh/remove','durable image upload and retrieval','private refresh owner','weighted expiring strike create/remove','grouped link list and modal'],discordWrites:0}));
  }finally{
   await db.query('DELETE FROM server_bans WHERE server_id=$1',[server]);
   await db.query('DELETE FROM strikes WHERE server_id=$1',[server]);
   await db.query('DELETE FROM servers WHERE id=$1',[server]);
  }
 }else{
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
 }
}catch(error){
 console.error(logs.slice(-8000));throw error;
}finally{
 if(bot)await bot.dispose().catch(()=>{});if(api&&api.exitCode===null){api.kill('SIGTERM');await Promise.race([new Promise(r=>api.once('exit',r)),new Promise(r=>setTimeout(r,5000))]);}
 if(ownsRecords){await db.query('DELETE FROM ranked_league_group_members WHERE player_tag=$1',[tag]);await db.query('DELETE FROM player_links WHERE user_id=ANY($1::text[])',[[actor,other]]);await db.query('DELETE FROM auth_users WHERE user_id=ANY($1::text[])',[[actor,other]]);}await db.end();await new Promise(r=>provider.close(r));
}
