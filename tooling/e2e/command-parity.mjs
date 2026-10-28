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
const verificationMode=process.argv.includes("--clan-verification-only");let verificationDescription="";
const rosterReadMode=process.argv.includes("--roster-commands-only");let rosterProfileFailure=false;
const helpMode=process.argv.includes("--help-only");
const warPreferenceMode=process.argv.includes("--war-preference-only");let warPreferenceFailure=false;
const summaryMode=process.argv.includes("--summary-only");
let summaryRaidStart=new Date();
const progressMode=process.argv.includes("--progress-only");
const clanReportMode=process.argv.includes("--clan-reports-only");
const familyOpsMode=process.argv.includes("--family-ops-only");
let raidSkip=false,raidFailure=false;
const raidFriday=new Date();raidFriday.setUTCDate(raidFriday.getUTCDate()-(raidFriday.getUTCDay()+2)%7);raidFriday.setUTCHours(7,0,0,0);if(raidFriday>new Date())raidFriday.setUTCDate(raidFriday.getUTCDate()-7);
const raidDate=raidFriday.toISOString().slice(0,10);
const streakMode=process.argv.includes("--streaks-only");
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
 if((memberMode||progressMode||summaryMode)&&(p===`/v1/clans/${group}`||p==='/v1/clans/#PYLQGRJJ'))return res.end(JSON.stringify({tag:p.split('/').at(-1),name:'Report Clan',memberList:[{tag,name:'Member Sixteen',townHallLevel:16,trophies:6000,role:'leader',leagueTier:{name:'Legend I'}},...(p.endsWith(group)?[{tag:tags[1],name:'Member Eighteen',townHallLevel:18,trophies:5000,role:'member',leagueTier:{name:'Legend II'}}]:[])]}));

 if(summaryMode&&p.endsWith('/capitalraidseasons')){
  if(raidFailure&&p.includes('#PYLQGRJJ')){res.statusCode=503;return res.end('{}');}
  const summaryMembers=p.includes('#PYLQGRJJ')?[{tag,name:'First',capitalResourcesLooted:33},{tag:tags[1],name:'Second',capitalResourcesLooted:222}]:[{tag,name:'First',capitalResourcesLooted:111}];
  return res.end(JSON.stringify({items:[{state:'ended',startTime:summaryRaidStart.toISOString(),endTime:new Date(+summaryRaidStart+3*86400000).toISOString(),capitalTotalLoot:333,totalAttacks:6,raidsCompleted:1,enemyDistrictsDestroyed:2,offensiveReward:1,defensiveReward:1,members:summaryMembers.map(m=>({...m,attacks:3,attackLimit:5,bonusAttackLimit:1}))}]}));
 }
 if((familyOpsMode||clanReportMode)&&p.endsWith('/capitalraidseasons')){
  if(raidFailure&&p.includes('#PYLQGRJJ')){res.statusCode=503;return res.end('{}');}
  const raid=(start,loot)=>({state:'ended',startTime:start.toISOString(),endTime:new Date(+start+3*86400000).toISOString(),capitalTotalLoot:loot,totalAttacks:6,raidsCompleted:2,enemyDistrictsDestroyed:4,offensiveReward:100,defensiveReward:20,members:[{tag, name:'Raider',attacks:6,attackLimit:5,bonusAttackLimit:1,capitalResourcesLooted:loot}]});
  return res.end(JSON.stringify({items:[raid(new Date(+raidFriday-7*86400000),999999),...(!raidSkip?[raid(raidFriday,12345)]:[])]}));
 }
 if((familyOpsMode||clanReportMode)&&(p===`/v1/clans/${group}`||p==='/v1/clans/#PYLQGRJJ'))return res.end(JSON.stringify({tag:p.split('/').at(-1),name:p.endsWith(group)?'Alpha Clan':'Beta Clan',members:20,clanPoints:p.endsWith(group)?1000:2000,clanBuilderBasePoints:500,clanCapitalPoints:300,requiredTownhallLevel:16,warLeague:{name:'Champion League I'},capitalLeague:{name:'Titan'},location:{name:'International'},memberList:[]}));
 if(clanReportMode&&p.endsWith('/warlog')){
  if(privateWar){res.statusCode=403;return res.end('{}');}
  return res.end(JSON.stringify({items:[{result:'win',endTime:fixturePrep,teamSize:2,attacksPerMember:2,clan:{tag:group,name:'Alpha Clan',stars:5,destructionPercentage:90,attacks:3},opponent:{tag:'#PYLQGRJJ',name:'Official Opponent',stars:4,destructionPercentage:85}}]}));
 }
 const startTime=new Date(Date.now()+1800000).toISOString(),warState=warEnded?'warEnded':reminderPreparation?'preparation':'inWar';
 const own={tag:group,name:'Reminder Clan',stars:5,destructionPercentage:80,members:[{tag,name:'Missing Player',townhallLevel:16,mapPosition:1,attacks:[]},{tag:tags[1],name:'Finished Player',townhallLevel:16,mapPosition:2,attacks:[{attackerTag:tags[1],defenderTag:'#PYLR',stars:3,destructionPercentage:100,order:1},{attackerTag:tags[1],defenderTag:'#PYLQ',stars:2,destructionPercentage:80,order:2}]}]};
 const opponent={tag:'#PYLQGRJJ',name:'Other Clan',stars:3,destructionPercentage:50,members:[]};
 const warBody={state:warState,teamSize:2,preparationStartTime:fixturePrep,startTime:startTime.replace(/[-:]/g,''),endTime,attacksPerMember:2,clan:own,opponent};
 if(p===`/v1/clans/${group}/currentwar`&&privateWar){res.statusCode=403;return res.end('{}');}
 if(familyOpsMode&&reminderCwl&&p==='/v1/clans/#PYLQGRJJ/currentwar')return res.end(JSON.stringify({state:'notInWar'}));
 if(p==='/v1/clans/#PYLQGRJJ/currentwar')return res.end(JSON.stringify({...warBody,endTime:opponentNextWar?new Date(fixtureNow+7200000).toISOString():endTime}));
 if(p===`/v1/clans/${group}/currentwar`)return res.end(JSON.stringify(reminderWarActive&&!reminderCwl?warBody:{state:'notInWar'}));
 if(p===`/v1/clans/${group}/currentwar/leaguegroup`||p==='/v1/clans/#PYLQGRJJ/currentwar/leaguegroup')return res.end(JSON.stringify({state:reminderCwl?'inWar':'notInWar',season:new Date().toISOString().slice(0,7),clans:[{tag:group,name:own.name},{tag:opponent.tag,name:opponent.name}],rounds:reminderCwl?[...(cwlGap?[{warTags:['#0']}]:[]),{warTags:['#PYLQGRJQ']}]:[]}));
 if(p==='/v1/clanwarleagues/wars/#PYLQGRJQ')return res.end(JSON.stringify({...warBody,attacksPerMember:1,clan:opponent,opponent:own}));
 if(p==='/v1/clans/#PYLQGRJJ')return res.end(JSON.stringify({tag:opponent.tag,name:opponent.name,warLeague:{id:48000019,name:'Champion League I'},memberList:[]}));
 if(p===`/v1/clans/${group}`)return res.end(JSON.stringify({tag:group,name:'Reminder Clan',description:verificationDescription,warLeague:{id:48000019,name:'Champion League I'},memberList:[{tag,name:'Missing Player',townHallLevel:16},{tag:tags[1],name:'Finished Player',townHallLevel:16}]}));
 if(p===`/v1/clans/${group}/capitalraidseasons`)return res.end(JSON.stringify({items:reminderRaidActive?[{state:'ongoing',endTime,members:[{tag:tags[1],attacks:6,attackLimit:5,bonusAttackLimit:1}]}]:[]}));
 if(url.pathname.startsWith('/v1/players/')){if((warPreferenceFailure||rosterProfileFailure)&&decodeURIComponent(url.pathname).endsWith(tags[1])){res.statusCode=503;return res.end('{}');}const playerTag=decodeURIComponent(url.pathname.split('/').at(-1));return res.end(JSON.stringify({tag:playerTag,name:playerTag===tag?'Current Player':`Account ${tags.indexOf(playerTag)+1}`,townHallLevel:memberMode&&playerTag===tags[1]?18:16,trophies:5500,warStars:100,expLevel:250,donations:50,donationsReceived:40,currentLeagueGroupTag:group,currentLeagueSeasonId:currentSeason,...(warPreferenceMode?{warPreference:playerTag===tag?'in':'out'}:{}),...(rosterReadMode?{troops:[],spells:[],heroes:[]}:{}),leagueTier:{id:todoMode&&playerTag===tags[0]?105000036:tier,name:'Current League'},...(todoMode?{clan:{tag:group,name:'Reminder Clan'}}:{}),
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
 if(verificationMode){
  const server='999999999999996510',second='999999999999996512';
  if((await db.query('SELECT 1 FROM servers WHERE id=ANY($1::text[])',[[server,second]])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=$1',[group])).rowCount)throw Error('Synthetic verification fixture exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Verification'),($2,'Other verification')",[server,second]);
  const {SignJWT}=await import(require.resolve('jose'));
  const verificationToken=await new SignJWT({}).setProtectedHeader({alg:'HS256'}).setSubject(actor).setAudience('clashking-web').setIssuedAt().setExpirationTime('10m').sign(new TextEncoder().encode(keys.JWT_ACCESS_SECRET));
  try{
   const generation=randomBytes(16).toString('hex');
   await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
   for(const id of [server,second])await db.query('INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,$2,$3,0,$4,true,true,true)',[id,JSON.stringify({owner_id:actor}),app,generation]);
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Verification',true,0,2,'',0,0)",[group]);
   await db.query('INSERT INTO server_clans(server_id,tag) VALUES($1,$3),($2,$3)',[server,second,group]);
   const call=async(id,suffix='')=>{const response=await fetch(`http://127.0.0.1:${port}/v2/server/${id}/clan/${encodeURIComponent(group)}/verification${suffix}`,{method:'POST',headers:{authorization:`Bearer ${verificationToken}`}});const value=await response.json();if(!response.ok)throw Error('Verification API '+response.status+' '+JSON.stringify(value));return value;};
   let value=await call(server);if(value.state!=='pending'||!/^[a-z]+ck$/.test(value.marker))throw Error('Challenge not issued');
   if((await call(server)).marker!==value.marker)throw Error('Pending challenge changed');
   const otherChallenge=await call(second);if(otherChallenge.marker===value.marker)throw Error('Simultaneous challenge collision');
   const seen=new Set();
   for(let n=0;n<21;n++){
    seen.add(value.marker);
    await db.query("UPDATE server_clan_verifications SET state='expired',started_at=now()-interval '3 hours',check_after=now()-interval '2 hours',expires_at=now()-interval '1 minute' WHERE server_id=$1 AND clan_tag=$2",[server,group]);
    const previous=value.marker;value=await call(server);if(value.marker===previous||value.marker===otherChallenge.marker)throw Error('Challenge rotation/collision failed');
   }
   if(seen.size!==19)throw Error('Rotation did not cover unreserved word choices');
   verificationDescription='Clan description '+value.marker;
   await db.query("UPDATE server_clan_verifications SET started_at=now()-interval '3 minutes',check_after=now()-interval '1 second',next_check_at=now()-interval '1 second' WHERE server_id=$1 AND clan_tag=$2",[server,group]);
   if((await call(server,'/check')).state!=='verified')throw Error('Description verification failed');
   console.log(JSON.stringify({clanVerification:'passed',checks:['real API/SQL','random initial challenge','stable pending challenge','cross-server collision exclusion','full word rotation/wrap','description verification'],externalDiscordWrites:0}));
  }finally{verificationDescription='';await db.query('DELETE FROM servers WHERE id=ANY($1::text[])',[[server,second]]);await db.query('DELETE FROM basic_clan WHERE tag=$1',[group]);await db.query('DELETE FROM discord_cache.guilds WHERE id=ANY($1::text[])',[[server,second]]);await db.query('DELETE FROM discord_cache.gateway_shards WHERE application_id=$1',[app]);}
 }else if(rosterReadMode){
  const server='999999999999996510',elsewhere='999999999999996512';
  if((await db.query('SELECT 1 FROM servers WHERE id=ANY($1::text[])',[[server,elsewhere]])).rowCount)throw Error('Synthetic roster server exists');
  if((await db.query('SELECT 1 FROM basic_clan WHERE tag=$1',[group])).rowCount)throw Error('Synthetic roster clan exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Roster server'),($2,'Other roster server')",[server,elsewhere]);
  const request=async(path,body)=>{const response=await fetch(`http://127.0.0.1:${port}`+path,{method:'POST',headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error('Roster API '+response.status+' '+JSON.stringify(data));return data;};
  try{
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Roster clan',true,0,2,'',0,0)",[group]);
   await db.query('INSERT INTO server_clans(server_id,tag) VALUES($1,$3),($2,$3)',[server,elsewhere,group]);
   const created=await request('/v2/roster?server_id='+server,{alias:'Visible roster',roster_type:'family',members:[{tag:tags[1],name:'Stored member',townhall:15,trophies:1}]});
   await request('/v2/roster?server_id='+elsewhere,{alias:'Other server secret',roster_type:'family',members:[{tag:tags[1],name:'Stored member',townhall:15}]});
   const list=await interact(command('roster','list'),actor,'32');if(!text(list).includes('Visible roster')||text(list).includes('Other server secret'))throw Error('Roster list scope failed: '+text(list));
   const selection=await interact({type:3,data:{custom_id:'ck:roster:select',component_type:3,values:[created.roster_id]}},actor,'32');if(!text(selection).includes('Stored member'))throw Error('Roster selection failed');
   const view=await interact(command('roster','view',[{name:'roster',type:3,value:created.roster_id}]),actor,'32');if(!text(view).includes('Stored member'))throw Error('Roster view failed');
   const search=await interact(command('roster','search',[{name:'player',type:3,value:tags[1]}]),actor,'32');
   if(!text(search).includes('Visible roster')||text(search).includes('Other server secret'))throw Error('Roster search scope failed: '+text(search));
   const own=await interact(command('roster','search'),actor,'32');if(!text(own).includes('Visible roster'))throw Error('Self roster search failed: '+text(own));
   const refreshed=await interact({type:3,data:{custom_id:search.components[0].components[0].custom_id,component_type:2}},actor,'32');if(!text(refreshed).includes('Visible roster'))throw Error('Search refresh failed');
   const denied=await interact(command('roster','refresh',[{name:'roster',type:3,value:created.roster_id}]),actor,'0');if(!text(denied).includes('Manage'))throw Error('Roster refresh permission bypass');
   rosterProfileFailure=true;
   const failed=await interact(command('roster','refresh',[{name:'roster',type:3,value:created.roster_id}]),actor,'32');if(!text(failed).includes('1 unavailable player(s) kept unchanged'))throw Error('Refresh hid upstream failure');
   if((await db.query('SELECT trophies FROM roster_members WHERE roster_id=$1 AND tag=$2',[created.roster_id,tags[1]])).rows[0]?.trophies!==1)throw Error('Failed refresh changed old profile');
   rosterProfileFailure=false;await db.query('UPDATE rosters SET last_refreshed_at=NULL WHERE id=$1',[created.roster_id]);
   const refresh=await interact(command('roster','refresh',[{name:'roster',type:3,value:created.roster_id}]),actor,'32');if(!text(refresh).includes('Roster data refreshed: 1'))throw Error('Data refresh failed: '+text(refresh));
   const row=(await db.query('SELECT townhall,trophies FROM roster_members WHERE roster_id=$1 AND tag=$2',[created.roster_id,tags[1]])).rows[0];if(row.townhall!==16||row.trophies!==5500)throw Error('Data refresh did not persist profile');
   const reused=await interact(command('roster','refresh',[{name:'roster',type:3,value:created.roster_id}]),actor,'32');if(!text(reused).includes('Recent roster data reused'))throw Error('Cooldown incorrectly reported new refresh');
   console.log(JSON.stringify({rosterReads:'passed',checks:['actual API-created rosters','server-scoped list and selection','direct view','player and self search','search refresh','permission gate','failed profile retained','actual stored profile update','cooldown reuse'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM servers WHERE id=ANY($1::text[])',[[server,elsewhere]]);await db.query('DELETE FROM basic_clan WHERE tag=$1',[group]);}
 }else if(helpMode){
  const list=await interact({type:2,data:{name:'help'}});
  if(!text(list).includes('/clan')||!text(list).includes('/link')||!text(list).includes('/help'))throw Error('Help missing current command roots');
  const detail=await interact({type:2,data:{name:'help',options:[{name:'command',type:3,value:'clan war-preference'}]}});
  if(!text(detail).includes('Required')||!text(detail).includes('townhall')||!text(detail).includes('Last preference change'))throw Error('Help detail missing real options');
  const refresh=detail.components[0].components[0].custom_id;
  if(!text(await interact({type:3,data:{custom_id:refresh,component_type:2}},other)).includes('/clan war-preference'))throw Error('Help refresh lost command');
  const root=await interact({type:2,data:{name:'help',options:[{name:'command',type:3,value:'clan'}]}});
  if(!text(root).includes('/clan summary')||!text(root).includes('/clan war-preference'))throw Error('Help group missing subcommands');
  const complete=await interact({type:4,data:{name:'help',options:[{name:'command',type:3,value:'war',focused:true}]}});
  if(!complete.choices?.some(choice=>choice.value==='clan war-preference'))throw Error('Help autocomplete missing leaf');
  const bad=await interact({type:2,data:{name:'help',options:[{name:'command',type:3,value:'not-real'}]}});
  if(!text(bad).includes('Choose a current command'))throw Error('Unknown help command accepted');
  console.log(JSON.stringify({help:'passed',checks:['current registry roots','generated required/options/choices','group children','autocomplete','public refresh retains selection','unknown command rejected'],externalDiscordWrites:0}));
 }else if(warPreferenceMode){
  const ids=[],selected=[tag,tags[1]],key='test-war-preference';
  for(const table of ['player_change_history','player_war_history','player_timers'])if((await db.query(`SELECT 1 FROM ${table} WHERE player_tag=ANY($1::text[])`,[selected])).rowCount)throw Error('Synthetic war-preference data exists');
  const endpoint=`http://127.0.0.1:${port}/v2/bot/players/war-status`;
  const request=async(body,token=keys.API_BOT_TOKEN)=>fetch(endpoint,{method:'POST',headers:{authorization:`Bearer ${token}`,'content-type':'application/json'},body:JSON.stringify(body)});
  const last=new Date(Date.now()-86400000),change=new Date(Date.now()-3600000),future=new Date(Date.now()+3600000);
  try{
   await db.query("INSERT INTO player_change_history(player_tag,event_time,change_type,previous_value,current_value) VALUES($1,$2,11,'0','1'),($1,$3,11,'1','0')",[tag,change,future]);
   for(const type of ['random','friendly'])ids.push((await db.query("INSERT INTO wars(clan_tag,opponent_tag,prep_time,start_time,end_time,size,war_type,state) VALUES($1,'#PYLQGRJJ',$2,$2,$3,2,$4,'warEnded') RETURNING war_id",[group,new Date(+last-86400000),new Date(+last+(type==='friendly'?1000:0)),type])).rows[0].war_id);
   await db.query('INSERT INTO player_war_history(player_tag,war_ids) VALUES($1,$2)',[tag,ids]);
   for(const type of ['random','cwl'])await db.query("INSERT INTO war_schedule(schedule_key,source_clan_tag,opponent_tag,prep_time,end_time,next_run_at,war_type) VALUES($1,$2,'#PYLQGRJJ',$3,$4,now(),$5)",[key+type,group,last,future,type]);
   await db.query("INSERT INTO player_timers(player_tag,event_type,event_key,expires_at) VALUES($1,'war',$2,$4),($1,'war',$3,$4),($5,'war',$2,$6),($5,'raid',$3,$4)",[tag,key+'random',key+'cwl',future,tags[1],last]);
   const data=await (await request({tags:[tag,tag,tags[1]]})).json(),row=data.items?.find(x=>x.tag===tag);
   if(data.items?.length!==2||row.lastPreferenceChange!==change.toISOString()||row.lastWarEnd!==last.toISOString()||row.timers.length!==2||!row.timers.some(x=>x.type==='cwl'))throw Error('Recorded history/timers mismatch: '+JSON.stringify(data));
   if(data.items.find(x=>x.tag===tags[1]).timers.length)throw Error('Expired or raid timer included');
   const clan={name:'clan',type:3,value:group};
   const initial=await interact(command('clan','war-preference',[clan]));
   if(!text(initial).includes('Opted in (1)')||!text(initial).includes('Opted out (1)'))throw Error('Preferences not split: '+text(initial));
   const timer=await interact(command('clan','war-preference',[clan,{name:'view',type:3,value:'timer'}]));
   if(!text(timer).includes('CWL')||!text(timer).includes('No recorded active timer'))throw Error('Timer labels missing');
   const refresh=timer.components[0].components[0].custom_id;
   if(!text(await interact({type:3,data:{custom_id:refresh,component_type:2}},other)).includes('CWL'))throw Error('Refresh did not preserve public timer view');
   warPreferenceFailure=true;
   const partial=await interact(command('clan','war-preference',[clan]));
   if(!text(partial).includes('Preference unknown (1)')||text(partial).includes('Opted out (1)'))throw Error('Unavailable player counted as opted out');
   if((await request({tags:[tag]},'invalid')).status!==401||(await request({tags:[]})).status!==400||(await request({tags:Array(101).fill(tag)})).status!==400)throw Error('War status validation failed');
   for(const message of [initial,timer,partial])if(message.embeds.reduce((n,e)=>n+(e.title?.length??0)+(e.description?.length??0)+(e.footer?.text?.length??0),0)>6000)throw Error('Discord embed limit exceeded');
   console.log(JSON.stringify({warPreference:'passed',checks:['real bot/API/SQL','latest nonfuture preference change','completed regular war excludes friendly','separate active regular/CWL timers','expired/raid timers excluded','null unknowns','unavailable profile stays unknown','public refresh preserves options','auth and bounds','Discord limits'],externalDiscordWrites:0}));
  }finally{
   warPreferenceFailure=false;
   await db.query('DELETE FROM player_change_history WHERE player_tag=ANY($1::text[])',[selected]);
   await db.query('DELETE FROM player_timers WHERE player_tag=ANY($1::text[])',[selected]);
   await db.query('DELETE FROM war_schedule WHERE schedule_key=ANY($1::text[])',[[key+'random',key+'cwl']]);
   await db.query('DELETE FROM player_war_history WHERE player_tag=ANY($1::text[])',[selected]);
   await db.query('DELETE FROM wars WHERE war_id=ANY($1::int[])',[ids]);
  }
 }else if(summaryMode){
  const server='999999999999996510',summaryTags=[tag,tags[1]],warRows=[];
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM player_war_history WHERE player_tag=ANY($1::text[])',[summaryTags])).rowCount||(await db.query('SELECT 1 FROM battles_farming WHERE player_tag=ANY($1::text[])',[summaryTags])).rowCount||(await db.query('SELECT 1 FROM battles_ranked WHERE player_tag=ANY($1::text[])',[summaryTags])).rowCount||(await db.query('SELECT 1 FROM player_stat_changes WHERE player_tag=ANY($1::text[])',[summaryTags])).rowCount||(await db.query('SELECT 1 FROM leaderboard_history_player_home WHERE player_tag=ANY($1::text[])',[summaryTags])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']])).rowCount)throw Error('Synthetic summary data exists');
  const getSummary=async()=>{const response=await fetch(`http://127.0.0.1:${port}/v2/bot/players/season-summary`,{method:'POST',headers:{Authorization:`Bearer ${keys.API_BOT_TOKEN}`,'Content-Type':'application/json'},body:JSON.stringify({tags:summaryTags,season:'2026-10'})});if(!response.ok)throw Error('Summary API '+response.status+' '+await response.text());return response.json();};
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Summary')",[server]);
  try{
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Summary Clan',true,0,2,'',0,0),('#PYLQGRJJ','Second Clan',true,0,1,'',0,0)",[group]);
   await db.query("INSERT INTO server_clans(tag,server_id) VALUES($1,$2),('#PYLQGRJJ',$2)",[group,server]);
   const window=await getSummary(),start=new Date(window.start),end=new Date(window.end);
   summaryRaidStart=new Date(+start+4*86400000);summaryRaidStart.setUTCHours(7,0,0,0);
   await db.query("INSERT INTO battles_farming(player_tag,battle_time,stars,destruction_percentage,duration_seconds,looted_resources) VALUES($1,$2,3,100,90,'{\"gold\":100,\"elixir\":200,\"darkElixir\":10}'),($1,$3,3,100,90,'{\"gold\":9999}')",[tag,new Date(+start+1000),end]);
   await db.query("INSERT INTO battles_ranked(player_tag,opponent_tag,battle_time,direction,battle_mode,player_town_hall,opponent_town_hall,stars,destruction_percentage,duration_seconds,looted_resources) VALUES($1,'#PYLR',$2,1,1,16,16,2,80,90,'{\"gold\":50,\"elixir\":20,\"darkElixir\":1}'),($1,'#PYLR',$3,2,1,16,16,3,100,90,NULL)",[tag,new Date(+start+2000),new Date(+start+3000)]);
   await db.query("INSERT INTO player_stat_changes(player_tag,clan_tag,event_time,stat_type,previous_value,current_value,delta) VALUES($1,$2,$3,'donated',0,321,321),($1,$2,$4,'capital_gold_donated',0,444,444),($5,$2,$3,'received',0,222,222)",[tag,group,new Date(+start+5000),new Date(+start+6000),tags[1]]);
   await db.query("INSERT INTO leaderboard_history_player_home(location_id,date,player_tag,player_name,exp_level,trophies,attack_wins,defense_wins,rank) VALUES('global',$1,$2,'Snapshot Player',200,1234,4,2,1)",[new Date(+start+2*86400000).toISOString().slice(0,10),tag]);
   const prep=new Date(+start+86400000).toISOString(),battleStart=new Date(+start+2*86400000).toISOString(),warEnd=new Date(+start+3*86400000).toISOString();
   const side=(sideTag,name,members)=>({tag:sideTag,name,badgeToken:'',clanLevel:1,attacks:2,stars:5,destructionPercentage:100,members});
   const archived={state:'warEnded',teamSize:2,attacksPerMember:2,preparationStartTime:prep,startTime:battleStart,endTime:warEnd,battleModifier:'none',clan:side(group,'Summary Clan',[{tag,name:'First',townhallLevel:16,mapPosition:1,attacks:[{defenderTag:'#PYLR',stars:3,destructionPercentage:100,duration:90,order:1},{defenderTag:'#PYLQ',stars:2,destructionPercentage:80,duration:90,order:2}]}]),opponent:side('#PYLQGRJJ','Second Clan',[])};
   for(const type of ['random','friendly']){const row=(await db.query("INSERT INTO wars(clan_tag,opponent_tag,prep_time,start_time,end_time,size,war_type,state) VALUES($1,'#PYLQGRJJ',$2,$3,$4,2,$5,'warEnded') RETURNING war_id",[group,prep,battleStart,new Date(Date.parse(warEnd)+(type==='friendly'?1000:0)),type])).rows[0];warRows.push({...row,endTime:new Date(Date.parse(warEnd)+(type==='friendly'?1000:0))});if(type==='random')await db.query('INSERT INTO war_archive_pending(war_id,end_time,payload) VALUES($1,$2,$3)',[row.war_id,warRows[0].endTime,JSON.stringify(archived)]);}
   await db.query('INSERT INTO player_war_history(player_tag,war_ids) VALUES($1,$2)',[tag,warRows.map(row=>row.war_id)]);
   const data=await getSummary(),first=data.items.find(row=>row.tag===tag),second=data.items.find(row=>row.tag===tags[1]);
   if(first.gold!==150||first.elixir!==220||first.darkElixir!==11||first.attacks!==2||first.wins!==2||first.donated!==321||first.capitalDonated!==444||first.warStars!==5||first.trophies!==1234||second.gold!==null||!data.warCoverageComplete)throw Error('Recorded summary mismatch '+JSON.stringify(data));
   const opts=[{name:'season',type:3,value:'2026-10'}],clan=await interact(command('clan','summary',[{name:'clan',type:3,value:group},...opts]));
   if(!text(clan).includes('150')||!text(clan).includes('1.2K'))throw Error('Clan summary missing totals '+text(clan));
   const family=await interact(command('family','summary',opts));
   if(!text(family).includes('144')||!text(family).includes('222')||!text(family).includes('2 current members'))throw Error('Family raid aggregation or member deduplication failed '+text(family));
   const refresh=family.components[0].components[0].custom_id;
   if(!refresh.includes('2026-10')||!text(await interact({type:3,data:{custom_id:refresh,component_type:2}},other)).includes('144'))throw Error('Summary refresh lost season');
   raidFailure=true;
   const partialRaid=await interact(command('family','summary',[...opts,{name:'view',type:3,value:'capital'}]));
   const lootField=partialRaid.embeds.flatMap(embed=>embed.fields??[]).find(field=>field.name.includes('looted'));
   if(!text(partialRaid).includes('raid histories incomplete')||!lootField?.value.includes('No recorded observations')||!text(partialRaid).includes('444'))throw Error('Partial raid history presented as complete');
   raidFailure=false;
   const countText=embeds=>embeds.reduce((sum,embed)=>sum+(embed.title?.length??0)+(embed.description?.length??0)+(embed.footer?.text?.length??0)+(embed.fields??[]).reduce((n,field)=>n+field.name.length+field.value.length,0),0);
   if(countText(family.embeds)>6000||family.embeds.some(embed=>(embed.fields??[]).some(field=>field.value.length>1024)))throw Error('Summary exceeds Discord limits');
   await db.query('DELETE FROM war_archive_pending WHERE war_id=$1 AND end_time=$2',[warRows[0].war_id,warRows[0].endTime]);
   const missing=await getSummary();if(missing.warCoverageComplete||missing.items.find(row=>row.tag===tag).warStars!==null||missing.items.find(row=>row.tag===tag).gold!==150)throw Error('Missing archive corrupted independent totals');
   const unauthorized=await fetch(`http://127.0.0.1:${port}/v2/bot/players/season-summary`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tags:summaryTags})});if(unauthorized.status!==401)throw Error('Summary auth missing');
   console.log(JSON.stringify({seasonSummary:'passed',checks:['farming plus ranked loot','defense excluded','exclusive season end','missing data stays null','donations and snapshot','completed non-friendly war stars','missing archive isolates metric','family deduplication','raid aggregation and partial failure','Discord message limits','refresh and authentication'],externalDiscordWrites:0}));
  }finally{
   await db.query('DELETE FROM player_war_history WHERE player_tag=ANY($1::text[])',[summaryTags]);for(const row of warRows)await db.query('DELETE FROM wars WHERE war_id=$1 AND end_time=$2',[row.war_id,row.endTime]);
   await db.query('DELETE FROM leaderboard_history_player_home WHERE player_tag=ANY($1::text[])',[summaryTags]);await db.query('DELETE FROM player_stat_changes WHERE player_tag=ANY($1::text[])',[summaryTags]);await db.query('DELETE FROM battles_farming WHERE player_tag=ANY($1::text[])',[summaryTags]);await db.query('DELETE FROM battles_ranked WHERE player_tag=ANY($1::text[])',[summaryTags]);await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']]);
  }
 }else if(progressMode){
  const server='999999999999996510';
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM player_change_history WHERE player_tag=ANY($1::text[])',[[tag,tags[1]]])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']])).rowCount)throw Error('Synthetic progress data exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Progress')",[server]);
  const requestProgress=async(body,auth=true)=>fetch(`http://127.0.0.1:${port}/v2/bot/players/upgrade-progress`,{method:'POST',headers:{'Content-Type':'application/json',...(auth?{Authorization:`Bearer ${keys.API_BOT_TOKEN}`}:{})},body:JSON.stringify(body)});
  try{
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Progress Clan',true,0,2,'',0,0),('#PYLQGRJJ','Second Clan',true,0,1,'',0,0)",[group]);
   await db.query("INSERT INTO server_clans(tag,server_id) VALUES($1,$2),('#PYLQGRJJ',$2)",[group,server]);
   const body={tags:[tag,tags[1]],type:'all',season:'2026-10'},response=await requestProgress(body),window=await response.json();
   if(!response.ok||!window.start||!window.end)throw Error('Progress window unavailable '+JSON.stringify(window));
   const start=new Date(window.start),end=new Date(window.end);
   const row=async(player,type,item,previous,current,time)=>db.query('INSERT INTO player_change_history(event_time,player_tag,change_type,item_id,townhall_level,previous_value,current_value) VALUES($1,$2,$3,$4,16,$5,$6)',[time,player,type,item,String(previous),String(current)]);
   await row(tag,3,0,10,15,start);await row(tag,5,0,1,2,new Date(+start+1000));
   await row(tag,1,0,10,11,new Date(+start+2000));await row(tag,4,0,1,2,new Date(+start+3000));await row(tag,6,0,1,2,new Date(+start+4000));
   await row(tag,2,0,0,1,new Date(+start+5000));await row(tag,3,0,15,14,new Date(+start+6000));await row(tag,3,0,15,15,new Date(+start+7000));
   await row(tag,3,0,1,50,new Date(+start-1));await row(tag,3,0,1,60,end);
   await row(tags[1],3,0,1,20,new Date(+start+8000));
   const computed=await (await requestProgress(body)).json();
   const units=computed.items.find(item=>item.tag===tag).units;
   if(units.reduce((sum,item)=>sum+item.levels,0)!==9||units.reduce((sum,item)=>sum+item.changes,0)!==5||units.some(item=>item.type===2)||units.some(item=>item.name.startsWith('Unknown')))throw Error('Upgrade boundaries or categories failed '+JSON.stringify(computed));
   const clanOpt={name:'clan',type:3,value:group},typeOpt={name:'type',type:3,value:'heroes'},seasonOpt={name:'season',type:3,value:'2026-10'};
   const clan=await interact(command('clan','progress',[clanOpt,typeOpt,seasonOpt]));
   if(!text(clan).includes('2 changes')||!text(clan).includes('+6 levels'))throw Error('Heroes/pets progress mismatch '+text(clan));
   const family=await interact(command('family','progress',[typeOpt,seasonOpt,{name:'sort_by',type:3,value:'levels'},{name:'limit',type:4,value:1}]));
   if(!JSON.stringify(family.embeds[0]).includes('Member Eighteen')||JSON.stringify(family.embeds[0]).includes('Member Sixteen')||!text(family).includes('+25 levels'))throw Error('Family deduplication/sort totals failed '+text(family));
   const filtered=await interact(command('clan','progress',[clanOpt,typeOpt,seasonOpt,{name:'townhall',type:4,value:18}]));
   if(JSON.stringify(filtered.embeds[0]).includes('Member Sixteen'))throw Error('Town Hall filter ignored');
   const refresh=family.components[0].components[0].custom_id;
   if(!refresh.includes('2026-10')||!text(await interact({type:3,data:{custom_id:refresh,component_type:2}},other)).includes('+25 levels'))throw Error('Progress refresh lost filters');
   if((await requestProgress(body,false)).status!==401||(await requestProgress({...body,tags:Array(101).fill(tag)})).status!==400)throw Error('Progress request guards failed');
   console.log(JSON.stringify({upgradeProgress:'passed',checks:['real game-season boundaries','boost/decrease/no-change excluded','events versus levels','canonical unit metadata','heroes and pets','family deduplication','sorting and limit','Town Hall filter','refresh','bot auth and batch cap'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM player_change_history WHERE player_tag=ANY($1::text[])',[[tag,tags[1]]]);await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']]);}
 }else if(clanReportMode){
  const clanOption={name:'clan',type:3,value:group},cwlId='E2Eclan00001';
  if((await db.query('SELECT 1 FROM cwl_groups WHERE cwl_id=$1',[cwlId])).rowCount)throw Error('Synthetic CWL group exists');
  if((await db.query('SELECT 1 FROM player_stat_changes WHERE player_tag=$1',[tag])).rowCount)throw Error('Synthetic contributions exist');
  const end=new Date(+raidFriday+7*86400000),before=new Date(+raidFriday-1000);
  const oldEnd=new Date(fixtureNow-2*86400000).toISOString(),oldStart=new Date(fixtureNow-3*86400000).toISOString(),oldPrep=new Date(fixtureNow-4*86400000).toISOString();
  let warRow;
  try{
   const side=(sideTag,name,stars)=>({tag:sideTag,name,badgeToken:'',clanLevel:1,attacks:2,stars,destructionPercentage:stars?100:0,members:[]});
   const archived={state:'warEnded',teamSize:2,attacksPerMember:2,preparationStartTime:oldPrep,startTime:oldStart,endTime:oldEnd,battleModifier:'none',clan:side(group,'Alpha Clan',6),opponent:side('#PYLQGRJJ','Archived Opponent',0)};
   warRow=(await db.query("INSERT INTO wars(clan_tag,opponent_tag,prep_time,start_time,end_time,size,war_type,state) VALUES($1,'#PYLQGRJJ',$2,$3,$4,2,'random','warEnded') RETURNING war_id",[group,oldPrep,oldStart,oldEnd])).rows[0];
   await db.query('INSERT INTO war_archive_pending(war_id,end_time,payload) VALUES($1,$2,$3)',[warRow.war_id,oldEnd,JSON.stringify(archived)]);
   const guardedHistory=`http://127.0.0.1:${port}/v2/clan/${encodeURIComponent(group)}/warlog`;
   if((await fetch(guardedHistory)).status!==401)throw Error('Stored war history became anonymous');
   if((await fetch(`http://127.0.0.1:${port}/v2/player/${encodeURIComponent(tag)}/last-activity`,{headers:{Authorization:`Bearer ${keys.API_BOT_TOKEN}`}})).status!==401)throw Error('Bot accessed private user activity');
   const official=await interact(command('clan','war-log',[clanOption]));
   if(!text(official).includes('Official Opponent')||!text(official).includes('3/4 attacks'))throw Error('Official war log failed '+text(official));
   privateWar=true;const stored=await interact(command('clan','war-log',[clanOption]));
   if(!text(stored).includes('Archived Opponent')||!text(stored).includes('official log is private'))throw Error('Private stored history failed');privateWar=false;
   await db.query("INSERT INTO cwl_groups(cwl_id,season,rounds,state,war_size) VALUES($1,'2026-09','[]','ended',15)",[cwlId]);
   await db.query("INSERT INTO cwl_group_clans(cwl_id,clan_tag,name) VALUES($1,$2,'Alpha Clan')",[cwlId,group]);
   const cwl=await interact(command('clan','war-log',[clanOption,{name:'view',type:3,value:'cwl'}]));
   if(!text(cwl).includes('2026-09')||!text(cwl).includes('Rank unavailable'))throw Error('Partial CWL history fabricated a rank '+text(cwl));
   const overview=await interact(command('clan','capital',[clanOption]));
   if(!text(overview).includes('12.3K')||!text(overview).includes('4 districts'))throw Error('Capital overview failed');
   const raiders=await interact(command('clan','capital',[clanOption,{name:'view',type:3,value:'raiders'}]));
   if(!text(raiders).includes('Raider')||!text(raiders).includes('6/6 attacks'))throw Error('Capital raiders failed');
   await db.query("INSERT INTO player_stat_changes(player_tag,clan_tag,event_time,stat_type,previous_value,current_value,delta) VALUES($1,$2,$3,'capital_gold_donated',0,321,321),($1,$2,$4,'capital_gold_donated',0,999,999),($1,$2,$5,'capital_gold_donated',0,888,888),($1,'#PYLQGRJJ',$6,'capital_gold_donated',0,777,777)",[tag,group,raidFriday,end,before,new Date(+raidFriday+1000)]);
   raidSkip=true;
   const donations=await interact(command('clan','capital',[clanOption,{name:'view',type:3,value:'donations'},{name:'weekend',type:3,value:raidDate}]));
   if(!JSON.stringify(donations.embeds).includes('321')||/999|888|777/.test(JSON.stringify(donations.embeds)))throw Error('Capital week/clan boundaries failed '+text(donations));
   const refresh=donations.components[0].components[0].custom_id;
   if(!refresh.includes(raidDate)||!text(await interact({type:3,data:{custom_id:refresh,component_type:2}},other)).includes('321'))throw Error('Capital refresh lost view/date');
   const filtered=await interact(command('clan','capital',[clanOption,{name:'view',type:3,value:'donations'},{name:'current_members',type:5,value:true}]));
   if(JSON.stringify(filtered.embeds).includes('321'))throw Error('Current-member filter ignored');
   const endpoint=`http://127.0.0.1:${port}/v2/bot/clans/${encodeURIComponent(group)}/capital-contributions?weekend=${raidDate}`;
   if((await fetch(endpoint)).status!==401)throw Error('Capital contributions lost bot auth');
   console.log(JSON.stringify({clanReports:'passed',checks:['official war log','history authentication and private activity guard','private-log archived fallback','partial CWL history','capital overview and raiders','Friday boundaries','clan attribution','donations without raid','current members filter','refresh','bot authentication'],externalDiscordWrites:0}));
  }finally{
   if(warRow)await db.query('DELETE FROM wars WHERE war_id=$1 AND end_time=$2',[warRow.war_id,oldEnd]);
   await db.query('DELETE FROM cwl_groups WHERE cwl_id=$1',[cwlId]);
   await db.query('DELETE FROM player_stat_changes WHERE player_tag=$1',[tag]);
  }
 }else if(familyOpsMode){
  const server='999999999999996510',statTime=new Date().toISOString();
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']])).rowCount)throw Error('Synthetic family operations data exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Family operations')",[server]);
  try{
   const cats=(await db.query("INSERT INTO server_clan_categories(server_id,name,position) VALUES($1,'Zulu group',0),($1,'Alpha group',1) RETURNING id,name",[server])).rows;
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Alpha Clan',true,0,20,'',0,0),('#PYLQGRJJ','Beta Clan',true,0,20,'',0,0)",[group]);
   await db.query("INSERT INTO server_clans(tag,server_id,category_id) VALUES($1,$2,$3),('#PYLQGRJJ',$2,$4)",[group,server,cats.find(c=>c.name==='Zulu group').id,cats.find(c=>c.name==='Alpha group').id]);
   const listing=await interact(command('family','clans'));
   if(text(listing).indexOf('Zulu group')>text(listing).indexOf('Alpha group')||!text(listing).includes('20/50'))throw Error('Configured category order lost '+text(listing));
   const stats=await interact(command('family','stats',[{name:'type',type:3,value:'trophies'},{name:'limit',type:4,value:1}]));
   if(!text(stats).includes('Beta Clan')||text(stats).includes('Alpha Clan'))throw Error('Clan ranking/limit wrong');
   await db.query("INSERT INTO player_stat_changes(player_tag,clan_tag,event_time,stat_type,previous_value,current_value,delta) VALUES($1,$2,$3,'donated',0,321,321)",[tag,group,statTime]);
   const donations=await interact(command('family','stats',[{name:'type',type:3,value:'donations'}]));
   if(!text(donations).includes('321'))throw Error('Recorded clan contribution missing');
   const listingRefresh=listing.components[0].components[0].custom_id;
   if(!text(await interact({type:3,data:{custom_id:listingRefresh,component_type:2}},other)).includes('Zulu group'))throw Error('Directory refresh lost grouping');
   const wars=await interact(command('family','wars'));
   if(!text(wars).includes('2/4 attacks')||!text(wars).includes('Alpha Clan')||!text(wars).includes('Beta Clan'))throw Error('Family war orientation failed '+text(wars));
   reminderCwl=true;
   const beforeWars=live.filter(path=>path==='/v1/clanwarleagues/wars/%23PYLQGRJQ').length;
   const cwlReport=await interact(command('family','wars'));
   if(!text(cwlReport).includes('CWL')||live.filter(path=>path==='/v1/clanwarleagues/wars/%23PYLQGRJQ').length-beforeWars!==1)throw Error('Family CWL lookup was not shared');
   reminderCwl=false;
   privateWar=true;
   const partial=await interact(command('family','wars'));
   if(!text(partial).includes('Private war log'))throw Error('Private clan silently dropped');privateWar=false;
   warEnded=true;const hidden=await interact(command('family','wars'));
   if(text(hidden).includes('2/4 attacks'))throw Error('Ended war included by default');
   const ended=await interact(command('family','wars',[{name:'include_ended',type:5,value:true}]));
   if(!text(ended).includes('2/4 attacks'))throw Error('Ended war option ignored');warEnded=false;
   const raids=await interact(command('family','raids'));
   if(!text(raids).includes('12.3K')||JSON.stringify(raids.embeds).includes('999'))throw Error('Wrong raid weekend chosen '+text(raids));
   raidSkip=true;const skipped=await interact(command('family','raids'));
   if(!text(skipped).includes('No matching raid'))throw Error('Old raid substituted for missing weekend');raidSkip=false;
   raidFailure=true;const failed=await interact(command('family','raids'));
   if(!text(failed).includes('Unavailable')||!text(failed).includes('12.3K'))throw Error('Partial raid failure lost valid clan');raidFailure=false;
   const dated=await interact(command('family','raids',[{name:'weekend',type:3,value:raidDate}]));
   const refresh=dated.components[0].components[0].custom_id;
   if(!refresh.includes(raidDate))throw Error('Explicit weekend lost');
   const refreshed=await interact({type:3,data:{custom_id:refresh,component_type:2}},other);
   if(!text(refreshed).includes('12.3K'))throw Error('Public family refresh failed');
   const invalid=await interact(command('family','raids',[{name:'weekend',type:3,value:'2026-10-26'}]));
   if(!text(invalid).includes('Choose a Friday'))throw Error('Invalid weekday accepted');
   console.log(JSON.stringify({familyOperations:'passed',checks:['configured categories and refresh','clan ranking and limit','recorded clan donations','own-side war orientation','shared CWL war lookup','private status','ended option','exact raid weekend','missing weekend','partial upstream failure','refresh weekend and public click','invalid date'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM player_stat_changes WHERE player_tag=$1 AND event_time=$2',[tag,statTime]);await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']]);}
 }else if(streakMode){
  const streakTags=[tag,tags[1],tags[2]];
  if((await db.query('SELECT 1 FROM legend_attack_streaks WHERE player_tag=ANY($1::text[])',[streakTags])).rowCount)throw Error('Synthetic streak rows already exist');
  try{
   await db.query("INSERT INTO legend_attack_streaks(player_tag,current_streak,observed_since,last_attack_at,last_non_triple_at) VALUES($1,100000003,now()-interval '3 days',now(),now()-interval '2 days'),($2,100000002,now()-interval '3 days',now(),NULL),($3,0,now(),now(),now())",streakTags);
   const response=await interact(command('legends','stats',[{name:'type',type:3,value:'streaks'},{name:'limit',type:4,value:2}]));
   if(!text(response).includes('100,000,003')||!text(response).includes('start not observed')||text(response).includes(tags[2]))throw Error('Streak order/limit/provenance failed '+text(response));
   const refresh=response.components.flatMap(row=>row.components??[]).find(item=>item.custom_id)?.custom_id;
   if(!refresh)throw Error('Streak refresh missing');
   const updated=await interact({type:3,data:{custom_id:refresh,component_type:2}},other);
   if(!text(updated).includes('100,000,003'))throw Error('Streak refresh failed');
   const denied=await fetch(`http://127.0.0.1:${port}/v2/bot/legends/stats?type=streaks`);
   if(denied.status!==401)throw Error('Streak API exposed without bot auth');
   console.log(JSON.stringify({streaks:'passed',checks:['actual API/SQL response','leader order and limit','unknown start label','zero streak excluded','public refresh','bot authentication'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM legend_attack_streaks WHERE player_tag=ANY($1::text[])',[streakTags]);}
 }else if(posterMode){
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
   const settings=async(body,credential=keys.API_BOT_TOKEN)=>{
    const response=await fetch(`http://127.0.0.1:${port}/v2/server/${roleServer}/role-settings`,{method:'PATCH',headers:{authorization:`Bearer ${credential}`,'content-type':'application/json'},body:JSON.stringify(body)});
    const value=await response.json();if(response.status!==200)throw Error('Settings update failed: '+response.status+' '+JSON.stringify(value));return value;
   };
   // Exercise the actual settings endpoint, not a direct queue fixture. Enabling
   // automatic evaluation must reconcile existing members without a game event.
   await db.query('INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,$3)',[roleServer,app,JSON.stringify({user:{id:app,bot:true},roles:[]})]);
   await settings({auto_eval_status:true,auto_eval_nickname:false});
   const jobId=`auto:${roleServer}:${actor}`;
   let queued=(await db.query('SELECT revision,grace_until FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0];
   if(!queued||(await db.query('SELECT 1 FROM role_refresh_jobs WHERE server_id=$1 AND user_id=$2',[roleServer,app])).rowCount)throw Error('Settings did not queue humans only');
   await settings({auto_eval_status:true,auto_eval_nickname:false});
   if((await db.query('SELECT revision FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0]?.revision!==queued.revision)throw Error('Unchanged settings requeued members');
   await db.query("UPDATE role_refresh_jobs SET grace_until=now()+interval '10 minutes',due_at=now()+interval '10 minutes' WHERE id=$1",[jobId]);
   await settings({nickname_rule:'Test {player_name}',non_family_nickname_rule:'Test {player_name}'});
   queued=(await db.query('SELECT revision,grace_until,due_at FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0];
   if(Number(queued.revision)!==2||!queued.grace_until||new Date(queued.due_at).getTime()!==new Date(queued.grace_until).getTime())throw Error('Settings bypassed pending leave grace');
   await settings({auto_eval_status:false});
   if((await db.query('SELECT revision FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0]?.revision!==queued.revision)throw Error('Disabled automation queued work');
   await settings({auto_eval_status:true});
   await db.query('UPDATE role_refresh_jobs SET grace_until=NULL,due_at=now() WHERE id=$1',[jobId]);
   const scheduled=await (await bot.getWorker()).scheduled({cron:'* * * * *'});
   console.log('Scheduled response',scheduled);
   await wait(async()=>Boolean((await db.query('SELECT completed_at FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0]?.completed_at),'automatic refresh completion').catch(async error=>{console.log('Synthetic job status',(await db.query('SELECT attempts,completed_at,result,due_at FROM role_refresh_jobs WHERE id=$1',[jobId])).rows);throw error;});
   if(!memberRoles.has(newRole)||memberRoles.has(oldRole)||scheduled.outcome!=='ok')throw Error('Scheduled role refresh failed');
   const previousNickname=nickname;
   await settings({auto_eval_nickname:true});
   const renewed=(await db.query('SELECT completed_at,grace_until FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0];
   if(renewed.completed_at||renewed.grace_until)throw Error('Completed refresh was not reopened');
   await (await bot.getWorker()).scheduled({cron:'* * * * *'});
   await wait(async()=>Boolean((await db.query('SELECT completed_at FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0]?.completed_at),'automatic nickname completion');
   if(nickname===previousNickname||!nickname.startsWith('Test '))throw Error('Changed nickname settings were not applied by scheduled consumer');
   const revision=(await db.query('SELECT revision FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0].revision;
   const cosmetic=await fetch(`http://127.0.0.1:${port}/v2/server/${roleServer}/settings`,{method:'PATCH',headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},body:JSON.stringify({embed_color:123456})});
   if(!cosmetic.ok)throw Error('Cosmetic settings failed: '+await cosmetic.text());
   if((await db.query('SELECT revision FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0]?.revision!==revision)throw Error('Cosmetic settings unnecessarily queued roles');
   const ruleRequest=async(method,path,body)=>{
    const response=await fetch(`http://127.0.0.1:${port}/v2/server/${roleServer}/server-roles${path}`,{method,headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
    const value=await response.json();if(!response.ok)throw Error('Rule mutation failed: '+response.status+' '+JSON.stringify(value));return value;
   };
   const flushRuleChange=async()=>{await (await bot.getWorker()).scheduled({cron:'* * * * *'});await wait(async()=>Boolean((await db.query('SELECT completed_at FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0]?.completed_at),'rule change refresh');};
   const created=await ruleRequest('POST','',{type:'family',option:'not_family',role_id:oldRole});
   await flushRuleChange();if(!memberRoles.has(oldRole))throw Error('New role rule was not applied');
   const ruleRevision=(await db.query('SELECT revision FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0].revision;
   await ruleRequest('PATCH','/'+created.role.id,{option:'not_family'});
   if((await db.query('SELECT revision FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0].revision!==ruleRevision)throw Error('Unchanged role rule requeued members');
   await ruleRequest('PATCH','/'+created.role.id,{option:'family'});
   await flushRuleChange();if(memberRoles.has(oldRole)||!memberRoles.has(newRole)||!memberRoles.has(unmanagedRole))throw Error('Updated rule did not reconcile or affected unrelated roles');
   await ruleRequest('DELETE','/'+created.role.id);
   await flushRuleChange();if(!memberRoles.has(newRole)||!memberRoles.has(unmanagedRole))throw Error('Deleted rule affected unrelated roles');
   console.log(JSON.stringify({roleRefresh:'passed',checks:['actual signed command/API/SQL flow','null nickname defaults','preview performs no Discord edits','role add/remove preserves unmanaged role','repeat no-op','role hierarchy protection','settings enable enqueues human members','unchanged settings no-op','leave grace retained','disabled settings do not enqueue','scheduled automatic job completion','completed job reopened','new nickname applied automatically','cosmetic settings do not enqueue','created and updated rule application','unchanged rule no-op','deleted rule reconciliation'],externalDiscordWrites:0,localProviderWrites:roleWrites.length}));
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
