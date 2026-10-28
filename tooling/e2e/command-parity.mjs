// Actual workerd -> local API -> local SQL/HTTP provider integration. No Discord network calls.
import { createServer } from 'node:http';
import { bundleWorker } from './bundle-worker.mjs';
import { createHash, generateKeyPairSync, randomBytes, sign } from 'node:crypto';
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
const giveawayDeliveryMode=process.argv.includes("--giveaway-delivery");
const giveawayMessages=[];
const giveawayMode=process.argv.includes("--giveaway-only")||giveawayDeliveryMode;
const graphMode=process.argv.includes("--graph-month-only");let graphFailure=false,graphGap=false,dailyGraphFailure=false;
const warPanelMode=process.argv.includes("--war-panel-only");
const roleUsersMode=process.argv.includes("--role-users-only");
const boostsMode=process.argv.includes("--boosts-only");let boostFailure=false;
const warStatsMode=process.argv.includes("--war-statistics-only");
const botInfoMode=process.argv.includes("--bot-info-only");let botInfoFailure=false;
const handoffMode=process.argv.includes("--roster-handoff-only");
const verificationMode=process.argv.includes("--clan-verification-only")||handoffMode;let verificationDescription="";
const warEventMode=process.argv.includes("--war-events-only");
const memberWarningMode=process.argv.includes("--member-warning-only");
const quickPanelMode=process.argv.includes("--quick-panel-only");
const rosterReadMode=process.argv.includes("--roster-commands-only")||quickPanelMode||memberWarningMode||warEventMode;let rosterProfileFailure=false;
const helpMode=process.argv.includes("--help-only");
const warPreferenceMode=process.argv.includes("--war-preference-only");let warPreferenceFailure=false;
const activityMode=process.argv.includes("--activity-only");
const summaryMode=process.argv.includes("--summary-only");
let summaryRaidStart=new Date();
const progressMode=process.argv.includes("--progress-only");
const clanReportMode=process.argv.includes("--clan-reports-only");
const familyOpsMode=process.argv.includes("--family-ops-only");
let raidSkip=false,raidFailure=false;
const raidFriday=new Date();raidFriday.setUTCDate(raidFriday.getUTCDate()-(raidFriday.getUTCDay()+2)%7);raidFriday.setUTCHours(7,0,0,0);if(raidFriday>new Date())raidFriday.setUTCDate(raidFriday.getUTCDate()-7);
const raidDate=raidFriday.toISOString().slice(0,10);
const streakMode=process.argv.includes("--streaks-only");
const pepeMode=process.argv.includes("--pepe-only"),pepeAcks=[];
const posterMode=process.argv.includes("--poster-only");
const memberMode=process.argv.includes("--members-only");
const todoMode=process.argv.includes("--todo-only");let legendFails=false;
const sentReminders=[];
const roleMode=process.argv.includes('--roles-only'),roleServer='999999999999996510';
const botRole='999999999999996520',newRole='999999999999996521',oldRole='999999999999996522',unmanagedRole='999999999999996523';
const memberRoles=new Set([oldRole,unmanagedRole]),roleWrites=[];
let nickname='Original nickname',roleJoinedAt;
const roleDefinitions=[{id:roleServer,name:'@everyone',position:0,permissions:'0'},
 {id:botRole,name:'Bot',position:10,permissions:String((1<<28)+(1<<27))},
 {id:newRole,name:'TH16',position:2,permissions:'0'},
 {id:oldRole,name:'TH15',position:1,permissions:'0'},
 {id:unmanagedRole,name:'Unmanaged',position:3,permissions:'0'}];
const provider=createServer(async(req,res)=>{
 let text='';for await(const chunk of req)text+=chunk;
 const url=new URL(req.url,'http://provider');live.push(url.pathname+url.search);res.setHeader('Content-Type','application/json');
 if((roleMode||memberWarningMode)&&url.pathname===`/api/v10/guilds/${roleServer}/roles`)return res.end(JSON.stringify(roleDefinitions.map(role=>({...role,managed:role.id===botRole}))));
 if(roleMode&&url.pathname===`/api/v10/guilds/${roleServer}`)return res.end(JSON.stringify({id:roleServer,owner_id:other}));
 if(memberWarningMode&&url.pathname.startsWith('/api/v10/channels/'))return res.end(JSON.stringify({id:url.pathname.split('/').at(-1),guild_id:url.pathname.endsWith('/999999999999996599')?'999999999999996512':roleServer,type:0}));
 const p=decodeURIComponent(url.pathname),endTime=fixtureEnd;
 if(giveawayDeliveryMode&&url.pathname==='/webhooks/999999999999996588'&&req.method==='GET')return res.end(JSON.stringify({id:'999999999999996588',type:1,guild_id:'999999999999996510',channel_id:'999999999999996511',token:'local-only'}));
 if(giveawayDeliveryMode&&url.pathname==='/webhooks/999999999999996588/local-only'&&req.method==='POST'){
  giveawayMessages.push(JSON.parse(text));return res.end(JSON.stringify({id:'999999999999996589',channel_id:'999999999999996511',timestamp:new Date().toISOString(),content:'',embeds:[]}));
 }

 if(boostsMode&&p.startsWith('/v1/clans/'))return res.end(JSON.stringify({tag:p.split('/').at(-1),name:'Boost Clan',memberList:[{tag,name:'First',townHallLevel:16},{tag:tags[1],name:'Second',townHallLevel:16},{tag:tags[2],name:'Moved',townHallLevel:16}]}));
 if(boostsMode&&p.startsWith('/v1/players/')){
  const who=p.split('/').at(-1);
  if(boostFailure&&who===tags[1]){res.statusCode=503;return res.end('{}');}
  return res.end(JSON.stringify({tag:who,name:who===tag?'Alpha':'Zulu',townHallLevel:16,trophies:1000,clan:{tag:who===tags[2]?'#QQQQ':group,name:'Boost Clan'},troops:[{name:'Super Barbarian',level:10,superTroopIsActive:true},{name:'Sneaky Goblin',level:8,superTroopIsActive:who===tag},{name:'Super Archer',level:10,superTroopIsActive:false}]}));
 }
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
 if(roleMode&&p===`/v1/clans/${group}`)return res.end(JSON.stringify({tag:group,name:'Role Clan',description:'',clanLevel:10,members:1,isWarLogPublic:true,warWins:1,warWinStreak:0,clanPoints:1000,badgeUrls:{},memberList:[{tag,name:'Current Player',townHallLevel:16,donations:0,donationsReceived:0}]}));
 if(p===`/v1/clans/${group}`)return res.end(JSON.stringify({tag:group,name:'Reminder Clan',description:verificationDescription,warLeague:{id:48000019,name:'Champion League I'},memberList:[{tag,name:'Missing Player',townHallLevel:16},{tag:tags[1],name:'Finished Player',townHallLevel:16}]}));
 if(p===`/v1/clans/${group}/capitalraidseasons`)return res.end(JSON.stringify({items:reminderRaidActive?[{state:'ongoing',endTime,members:[{tag:tags[1],attacks:6,attackLimit:5,bonusAttackLimit:1}]}]:[]}));
 if(url.pathname.startsWith('/v1/players/')){if((warPreferenceFailure||rosterProfileFailure)&&decodeURIComponent(url.pathname).endsWith(tags[1])){res.statusCode=503;return res.end('{}');}const playerTag=decodeURIComponent(url.pathname.split('/').at(-1));return res.end(JSON.stringify({tag:playerTag,name:playerTag===tag?'Current Player':`Account ${tags.indexOf(playerTag)+1}`,townHallLevel:memberMode&&playerTag===tags[1]?18:16,trophies:5500,warStars:100,expLevel:250,donations:50,donationsReceived:40,currentLeagueGroupTag:group,currentLeagueSeasonId:currentSeason,...(warPreferenceMode?{warPreference:playerTag===tag?'in':'out'}:{}),...(rosterReadMode?{troops:[],spells:[],heroes:[]}:{}),leagueTier:{id:todoMode&&playerTag===tags[0]?105000036:tier,name:'Current League'},...((todoMode||roleMode)?{clan:{tag:group,name:'Reminder Clan'}}:{}),
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
   if(roleMode||quickPanelMode){
    if(url.pathname==='/api/v10/users/@me')return Response.json({id:app});
    if(url.pathname===`/api/v10/guilds/${roleServer}`)return Response.json({id:roleServer,owner_id:other});
    if(url.pathname===`/api/v10/guilds/${roleServer}/roles`)return Response.json(roleDefinitions);
    if(url.pathname===`/api/v10/guilds/${roleServer}/members/${app}`)return Response.json({user:{id:app,bot:true},roles:[botRole]});
    if(url.pathname===`/api/v10/guilds/${roleServer}/members/${actor}`){
     if(request.method==='GET')return Response.json({user:{id:actor,username:'Local'},nick:nickname,roles:[...memberRoles],joined_at:roleJoinedAt});
     if(request.method==='PATCH'){nickname=(await request.json()).nick;roleWrites.push({kind:'nickname',value:nickname});return Response.json({});}
    }
    const change=new RegExp(`/guilds/${roleServer}/members/${actor}/roles/([0-9]+)$`).exec(url.pathname);
    if(change){if(request.method==='PUT')memberRoles.add(change[1]);else if(request.method==='DELETE')memberRoles.delete(change[1]);else throw Error('Unexpected role method');roleWrites.push({kind:request.method,role:change[1]});return new Response(null,{status:204});}
   }
   if(request.method==='GET'&&url.pathname.endsWith('/emojis')){emojiInventoryRequests++;return Response.json({items:emojiItems});}
   if(request.method==='GET'&&url.pathname.includes('/channels/'))return Response.json({id:url.pathname.split('/').at(-1),guild_id:quickPanelMode&&url.pathname.endsWith('/999999999999996599')?'999999999999996512':'999999999999996510',type:0});
   if(request.method==='POST'&&url.pathname.endsWith('/messages')){if(reminderSendFails)return Response.json({message:'Missing permissions'},{status:403});sentReminders.push(await request.json());return Response.json({id:'999999999999996999'});}
   const token=url.pathname.split('/')[5];let data;
   if(request.headers.get('content-type')?.startsWith('multipart/form-data')){
    const form=await request.formData();data=JSON.parse(form.get('payload_json'));
    const file=form.get('files[0]');if(!file)throw Error('Missing poster attachment');
    const bytes=Buffer.from(await file.arrayBuffer());
    const dimension=pepeMode?250:1600,height=pepeMode?250:1100;
    if(bytes.subarray(0,8).toString('hex')!=='89504e470d0a1a0a'||bytes.readUInt32BE(16)!==dimension||bytes.readUInt32BE(20)!==height)throw Error('Invalid rendered PNG');
    if(pepeMode){data.imageHash=createHash('sha256').update(bytes).digest('hex');data.imageName=file.name;}
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
  if(botInfoMode&&botInfoFailure&&url.pathname==="/v2/bot/status")return Response.json({message:"Unavailable"},{status:503});
  if(graphMode&&dailyGraphFailure&&url.pathname==='/v2/bot/clans/daily-stats')return Response.json({message:'Unavailable'},{status:503});
  if(graphMode&&graphGap&&decodeURIComponent(url.pathname).includes(group+'/season-stats')&&url.searchParams.get('season')==='2024-12')return Response.json({message:'Unavailable'},{status:503});
  if(graphMode&&graphFailure&&decodeURIComponent(url.pathname).includes('#PYLQGRJJ/season-stats'))return Response.json({message:'Unavailable'},{status:503});
  if(todoMode&&legendFails&&url.pathname==='/v2/legends/days')return Response.json({message:'Temporarily unavailable'},{status:503});
  if(url.hostname==='127.0.0.1'&&url.port===String(port))return fetch(request.url,{method:request.method,headers:Object.fromEntries(request.headers),body:['GET','HEAD'].includes(request.method)?undefined:await request.arrayBuffer()});
  throw Error('External request blocked by local integration harness');
 }}]}));
 const origin=new URL('/interactions',String(await bot.ready)).href;
 async function interact(data,who=actor,permissions='0'){const token=String(counter++);const rawBody=JSON.stringify({id:token,application_id:app,guild_id:'999999999999996510',channel_id:'999999999999996511',member:{user:{id:who,username:'Local'},roles:[],permissions},version:1,token,...data});const timestamp=String(Math.floor(Date.now()/1000));const response=await fetch(origin,{method:'POST',headers:{'Content-Type':'application/json','X-Signature-Timestamp':timestamp,'X-Signature-Ed25519':sign(null,Buffer.from(timestamp+rawBody),privateKey).toString('hex')},body:rawBody});const initial=await response.json();if(pepeMode)pepeAcks.push(initial);if(response.status!==200)throw Error(`Bot HTTP ${response.status}`);const result=[5,6].includes(initial.type)?await wait(()=>replies.get(token),'deferred reply'):initial.data;return result;}
 const command=(name,action,options=[])=>({type:2,data:{name,options:[{name:action,type:1,options}]}});
 const player={name:'player',type:3,value:tag};
 const text=value=>JSON.stringify(value);
 if(pepeMode){
  const run=(value,hidden)=>interact({type:2,data:{name:'pepe',options:[{name:'sign_text',type:3,value},...(hidden?[{name:'hidden',type:3,value:hidden}]:[])]}});
  const privateImage=await run('Hello clan');
  if(pepeAcks.at(-1).data.flags!==64||privateImage.flags!==64||privateImage.imageName!=='pepe.png'||privateImage.posterBytes<10000)throw Error('Private image visibility or PNG missing');
  const publicImage=await run('Hello clan','No');
  if(pepeAcks.at(-1).data.flags||publicImage.flags||publicImage.imageHash!==privateImage.imageHash)throw Error('Public acknowledgement or render changed');
  const long=await run('W'.repeat(40),'Yes');if(long.imageHash===privateImage.imageHash)throw Error('Text not rendered');
  const escaped=await run('<image href="https://example.com"/>','Yes');if(!escaped.posterBytes)throw Error('Escaped sign not rendered');
  for(const value of [' ', '\u0000', 'W'.repeat(41)]){const invalid=await run(value);if(invalid.posterBytes||!text(invalid).includes('1–40'))throw Error('Invalid sign accepted');}
  console.log(JSON.stringify({pepe:'passed',checks:['actual bundled PNG and font rendering','250px PNG attachment','private acknowledgement by default','public acknowledgement when requested','40-character unbroken text','XML escaped input','empty and over-limit rejection'],externalDiscordWrites:0}));
 }else if(botInfoMode){
  const servers=['999999999999996510','999999999999996512','999999999999996513'],clans=[group,'#PYLQGRJJ'];
  if((await db.query('SELECT 1 FROM servers WHERE id=ANY($1::text[])',[servers])).rowCount||(await db.query('SELECT 1 FROM discord_cache.gateway_shards WHERE application_id=$1',[app])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[clans])).rowCount)throw Error('Bot status fixture exists');
  const get=()=>fetch(`http://127.0.0.1:${port}/v2/bot/status`,{headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`}}).then(response=>response.json());
  const before=await get();const generation=randomBytes(16).toString('hex'),wrong=randomBytes(16).toString('hex');
  try{
   await db.query("INSERT INTO servers(id,name,left_at) VALUES($1,'Status A',NULL),($2,'Status B',NULL),($3,'Left server',now())",servers);
   for(const clan of clans)await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Status clan',true,0,0,'',0,0)",[clan]);
   await db.query('INSERT INTO server_clans(server_id,tag) VALUES($1,$4),($2,$4),($3,$5)',[...servers,...clans]);
   await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,2,$2,true,now()),($1,1,2,$2,true,now())',[app,generation]);
   await db.query("INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,'{}',$3,0,$4,true,true,true),($2,'{}',$3,1,$5,true,true,true)",[servers[0],servers[1],app,generation,wrong]);
   const current=await get();if(current.configuredServers!==before.configuredServers+2||current.familyClans!==before.familyClans+1||current.healthyShards!==2||current.readyGuilds!==1||current.cachedGuilds!==2||current.expectedShards!==2)throw Error('Status aggregation or generation fencing incorrect '+JSON.stringify(current));
   if(!Number.isFinite(Date.parse(current.countsRefreshedAt)))throw Error('Stored counts missing snapshot age');
   await db.query('UPDATE discord_cache.guilds SET generation=$2 WHERE id=$1',[servers[1],generation]);if((await get()).readyGuilds!==2)throw Error('Matching guild not ready');
   await db.query("UPDATE discord_cache.gateway_shards SET heartbeat_at=now()-interval '1 hour' WHERE application_id=$1 AND shard_id=1",[app]);
   const stale=await get();if(stale.healthyShards!==1||stale.readyGuilds!==1)throw Error('Stale gateway reported ready');
   const first=await interact({type:2,data:{name:'bot'}});if(!text(first).includes('ClashKing statistics')||!text(first).includes('1/2 healthy')||text(first).includes('http://'))throw Error('Bot statistics response incorrect '+text(first));
   const refresh=await interact({type:3,data:{custom_id:first.components[0].components[0].custom_id,component_type:2}},other);if(!text(refresh).includes('ClashKing statistics'))throw Error('Bot info refresh failed');
   if((await fetch(`http://127.0.0.1:${port}/v2/bot/status`)).status!==401)throw Error('Bot status missing authentication');
   botInfoFailure=true;const failed=await interact({type:2,data:{name:'bot'}});if(!text(failed).includes('temporarily unavailable')||failed.embeds?.length)throw Error('Failed stats shown as zero');
   console.log(JSON.stringify({botInfo:'passed',checks:['configured servers exclude left servers','family clans deduplicated','gateway generation fencing','heartbeat freshness','data timestamp','public refresh','API authentication','unavailable state'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM discord_cache.guilds WHERE id=ANY($1::text[])',[servers]);await db.query('DELETE FROM discord_cache.gateway_shards WHERE application_id=$1',[app]);await db.query('DELETE FROM servers WHERE id=ANY($1::text[])',[servers]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[clans]);}
 }else if(giveawayMode){
  const server='999999999999996510',foreign='999999999999996512',id='local-reroll-fixture',outsider='local-reroll-foreign';
  const eligible='999999999999996504',zero='999999999999996505';
  if((await db.query('SELECT 1 FROM servers WHERE id=ANY($1::text[])',[[server,foreign]])).rowCount)throw Error('Giveaway test scope exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Giveaway fixture'),($2,'Foreign giveaway')",[server,foreign]);
  try{
   await db.query(`INSERT INTO giveaways(id,server_id,prize,status,start_time,end_time,winners,entries,winners_list,channel_id,message_id)
    VALUES($1,$2,'Local prize','ended',now()-interval '2 hours',now()-interval '1 hour',1,$3::jsonb,$4::jsonb,'999999999999996511','999999999999996599')`,[id,server,JSON.stringify([actor,eligible,zero]),JSON.stringify([{user_id:actor,status:'winner'}])]);
   await db.query(`INSERT INTO giveaway_outcome_runs(giveaway_id,server_id,channel_id,start_time,end_time,source_updated_at,winner_count,boosters,entry_count,cursor,state)
    SELECT id,server_id,channel_id,start_time,end_time,updated_at,winners,'[]'::jsonb,3,3,'completed' FROM giveaways WHERE id=$1`,[id]);
   await db.query(`INSERT INTO giveaway_outcome_entries(run_id,user_id,ordinal,weight,score)
    SELECT id,x.user_id,x.ordinal,x.weight,0 FROM giveaway_outcome_runs CROSS JOIN (VALUES($2::text,1,5),($3::text,2,2),($4::text,3,0)) x(user_id,ordinal,weight) WHERE giveaway_id=$1`,[id,actor,eligible,zero]);
   await db.query(`INSERT INTO giveaway_publication_effects(effect_id,giveaway_id,server_id,channel_id,kind,start_time,source_updated_at,payload_version,payload,state)
    SELECT encode(sha256(id::bytea),'hex'),id,server_id,channel_id,'end',start_time,updated_at,1,'{}'::jsonb,'succeeded' FROM giveaways WHERE id=$1`,[id]);
   await db.query(`INSERT INTO giveaways(id,server_id,prize,status,start_time,end_time,winners,entries,winners_list)
    VALUES($1,$2,'Foreign prize','ended',now()-interval '2 hours',now()-interval '1 hour',1,$3::jsonb,$4::jsonb)`,[outsider,foreign,JSON.stringify([actor,eligible]),JSON.stringify([{user_id:actor,status:'winner'}])]);
   const opts=[{name:'giveaway',type:3,value:id},{name:'winners',type:3,value:`<@${actor}>`},{name:'reason',type:3,value:'Winner could not claim prize'}];
   const denied=await interact(command('giveaway','reroll',opts),actor,'0');if(!text(denied).includes('Manage Server'))throw Error('Giveaway permission bypass');
   const invalid=await interact(command('giveaway','reroll',[opts[0],{name:'winners',type:3,value:`<@${actor}> <@${actor}>`}]),actor,'32');if(!text(invalid).includes('distinct'))throw Error('Duplicate replacement accepted');
   const cross=await interact(command('giveaway','reroll',[{...opts[0],value:outsider},opts[1]]),actor,'32');if(!text(cross).includes('not found'))throw Error('Cross-server reroll accepted '+text(cross));
   const replaced=await interact(command('giveaway','reroll',opts),actor,'32');if(!text(replaced).includes(eligible)||text(replaced).includes(`<@${zero}>`))throw Error('Weighted reroll failed '+text(replaced));
   const winners=(await db.query('SELECT winners_list FROM giveaways WHERE id=$1',[id])).rows[0].winners_list;
   if(winners.find(x=>x.user_id===actor)?.reason!=='Winner could not claim prize'||winners.find(x=>x.user_id===eligible)?.status!=='winner')throw Error('Reroll history not persisted');
   const effects=(await db.query("SELECT payload FROM giveaway_publication_effects WHERE giveaway_id=$1 AND kind='reroll'",[id])).rows;
   if(effects.length!==1||effects[0].payload.reason!=='Winner could not claim prize'||effects[0].payload.actor_label!=='Discord')throw Error('Reroll publication missing reason/source');
   if(giveawayDeliveryMode){
    if(!/^127\.0\.0\.1:\d+$/u.test(process.env.CLASHKING_E2E_VALKEY_ADDR??''))throw Error('Dedicated loopback Valkey required for delivery test');
    await db.query('UPDATE giveaways SET webhook_id=$2 WHERE id=$1',[id,'999999999999996588']);
    const trackingRepo=process.env.CLASHKING_E2E_TRACKING_REPO??join(botRepo,'../clashking_tracking');
    const child=spawn('go',['run','./cmd/verify-giveaway-delivery'],{cwd:trackingRepo,env:{PATH:process.env.PATH,HOME:process.env.HOME,TMPDIR:process.env.TMPDIR,CLASHKING_GIVEAWAY_E2E:'1',TEST_DATABASE_URL:database,TEST_API_URL:`http://127.0.0.1:${port}`,TEST_DISCORD_URL:`http://127.0.0.1:${providerPort}`,TEST_API_TOKEN:keys.API_BOT_TOKEN,TEST_GUILD_ID:server,TEST_GIVEAWAY_ID:id,TEST_VALKEY_ADDR:process.env.CLASHKING_E2E_VALKEY_ADDR},stdio:['ignore','pipe','pipe']});
    let output='';child.stdout.on('data',chunk=>output+=chunk);child.stderr.on('data',chunk=>output+=chunk);
    const code=await new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',resolve);});
    if(code!==0)throw Error('Tracking delivery failed: '+output.slice(-4000));
    if(giveawayMessages.length!==1||!JSON.stringify(giveawayMessages[0]).includes('Winner could not claim prize'))throw Error('Delivered message missing reason or duplicated');
    const mentions=giveawayMessages[0].allowed_mentions;
    if(mentions.parse?.length||JSON.stringify(mentions.users)!==JSON.stringify([eligible]))throw Error('Unexpected announcement mentions');
   }
   const repeat=await interact(command('giveaway','reroll',opts),actor,'32');if(!text(repeat).includes('not a current winner'))throw Error('Repeat rerolled old winner');
   const counts=(await db.query("SELECT count(*)::int n FROM giveaway_publication_effects WHERE giveaway_id=$1 AND kind='reroll'",[id])).rows[0].n;if(counts!==1)throw Error('Repeat queued duplicate announcement');
   const imported='local-reroll-imported';
   await db.query(`INSERT INTO giveaways(id,server_id,prize,status,start_time,end_time,winners,entries,winners_list,boosters)
    VALUES($1,$2,'Imported prize','ended',now()-interval '2 hours',now()-interval '1 hour',1,$3::jsonb,$4::jsonb,$5::jsonb)`,[imported,server,JSON.stringify([actor,eligible]),JSON.stringify([{user_id:actor}]),JSON.stringify([{roles:['999999999999996599'],value:2}])]);
   const importedOptions=[{...opts[0],value:imported},opts[1]];
   const noWeights=await interact(command('giveaway','reroll',importedOptions),actor,'32');if(!text(noWeights).includes('no recorded booster weights'))throw Error('Imported boosted odds silently discarded '+text(noWeights));
   await db.query("UPDATE giveaways SET boosters='[]'::jsonb WHERE id=$1",[imported]);
   const fallback=await interact(command('giveaway','reroll',importedOptions),actor,'32');if(!text(fallback).includes(eligible))throw Error('Legacy winner without status not supported '+text(fallback));
   await db.query("UPDATE giveaways SET status='ongoing' WHERE id=$1",[imported]);
   const ongoing=await interact(command('giveaway','reroll',[{...opts[0],value:imported},{...opts[1],value:eligible}]),actor,'32');if(!text(ongoing).includes('ended giveaway'))throw Error('Ongoing reroll accepted');
   console.log(JSON.stringify({giveawayReroll:'passed',trackingDelivery:giveawayDeliveryMode?'passed':'not run',checks:['manager permission','duplicate and foreign rejection','recorded positive weights','zero weight excluded','reason and history persisted','announcement queued','stale retry rejected','missing imported booster odds rejected','legacy unweighted import','ongoing rejected'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM giveaway_publication_effects WHERE server_id=ANY($1::text[]) AND giveaway_id=ANY($2::text[])',[[server,foreign],[id,outsider,'local-reroll-imported']]);await db.query('DELETE FROM giveaways WHERE server_id=ANY($1::text[])',[[server,foreign]]);await db.query('DELETE FROM servers WHERE id=ANY($1::text[])',[[server,foreign]]);}
 }else if(graphMode){
  const server='999999999999996510',season='2025-01';
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']])).rowCount)throw Error('Synthetic graph scope exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Graph fixture')",[server]);
  let event,priorEvent,dailyOwned=false;const graphWarIds=[],graphRaidStarts=[],graphCapitalDates=[];const dailyPlayer=tags[10],dailyTime=new Date();dailyTime.setUTCDate(dailyTime.getUTCDate()-1);dailyTime.setUTCHours(12,0,0,0);
  try{
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Alpha Clan',true,0,0,'',0,0),('#PYLQGRJJ','Beta Clan',true,0,0,'',0,0)",[group]);
   await db.query("INSERT INTO server_clans(tag,server_id) VALUES($1,$2),('#PYLQGRJJ',$2)",[group,server]);
   const window=await(await fetch(`http://127.0.0.1:${port}/v2/bot/clans/${encodeURIComponent(group)}/season-stats?season=${season}`,{headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`}})).json();event=new Date(Date.parse(window.start)+86400000);
   await db.query("INSERT INTO player_stat_changes(player_tag,clan_tag,event_time,stat_type,previous_value,current_value,delta) VALUES($1,$2,$3,'donated',0,260,260),($4,'#PYLQGRJJ',$3,'donated',0,100,100)",[tag,group,event,tags[1]]);
   const prior=await(await fetch(`http://127.0.0.1:${port}/v2/bot/clans/${encodeURIComponent(group)}/season-stats?season=2024-12`,{headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`}})).json();priorEvent=new Date(Date.parse(prior.start)+86400000);
   await db.query("INSERT INTO player_stat_changes(player_tag,clan_tag,event_time,stat_type,previous_value,current_value,delta) VALUES($1,$2,$3,'donated',0,130,130)",[tag,group,priorEvent]);
   const first=await interact(command('graph','month',[{name:'attribute',type:3,value:'donated'},{name:'season',type:3,value:season}]));
   if(!first.posterBytes||!text(first).includes('Alpha Clan: 260')||!text(first).includes('Beta Clan: 100'))throw Error('Graph totals or PNG missing '+text(first));
   const custom=await interact(command('graph','month',[{name:'attribute',type:3,value:'donated'},{name:'season',type:3,value:season},{name:'clans',type:3,value:group},{name:'limit',type:4,value:1}]));
   if(!text(custom).includes(group+': 260')||text(custom).includes('Beta Clan:'))throw Error('Custom clan selection ignored');
   const id=first.components[0].components[0].custom_id;
   const refreshed=await interact({type:3,data:{custom_id:id}},other);
   if(!refreshed.posterBytes||!text(refreshed).includes('260'))throw Error('Public chart refresh failed');
   const series=await interact(command('graph','over-time',[{name:'attribute',type:3,value:'donated'},{name:'season',type:3,value:season},{name:'months',type:4,value:2}]));
   if(!series.posterBytes||!text(series).includes('130 → 260')||!text(series).includes('0 → 100'))throw Error('Multi-season contributions failed '+text(series));
   graphGap=true;
   const seriesId=series.components[0].components[0].custom_id;
   const gap=await interact({type:3,data:{custom_id:seriesId}},other);
   if(!gap.posterBytes||!text(gap).includes('? → 260')||!text(gap).includes('1 observations unavailable'))throw Error('Missing season became zero '+text(gap));
   graphGap=false;
   graphFailure=true;const partial=await interact(command('graph','month',[{name:'attribute',type:3,value:'donated'},{name:'season',type:3,value:season}]));
   if(text(partial).includes('Beta Clan:')||!partial.posterBytes)throw Error('Failed clan included as zero');
   if((await db.query('SELECT 1 FROM basic_player WHERE tag=$1',[dailyPlayer])).rowCount)throw Error('Daily player fixture already exists');
   await db.query("INSERT INTO basic_player(tag,name,clan_tag,townhall_level) VALUES($1,'Daily fixture','#PYLQGRJJ',16)",[dailyPlayer]);dailyOwned=true;
   await db.query("INSERT INTO player_change_history(event_time,player_tag,change_type,item_id,previous_value,current_value) VALUES($1,$2,1,0,'10','13'),($1,$2,1,1,'13','12'),($1,$2,1,2,'12','12'),($1,$2,2,0,'0','1'),($1,$2,12,NULL,'Old name','New name')",[dailyTime,dailyPlayer]);
   await db.query("INSERT INTO player_stat_changes(player_tag,clan_tag,event_time,stat_type,previous_value,current_value,delta) VALUES($1,$2,$3,'donated',0,100,100)",[dailyPlayer,group,dailyTime]);
   let resetRejected=false;try{await db.query("INSERT INTO player_stat_changes(player_tag,clan_tag,event_time,stat_type,previous_value,current_value,delta) VALUES($1,$2,$3,'donated',100,50,-50)",[dailyPlayer,group,dailyTime]);}catch(error){if(error.code==='23514')resetRejected=true;else throw error;}if(!resetRejected)throw Error('Negative contribution reset accepted by schema');
   await db.query('INSERT INTO player_online_events(tag,clan_tag,seen_at) VALUES($1,$2,$3),($1,$2,$3)',[dailyPlayer,group,dailyTime]);
   await db.query("INSERT INTO battles_farming(player_tag,battle_time,stars,destruction_percentage,looted_resources) VALUES($1,$2,2,70,$3),($1,$4,0,20,$5)",[dailyPlayer,event,JSON.stringify({gold:100,elixir:200,darkElixir:10}),new Date(+event+3600000),JSON.stringify({gold:50,elixir:100,darkElixir:5})]);
   await db.query("INSERT INTO player_change_history(event_time,player_tag,change_type,item_id,previous_value,current_value) VALUES($1,$2,1,11,'2','5'),($1,$2,3,12,'5','7')",[event,dailyPlayer]);
   await db.query('INSERT INTO player_online_events(tag,clan_tag,seen_at) VALUES($1,$2,$3)',[dailyPlayer,group,event]);
   for(const [type,a,b] of [['random',10,9],['cwl',7,8],['friendly',30,0]]){const war=await db.query("INSERT INTO wars(clan_tag,opponent_tag,prep_time,start_time,end_time,size,war_type,state,clan_stars,opponent_stars) VALUES($1,'#PYLQGRJJ',$2,$2,$3,15,$4,'warEnded',$5,$6) RETURNING war_id",[group,event,new Date(+event+86400000),type,a,b]);graphWarIds.push(war.rows[0].war_id);}
   const total=async(metric,clan=group)=>{const response=await fetch(`http://127.0.0.1:${port}/v2/bot/clans/${encodeURIComponent(clan)}/graph-total?season=${season}&metric=${metric}`,{headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`}});return {status:response.status,data:await response.json()};};
   for(const [metric,want] of [['gold',150],['elixir',300],['darkElixir',15],['attackWins',1],['troopLevels',3],['heroLevels',2]]){const value=await total(metric,'#PYLQGRJJ');if(value.status!==200||value.data.value!==want||value.data.basis!=='latest_stored_members')throw Error('Extended member metric '+metric+' '+JSON.stringify(value));}
   for(const [metric,want] of [['activity',1],['warStars',17],['warsWon',1],['warsSpun',2]]){const value=await total(metric);if(value.status!==200||value.data.value!==want||value.data.basis!=='recorded_clan')throw Error('Extended event metric '+metric+' '+JSON.stringify(value));}
   if((await total('warStars','#PYLQGRJJ')).data.value!==17||(await total('warsWon','#PYLQGRJJ')).data.value!==1)throw Error('Opponent war perspective incorrect');
   if((await total('unsupported')).status!==400)throw Error('Unsupported graph metric accepted');
   const more=await interact(command('graph','month',[{name:'attribute',type:3,value:'gold'},{name:'season',type:3,value:season}]));if(!more.posterBytes||!text(more).includes('Beta Clan: 150')||!text(more).includes('Latest stored clan members'))throw Error('Extended monthly graph failed '+text(more));
   const moreSeries=await interact(command('graph','over-time',[{name:'attribute',type:3,value:'attackWins'},{name:'season',type:3,value:season},{name:'months',type:4,value:2}]));if(!moreSeries.posterBytes||!text(moreSeries).includes('Beta Clan: 0 → 1'))throw Error('Extended series failed '+text(moreSeries));
   console.log(JSON.stringify({extendedGraph:'passed',checks:['six latest-member metrics','four event/war metrics','opponent perspective','friendly wars excluded','unsupported metric rejected','monthly PNG and basis','series PNG']}));
   for(const [index,loot,participants,state] of [[0,1000,2,'ended'],[1,2000,3,'ended'],[2,9000,4,'ongoing']]){const start=new Date(+event+index*86400000);await db.query('INSERT INTO capital_raid_history(clan_tag,start_time,end_time,state,data) VALUES($1,$2,$3,$4,$5)',[group,start,new Date(+start+3*86400000),state,JSON.stringify({capitalTotalLoot:loot,members:Array.from({length:participants},(_,i)=>({tag:tags[i],attacks:1}))})]);graphRaidStarts.push(start);}
   if((await total('capitalRaided')).data.value!==3000||(await total('raidParticipants')).data.value!==2.5)throw Error('Raid graph totals or average incorrect');
   if((await total('capitalRaided','#PYLQGRJJ')).data.value!==null)throw Error('Missing raid history became zero');
   const raidsChart=await interact(command('graph','month',[{name:'attribute',type:3,value:'raidParticipants'},{name:'season',type:3,value:season}]));if(!raidsChart.posterBytes||!text(raidsChart).includes('Alpha Clan: 2.5')||text(raidsChart).includes('Beta Clan:'))throw Error('Fractional raid average chart failed '+text(raidsChart));
   console.log(JSON.stringify({raidGraphs:'passed',checks:['completed raid loot','fractional participation average','ongoing raids excluded','missing history stays null','real PNG']}));
   for(const [offset,points] of [[0,4000],[1,4200]]){const date=new Date(+event+offset*86400000).toISOString().slice(0,10);await db.query("INSERT INTO leaderboard_history_clan_capital(location_id,date,clan_tag,clan_name,clan_badge_token,clan_level,capital_points,members,rank) VALUES('global',$1,$2,'Alpha Clan','fixture',10,$3,40,999999)",[date,group,points]);graphCapitalDates.push(date);}
   if((await total('capitalTrophies')).data.value!==4200)throw Error('Capital trophies did not use final recorded snapshot');
   if((await total('capitalTrophies','#PYLQGRJJ')).data.value!==null)throw Error('Missing Capital snapshot became zero');
   const laterCapitalDate=new Date(+event+21*86400000).toISOString().slice(0,10);await db.query("INSERT INTO leaderboard_history_clan_capital(location_id,date,clan_tag,clan_name,clan_badge_token,clan_level,capital_points,members,rank) VALUES('global',$1,$2,'Alpha Clan','fixture',10,4300,40,999999)",[laterCapitalDate,group]);graphCapitalDates.push(laterCapitalDate);
   const weekly=await(await fetch(`http://127.0.0.1:${port}/v2/bot/clans/${encodeURIComponent(group)}/capital-trophy-history?season=${season}&months=2`,{headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`}})).json();
   if(weekly.weeks.length<6||weekly.values.filter(v=>v!==null).join(',')!=='4200,4300'||weekly.sampleDates.filter(v=>v!==null).at(-1)!==laterCapitalDate)throw Error('Weekly Capital observations or gaps incorrect '+JSON.stringify(weekly));
   const trophiesChart=await interact(command('graph','over-time',[{name:'attribute',type:3,value:'capitalTrophies'},{name:'season',type:3,value:season},{name:'months',type:4,value:2}]));if(!trophiesChart.posterBytes||!text(trophiesChart).includes('Alpha Clan: 4300')||!text(trophiesChart).includes('weekly observations'))throw Error('Capital weekly chart failed '+text(trophiesChart));
   const weeklyRefresh=await interact({type:3,data:{custom_id:trophiesChart.components[0].components[0].custom_id,component_type:2}},other);if(!text(weeklyRefresh).includes('4300'))throw Error('Weekly graph refresh lost options');
   console.log(JSON.stringify({capitalTrophyGraph:'passed',checks:['latest snapshot instead of sum','missing remains unknown','series PNG and historical gap']}));
   const dailyQuery=async(metric,days=3)=>{const response=await fetch(`http://127.0.0.1:${port}/v2/bot/clans/daily-stats`,{method:'POST',headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},body:JSON.stringify({clans:[group,'#PYLQGRJJ',group],metric,days})});return {status:response.status,data:await response.json()};};
   const gain=await dailyQuery('troopLevels');if(gain.status!==200||gain.data.basis!=='latest_stored_members'||gain.data.series.length!==2||gain.data.series.find(x=>x.tag==='#PYLQGRJJ').values.reduce((a,b)=>a+b,0)!==3)throw Error('Daily upgrade delta or attribution failed '+JSON.stringify(gain));
   const names=await dailyQuery('nameChanges');if(names.data.series.find(x=>x.tag==='#PYLQGRJJ').values.reduce((a,b)=>a+b,0)!==1)throw Error('Name change was not counted once');
   const donations=await dailyQuery('donated');if(donations.data.basis!=='recorded_clan'||donations.data.series.find(x=>x.tag===group).values.reduce((a,b)=>a+b,0)!==100)throw Error('Donation attribution or negative reset incorrect');
   const activity=await dailyQuery('activity');if(activity.data.series.find(x=>x.tag===group).values.reduce((a,b)=>a+b,0)!==2)throw Error('Activity aggregate incorrect');
   if((await dailyQuery('donated',181)).status!==400)throw Error('Unbounded daily range accepted');
   const dayOptions=[{name:'attribute',type:3,value:'donated'},{name:'days',type:4,value:3}];
   const chart=await interact(command('graph','daily',dayOptions));if(!chart.posterBytes||!text(chart).includes('Alpha Clan: 100')||!text(chart).includes('Today is partial'))throw Error('Daily chart output failed '+text(chart));
   const control=chart.components[0].components[0].custom_id;if(!text(await interact({type:3,data:{custom_id:control,component_type:2}},other)).includes('Alpha Clan: 100'))throw Error('Daily refresh lost options');
   dailyGraphFailure=true;const missingDaily=await interact(command('graph','daily',dayOptions));if(missingDaily.posterBytes||!text(missingDaily).includes('unavailable'))throw Error('Missing daily data rendered as zero');dailyGraphFailure=false;
   console.log(JSON.stringify({dailyGraph:'passed',checks:['positive level gains counted once','decreases/boosts ignored','name events','recorded donation clan','schema rejects negative resets','aggregate activity','bounded range','duplicate clans','real PNG','refresh options','upstream failure'],externalDiscordWrites:0}));
   console.log(JSON.stringify({graphMonth:'passed',checks:['actual recorded clan totals','PNG rendering','custom clan selection','public refresh','unavailable clan excluded','multi-season totals','missing season preserved as gap','series refresh options'],externalDiscordWrites:0}));
  }finally{if(graphCapitalDates.length)await db.query('DELETE FROM leaderboard_history_clan_capital WHERE clan_tag=$1 AND date=ANY($2::date[])',[group,graphCapitalDates]);if(graphRaidStarts.length)await db.query('DELETE FROM capital_raid_history WHERE clan_tag=$1 AND start_time=ANY($2::timestamptz[])',[group,graphRaidStarts]);if(graphWarIds.length)await db.query('DELETE FROM wars WHERE war_id=ANY($1::int[])',[graphWarIds]);if(dailyOwned){await db.query('DELETE FROM battles_farming WHERE player_tag=$1',[dailyPlayer]);await db.query('DELETE FROM player_change_history WHERE player_tag=$1',[dailyPlayer]);await db.query('DELETE FROM player_stat_changes WHERE player_tag=$1',[dailyPlayer]);await db.query('DELETE FROM player_online_events WHERE tag=$1',[dailyPlayer]);await db.query('DELETE FROM basic_player WHERE tag=$1',[dailyPlayer]);}if(event)await db.query('DELETE FROM player_stat_changes WHERE event_time=ANY($1::timestamptz[]) AND player_tag=ANY($2::text[])',[[event,...(priorEvent?[priorEvent]:[])],[tag,tags[1]]]);await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']]);}
 }else if(warPanelMode){
  const server='999999999999996510',message='999999999999996599',prep=String(Math.floor(Date.parse(fixturePrep)/1000));
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=$1',[group])).rowCount)throw Error('Synthetic panel scope exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Panel fixture')",[server]);
  try{
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Panel Clan',true,0,2,'',0,0)",[group]);
   await db.query("INSERT INTO server_clans(tag,server_id) VALUES($1,$2)",[group,server]);
   await db.query("INSERT INTO server_logs(server_id,clan_tag,type,webhook_id,message_id,active_war_id) VALUES($1,$2,'war_panel','999999999999996588',$3,$4)",[server,group,message,`${group}v#PYLQGRJJ-${prep}`]);
   const clickPanel=(action,who=actor,extra={})=>interact({type:3,message:{id:message},data:{custom_id:`ck:war:${action}:${group.slice(1)}:${prep}`},...extra},who);
   const refresh=await clickPanel('refresh');if(!text(refresh).includes('War Stats')||text(refresh).includes('Invalid war'))throw Error('Panel refresh swallowed '+text(refresh));
   const attack=await clickPanel('attacks',other);if(!text(attack).includes('Finished Player'))throw Error('Panel attacks failed '+text(attack));
   const defense=await clickPanel('defenses');if(!text(defense).includes('Defenses Taken')||!text(defense).includes('No defenses taken'))throw Error('Panel defenses failed '+text(defense));
   const stale=await clickPanel('refresh',actor,{data:{custom_id:`ck:war:refresh:${group.slice(1)}:${Number(prep)+1}`}});if(stale.flags!==64||!text(stale).includes('different war'))throw Error('Stale panel identity accepted '+text(stale));
   const opponent=await clickPanel('opponent');if(opponent.flags!==64||!text(opponent).includes('Opponent Link'))throw Error('Panel opponent details not private '+text(opponent));
   const foreign=await clickPanel('refresh',actor,{guild_id:'999999999999997000'});if(foreign.flags!==64||!text(foreign).includes('no longer active'))throw Error('Panel crossed server boundary '+text(foreign));
   await db.query("UPDATE server_logs SET disabled=true WHERE server_id=$1 AND type='war_panel'",[server]);
   const disabled=await clickPanel('refresh');if(disabled.flags!==64||!text(disabled).includes('no longer active'))throw Error('Disabled panel still updates '+text(disabled));
   console.log(JSON.stringify({warPanel:'passed',checks:['colon-format refresh routing','attacks and defenses','another viewer','private opponent followup','foreign guild rejected','disabled panel rejected'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM basic_clan WHERE tag=$1',[group]);}
 }else if(roleUsersMode){
  const server='999999999999996510',role='999999999999996580',generation=randomBytes(16).toString('hex');
  if((await db.query('SELECT 1 FROM discord_cache.guilds WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM discord_cache.gateway_shards WHERE application_id=$1',[app])).rowCount)throw Error('Synthetic role users scope exists');
  try{
   await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
   await db.query('INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,$2,$3,0,$4,true,true,true)',[server,JSON.stringify({owner_id:actor}),app,generation]);
   for(const item of [{id:server,name:'@everyone'},{id:role,name:'Managed fixture',managed:true}])await db.query('INSERT INTO discord_cache.roles(guild_id,id,data) VALUES($1,$2,$3)',[server,item.id,JSON.stringify(item)]);
   for(let i=0;i<35;i++){const id=String(999999999999995000n+BigInt(i));await db.query('INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,$3)',[server,id,JSON.stringify({user:{id,username:'User '+String(i).padStart(2,'0')},roles:[role]})]);}
   for(const id of [actor,other])await db.query('INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,$3)',[server,id,JSON.stringify({user:{id,username:'Viewer'},roles:[]})]);
   const first=await interact({type:2,data:{name:'role-users',options:[{name:'role',type:8,value:role}]}});
   if(!text(first).includes('35 members')||!text(first).includes('User 19')||text(first).includes('User 20'))throw Error('Role members first page incorrect '+text(first));
   const next=first.components[0].components.find(c=>c.label==='→');
   const second=await interact({type:3,data:{custom_id:next.custom_id}},other);
   if(!text(second).includes('User 34')||!text(second).includes('Page 2/2')||text(second).includes('User 00'))throw Error('Public member pagination failed '+text(second));
   const all=await interact({type:2,data:{name:'role-users',options:[{name:'role',type:8,value:server}]}});
   if(!text(all).includes('37 members'))throw Error('Implicit everyone membership missing '+text(all));
   const api=async(id,query,status)=>{const response=await fetch(`http://127.0.0.1:${port}/v2/bot/servers/${server}/roles/${id}/members?`+new URLSearchParams(query),{headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`}});const value=await response.json();if(response.status!==status)throw Error('Role API '+response.status+' '+JSON.stringify(value));return value;};
   const value=await api(role,{actorId:actor},200);
   if(Object.keys(value.items[0]).sort().join(',')!=='id,name')throw Error('Role members expose excess fields');
   await api(role,{actorId:'999999999999997999'},403);
   await api('999999999999997888',{actorId:actor},404);
   await db.query('UPDATE discord_cache.guilds SET members_complete=false WHERE id=$1',[server]);
   await api(role,{actorId:actor},503);
   console.log(JSON.stringify({roleUsers:'passed',checks:['managed role members','sorted pagination','another member can refresh','implicit everyone role','display fields only','nonmember forbidden','missing role rejected','incomplete cache unavailable'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM discord_cache.members WHERE guild_id=$1',[server]);await db.query('DELETE FROM discord_cache.roles WHERE guild_id=$1',[server]);await db.query('DELETE FROM discord_cache.guilds WHERE id=$1',[server]);await db.query('DELETE FROM discord_cache.gateway_shards WHERE application_id=$1',[app]);}
 }else if(boostsMode){
  const server='999999999999996510';
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']])).rowCount)throw Error('Synthetic boosts scope exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Boosts')",[server]);
  try{
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Boost Clan',true,0,3,'',0,0),('#PYLQGRJJ','Second Clan',true,0,3,'',0,0)",[group]);
   await db.query("INSERT INTO server_clans(tag,server_id) VALUES($1,$2),('#PYLQGRJJ',$2)",[group,server]);
   const run=options=>interact({type:2,data:{name:'boosts',options}});
   const base=await run([]);
   if(!text(base).includes('2/2 boosted players')||!text(base).includes('3/3 profiles checked')||text(base).includes('Super Archer')||text(base).includes('Moved'))throw Error('Boost membership/active/dedup failed '+text(base));
   const sorted=await run([{name:'limit',type:4,value:1},{name:'sort_order',type:3,value:'desc'}]);
   if(!text(sorted).includes('Zulu')||text(sorted).includes('Alpha')||!text(sorted).includes('1/2 boosted players'))throw Error('Boost sort/limit failed '+text(sorted));
   const empty=await run([{name:'super_troop',type:3,value:'Super Archer'}]);
   if(!text(empty).includes('No active boosts found.')||text(empty).includes('Coverage is incomplete'))throw Error('Inactive troop reported active '+text(empty));
   const filtered=await run([{name:'clan',type:3,value:group},{name:'super_troop',type:3,value:'Sneaky Goblin'},{name:'limit',type:4,value:1},{name:'sort_order',type:3,value:'desc'}]);
   if(!text(filtered).includes('1/1 boosted players')||!text(filtered).includes('Alpha')||text(filtered).includes('Zulu'))throw Error('Boost filter failed '+text(filtered));
   const control=filtered.components[0].components[0].custom_id;
   if(control.length>100)throw Error('Boost refresh ID exceeds Discord limit');
   const refreshed=await interact({type:3,data:{custom_id:control}},other);
   if(!text(refreshed).includes('Sneaky Goblin')||!text(refreshed).includes('1/1 boosted players'))throw Error('Public boost refresh lost filters '+text(refreshed));
   const automatic=await interact({type:4,data:{name:'boosts',options:[{name:'super_troop',type:3,value:'Sneaky',focused:true}]}});
   if(!text(automatic).includes('Sneaky Goblin'))throw Error('Canonical troop autocomplete missing');
   boostFailure=true;
   const incomplete=await run([]);
   if(!text(incomplete).includes('1 unavailable')||!text(incomplete).includes('1/1 boosted players'))throw Error('Missing boost profile not reported '+text(incomplete));
   console.log(JSON.stringify({boosts:'passed',checks:['current active troop flags','family member deduplication','transferred profile excluded','troop filter','limit and ordering','public refresh preserves filters','canonical autocomplete','partial failures explicit'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']]);}
 }else if(warStatsMode){
  const server='999999999999996510',ids=[];
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']])).rowCount)throw Error('Synthetic war stats scope exists');
  const query=async(extra={})=>{const response=await fetch(`http://127.0.0.1:${port}/v2/bot/war-statistics`,{method:'POST',headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},body:JSON.stringify({clans:[group],season:'2026-10',warTypes:['random'],...extra})});const value=await response.json();if(!response.ok)throw Error('War stats API '+response.status+' '+JSON.stringify(value));return value;};
  await db.query("INSERT INTO servers(id,name) VALUES($1,'War stats')",[server]);
  try{
   await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'First Clan',true,0,2,'',0,0),('#PYLQGRJJ','Second Clan',true,0,2,'',0,0)",[group]);
   await db.query("INSERT INTO server_clans(tag,server_id) VALUES($1,$2),('#PYLQGRJJ',$2)",[group,server]);
   const window=await query(),start=new Date(window.start),end=new Date(window.end);
   const hit=(defenderTag,stars,order)=>({defenderTag,stars,destructionPercentage:stars===3?100:50,duration:90,order});
   for(const [n,type] of ['random','cwl','friendly'].entries()){
    const prep=new Date(+start+86400000+n*1000),finish=new Date(+prep+2*86400000);
    const id=(await db.query("INSERT INTO wars(clan_tag,opponent_tag,prep_time,start_time,end_time,size,war_type,state) VALUES($1,'#PYLQGRJJ',$2,$2,$3,2,$4,'warEnded') RETURNING war_id",[group,prep,finish,type])).rows[0].war_id;ids.push(id);
    const member=(tag,name,th,attacks,position)=>({tag,name,townhallLevel:th,mapPosition:position,attacks});
    const side=(tag,name,members)=>({tag,name,badgeToken:'',clanLevel:1,attacks:3,stars:4,destructionPercentage:100,members});
    const payload={state:'warEnded',teamSize:2,attacksPerMember:type==='cwl'?1:2,preparationStartTime:prep.toISOString(),startTime:prep.toISOString(),endTime:finish.toISOString(),battleModifier:'none',clan:side(group,'First Clan',[member(tag,'First',16,type==='cwl'?[hit('#PYLR',3,1)]:[hit('#PYLR',3,1),hit('#PYLY',1,2)],1),member(tags[1],'Second',15,[hit('#PYLR',2,3)],2)]),opponent:side('#PYLQGRJJ','Second Clan',[member('#PYLR','Enemy One',16,[hit(tag,3,4)],1),member('#PYLY','Enemy Two',15,[hit(tags[1],0,5)],2)])};
    await db.query('INSERT INTO war_archive_pending(war_id,end_time,payload) VALUES($1,$2,$3)',[id,finish,JSON.stringify(payload)]);
   }
   // An exact end-boundary preparation time is outside the selected season.
   ids.push((await db.query("INSERT INTO wars(clan_tag,opponent_tag,prep_time,start_time,end_time,size,war_type,state) VALUES($1,'#PYLQGRJJ',$2,$2,$2,2,'random','warEnded') RETURNING war_id",[group,end])).rows[0].war_id);
   const attack=await query();if(!attack.complete||attack.selectedWars!==1||attack.items.find(x=>x.tag===tag)?.attempts!==2||attack.items.find(x=>x.tag===tag)?.matching!==1)throw Error('Attack aggregate mismatch: '+JSON.stringify(attack));
   const defense=await query({view:'defense'});if(defense.items.find(x=>x.tag===tag)?.attempts!==1||defense.items.find(x=>x.tag===tags[1])?.matching!==0)throw Error('Defense orientation mismatch');
   const equal=await query({thFilter:'equal'});if(equal.items.length!==1||equal.items[0].attempts!==1)throw Error('Equal TH filter mismatch');
   const family=await query({clans:[group,'#PYLQGRJJ',group]});if(family.selectedWars!==1||family.items.reduce((n,x)=>n+x.attempts,0)!==5)throw Error('Family war/attack double counting');
   const cwl=await query({warTypes:['cwl']});if(cwl.selectedWars!==1||cwl.items.find(x=>x.tag===tag).attempts!==1)throw Error('CWL filter mismatch');
   const options=[{name:'clan',type:3,value:group},{name:'season',type:3,value:'2026-10'},{name:'war_types',type:3,value:'r'},{name:'min_attacks',type:4,value:1}];
   const board=await interact(command('stats','war',options));if(!text(board).includes('50.0%')||!text(board).includes('First'))throw Error('War stats command missing values: '+text(board));
   const defensive=await interact(command('stats','war',[...options,{name:'type',type:3,value:'d'}]));if(!text(defensive).includes('Lower conceded rate is better')||text(defensive).indexOf('Second')>text(defensive).indexOf('First'))throw Error('Defense ranking/order failed');
   const info=await interact(command('stats','war',[...options,{name:'type',type:3,value:'a'}]));if(!text(info).includes('2.00'))throw Error('Attack information averages failed');
   const latest=await query({season:undefined,warCount:1,warTypes:['cwl']});if(latest.selectedWars!==1||latest.items.find(x=>x.tag===tag)?.attempts!==1)throw Error('Latest matching-war window failed');
   const refresh=board.components[0].components[0].custom_id;if(refresh.length>100)throw Error('Control exceeds Discord limit');
   if(!text(await interact({type:3,data:{custom_id:refresh,component_type:2}},other)).includes('50.0%'))throw Error('Stats refresh lost options');
   const invalid=await fetch(`http://127.0.0.1:${port}/v2/bot/war-statistics`,{method:'POST',headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},body:JSON.stringify({clans:[group],season:'2026-10',days:30})});if(invalid.status!==400)throw Error('Ambiguous windows accepted');
   await db.query('DELETE FROM war_archive_pending WHERE war_id=$1',[ids[0]]);
   const missing=await query();if(missing.complete||missing.items.length)throw Error('Incomplete archive produced a ranking');
   const message=await interact(command('stats','war',options));if(!text(message).includes('No leaderboard was calculated'))throw Error('Archive gap hidden by command');
   console.log(JSON.stringify({warStatistics:'passed',checks:['real bot/API/SQL/archive path','attack and defense orientation','CWL and equal-TH filters','family deduplication','season boundary','public refresh','window validation','missing archive suppresses leaderboard'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM war_archive_pending WHERE war_id=ANY($1::int[])',[ids]);await db.query('DELETE FROM wars WHERE war_id=ANY($1::int[])',[ids]);await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[[group,'#PYLQGRJJ']]);}
 }else if(verificationMode){
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
   if(handoffMode){
    await db.query("INSERT INTO auth_refresh_tokens(token_hash,user_id,device_id,expires_at) VALUES('local-handoff-refresh',$1,'',now()+interval '10 minutes')",[actor]);
    const createRoster=async(serverId)=>{const response=await fetch(`http://127.0.0.1:${port}/v2/roster?server_id=${serverId}`,{method:'POST',headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},body:JSON.stringify({alias:'Settings handoff',roster_type:'family'})});const value=await response.json();if(!response.ok)throw Error('Create handoff roster failed');return value.roster_id;};
    const rosterId=await createRoster(server),foreignRoster=await createRoster(second);
    const settingsOptions=[{name:'roster',type:3,value:rosterId}];
    const denied=await interact(command('roster','settings',settingsOptions),actor,'0');if(!text(denied).includes('Manage'))throw Error('Settings handoff permission bypass');
    const foreign=await interact(command('roster','settings',[{name:'roster',type:3,value:foreignRoster}]),actor,'32');if(text(foreign).includes('Open roster settings'))throw Error('Foreign roster got a handoff');
    const settings=await interact(command('roster','settings',settingsOptions),actor,'32');
    const destination=new URL(settings.components?.[0]?.components?.[0]?.url);
    const params=new URLSearchParams(destination.hash.slice(1)),code=params.get('code');
    if(destination.pathname!=='/access'||destination.search||params.get('roster')!==rosterId||!/^[a-f0-9]{64}$/u.test(code??''))throw Error('Settings handoff target invalid');
    const digest=createHash('sha256').update(code).digest('hex');
    const grant=(await db.query('SELECT user_id,server_id,expires_at FROM dashboard_access_grants WHERE token_hash=$1',[digest])).rows[0];
    if(grant?.user_id!==actor||grant?.server_id!==server||+grant.expires_at>Date.now()+121000)throw Error('Grant owner/server/expiry mismatch');
    const wrongToken=await new SignJWT({}).setProtectedHeader({alg:'HS256'}).setSubject(other).setAudience('clashking-web').setIssuedAt().setExpirationTime('10m').sign(new TextEncoder().encode(keys.JWT_ACCESS_SECRET));
    const exchange=token=>fetch(`http://127.0.0.1:${port}/v2/auth/server-dashboard/exchange`,{method:'POST',headers:{authorization:`Bearer ${token}`,'content-type':'application/json'},body:JSON.stringify({code})});
    if((await exchange(wrongToken)).status!==403)throw Error('Wrong user consumed grant');
    const accepted=await exchange(verificationToken),session=await accepted.json();if(!accepted.ok||session.serverId!==server||!session.access_token)throw Error('Owner could not exchange grant');
    if((await exchange(verificationToken)).status!==401)throw Error('One-use grant replay accepted');
    const scoped=await fetch(`http://127.0.0.1:${port}/v2/server/${server}/rosters/${rosterId}`,{headers:{authorization:`Bearer ${session.access_token}`}});if(!scoped.ok)throw Error('Scoped session cannot open own roster');
    const blocked=await fetch(`http://127.0.0.1:${port}/v2/server/${second}/rosters/${foreignRoster}`,{headers:{authorization:`Bearer ${session.access_token}`}});if(blocked.status!==403)throw Error('Scoped session escaped server');
    const expired=await interact(command('roster','settings',settingsOptions),actor,'32');
    const expiredCode=new URLSearchParams(new URL(expired.components[0].components[0].url).hash.slice(1)).get('code');
    await db.query("UPDATE dashboard_access_grants SET expires_at=now()-interval '1 minute' WHERE token_hash=$1",[createHash('sha256').update(expiredCode).digest('hex')]);
    const expiry=await fetch(`http://127.0.0.1:${port}/v2/auth/server-dashboard/exchange`,{method:'POST',headers:{authorization:`Bearer ${verificationToken}`,'content-type':'application/json'},body:JSON.stringify({code:expiredCode})});if(expiry.status!==401)throw Error('Expired grant accepted');
    await db.query("DELETE FROM auth_refresh_tokens WHERE token_hash='local-handoff-refresh' AND user_id=$1",[actor]);
    const revoked=await fetch(`http://127.0.0.1:${port}/v2/server/${server}/rosters/${rosterId}`,{headers:{authorization:`Bearer ${session.access_token}`}});if(revoked.status!==401)throw Error('Signed-out browser retained scoped access');
    console.log(JSON.stringify({rosterHandoff:'passed' ,checks:['manager only','roster/server lookup','fragment target','grant ownership and expiry','wrong user rejected','one use only','scoped roster read','cross-server rejection','expired code rejected','parent session revocation'],browserNavigation:'not exercised'}));
   }
   console.log(JSON.stringify({clanVerification:'passed',checks:['real API/SQL','random initial challenge','stable pending challenge','cross-server collision exclusion','full word rotation/wrap','description verification'],externalDiscordWrites:0}));
  }finally{verificationDescription='';await db.query("DELETE FROM auth_refresh_tokens WHERE token_hash='local-handoff-refresh' AND user_id=$1",[actor]);await db.query('DELETE FROM dashboard_scoped_sessions WHERE server_id=ANY($1::text[])',[[server,second]]);await db.query('DELETE FROM dashboard_access_grants WHERE server_id=ANY($1::text[])',[[server,second]]);await db.query('DELETE FROM servers WHERE id=ANY($1::text[])',[[server,second]]);await db.query('DELETE FROM basic_clan WHERE tag=$1',[group]);await db.query('DELETE FROM discord_cache.guilds WHERE id=ANY($1::text[])',[[server,second]]);await db.query('DELETE FROM discord_cache.gateway_shards WHERE application_id=$1',[app]);}
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
   const foreignRoster=await request('/v2/roster?server_id='+elsewhere,{alias:'Other server secret',roster_type:'family',members:[{tag:tags[1],name:'Stored member',townhall:15}]});
   if(warEventMode){
    const run=action=>interact(command('clan','war-events',[{name:'clan',type:3,value:group},{name:'action',type:3,value:action}]),actor,'32');
    const blocked=await interact(command('clan','war-events',[{name:'clan',type:3,value:group},{name:'action',type:3,value:'enable'}]),actor,'0');
    if(!text(blocked).includes('Manage Server'))throw Error('War events permission bypass');
    if(!text(await run('view')).includes('Disabled'))throw Error('War events default not off');
    if(!text(await run('enable')).includes('Enabled'))throw Error('War events not enabled');
    if(!(await db.query('SELECT war_events_enabled FROM server_clans WHERE tag=$1 AND server_id=$2',[group,server])).rows[0]?.war_events_enabled)throw Error('War event setting not persisted');
    if(!text(await run('disable')).includes('Disabled'))throw Error('War events not disabled');
    const base=`http://127.0.0.1:${port}/v2/server/${server}/clan/`;
    const put=(tag,body,auth=true)=>fetch(base+encodeURIComponent(tag)+'/war-events',{method:'PUT',headers:{'Content-Type':'application/json',...(auth?{Authorization:`Bearer ${keys.API_BOT_TOKEN}`}:{})},body:JSON.stringify(body)});
    if((await put(group,{enabled:true},false)).status!==401||(await put(group,{enabled:'yes'})).status!==400||(await put('#QQQQ',{enabled:true})).status!==404)throw Error('War event validation or linked-clan scope failed');
    console.log(JSON.stringify({warEventsSettings:'passed',checks:['manager only','default off','enable persistence','view','disable','auth','invalid boolean','unlinked clan'],externalDiscordWrites:0}));
   }
   if(memberWarningMode){
    const base=[{name:'clan',type:3,value:group}];
    const cmd=(action,extra=[])=>command('clan','member-warning',[...base,{name:'action',type:3,value:action},...extra]);
    const values=[{name:'channel',type:7,value:'999999999999996511'},{name:'below',type:4,value:10},{name:'above',type:4,value:45},{name:'role',type:8,value:newRole}];
    const denied=await interact(cmd('set',values),actor,'0');if(!text(denied).includes('Manage Server'))throw Error('Warning permission bypass');
    const created=await interact(cmd('set',values),actor,'32');if(!text(created).includes('Saved warnings'))throw Error('Warning save failed '+text(created));
    const saved=(await db.query('SELECT below_count,above_count,role_id FROM server_clan_member_warnings WHERE server_id=$1 AND clan_tag=$2',[server,group])).rows[0];if(saved?.below_count!==10||saved?.above_count!==45||saved?.role_id!==newRole)throw Error('Warning configuration missing');
    if(!text(await interact(cmd('view'),actor,'32')).includes('Above 45'))throw Error('Warning view failed');
    const invalid=await interact(cmd('set',values.map(v=>v.name==='below'?{...v,value:49}:v)),actor,'32');if(text(invalid).includes('Saved warnings'))throw Error('Overlapping warning thresholds accepted');
    const foreign=await interact(cmd('set',values.map(v=>v.name==='channel'?{...v,value:'999999999999996599'}:v)),actor,'32');if(text(foreign).includes('Saved warnings'))throw Error('Foreign warning channel accepted');
    const broad=await interact(cmd('set',values.map(v=>v.name==='role'?{...v,value:server}:v)),actor,'32');if(text(broad).includes('Saved warnings'))throw Error('Everyone warning role accepted');
    const disabled=await interact(cmd('disable'),actor,'32');if(!text(disabled).includes('disabled')||(await db.query('SELECT 1 FROM server_clan_member_warnings WHERE server_id=$1',[server])).rowCount)throw Error('Warning disable failed');
    console.log(JSON.stringify({memberWarningConfiguration:'passed',checks:['manager-only command','actual API and SQL persistence','view','invalid thresholds','foreign channel','everyone role rejected','disable']}));
   }
   if(quickPanelMode){
    if((await db.query('SELECT 1 FROM discord_cache.gateway_shards WHERE application_id=$1',[app])).rowCount)throw Error('Synthetic panel gateway exists');
    const generation=randomBytes(16).toString('hex');
    await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
    await db.query('INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,$2,$3,0,$4,true,true,true)',[server,JSON.stringify({owner_id:other}),app,generation]);
    await db.query('INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,$3)',[server,actor,JSON.stringify({user:{id:actor},roles:[]})]);
    const post=options=>interact({type:2,data:{name:'buttons',options}},actor,'32');
    const denied=await interact({type:2,data:{name:'buttons'}},actor,'0');if(!text(denied).includes('Manage Server'))throw Error('Panel post permission bypass');
    const posted=await post([{name:'help',type:5,value:true}]);if(!text(posted).includes('Panel posted')||sentReminders.length!==1)throw Error('Panel was not posted');
    const payload=sentReminders[0];if(payload.components[0].components.length!==5||payload.allowed_mentions.parse.length)throw Error('Panel controls/mentions invalid');
    const click=async(action,who=actor,legacy=false)=>interact({type:3,data:{component_type:2,custom_id:legacy?action:`ck:quick:${server}:${action}`}},who);
    const link=await click('link');if(link.custom_id!=='ck:link:submit')throw Error('Panel link did not open existing modal');
    const help=await click('help');if(help.flags!==64||!help.embeds?.length)throw Error('Panel help not private');
    const own=await click('rosters');if(own.flags!==64||!text(own).includes('Visible roster')||text(own).includes('Other server secret'))throw Error('Own roster panel scope failed');
    const stranger=await click('rosters',other);if(text(stranger).includes('Stored member'))throw Error('Panel reused creator identity');
    await db.query('UPDATE player_links SET hidden=true,is_verified=true WHERE tag=$1',[tags[1]]);if(text(await click('rosters')).includes('Stored member'))throw Error('Hidden link exposed');await db.query('UPDATE player_links SET hidden=false,is_verified=false WHERE tag=$1',[tags[1]]);
    if(!text(await click('MyRosters',actor,true)).includes('Visible roster'))throw Error('Legacy roster button broken');
    const refresh=await click('refresh');if(refresh.flags!==64||!text(refresh).includes('refreshes completed'))throw Error('Panel refresh failed '+text(refresh));
    const todo=await click('todo');if(todo.flags!==64||!todo.embeds?.length)throw Error('Panel to-do failed '+text(todo));
    const cross=await interact({type:3,data:{component_type:2,custom_id:`ck:quick:${elsewhere}:rosters`}});if(!text(cross).includes('another server'))throw Error('Foreign panel accepted');
    const badChannel=await post([{name:'channel',type:7,value:'999999999999996599'}]);if(text(badChannel).includes('Panel posted')||sentReminders.length!==1)throw Error('Panel posted to foreign channel');
    const empty=await post(['link','help','refresh','todo','rosters'].map(name=>({name,type:5,value:false})));if(!text(empty).includes('at least one'))throw Error('Empty panel accepted');
    console.log(JSON.stringify({quickPanel:'passed',checks:['manager-only post','five controls','link modal','private help/tasks/refresh','clicker identity','own roster scope','hidden links excluded','legacy IDs','cross-server rejection','empty panel rejected'],externalDiscordWrites:0,localPanelPosts:sentReminders.length}));
   }
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
   const rosterOption={name:'roster',type:3,value:created.roster_id};
   const destination=await request('/v2/roster?server_id='+server,{alias:'Destination',roster_type:'family'});
   const playerInput={name:'players',type:3,value:tag};
   const addDenied=await interact(command('roster','add-player',[rosterOption,playerInput]),actor,'0');if(!text(addDenied).includes('Manage'))throw Error('Roster add permission bypass');
   const added=await interact(command('roster','add-player',[rosterOption,playerInput]),actor,'32');if(!text(added).includes('Added 1'))throw Error('Roster add failed '+text(added));
   const addedRow=(await db.query('SELECT name,townhall FROM roster_members WHERE roster_id=$1 AND tag=$2',[created.roster_id,tag])).rows[0];if(addedRow?.name!=='Current Player'||addedRow?.townhall!==16)throw Error('Added player snapshot not hydrated');
   const groupAction=(action,extra=[])=>command('roster','groups',[{name:'action',type:3,value:action},...extra]);
   const labelName={name:'name',type:3,value:'War starters'};
   const labelDenied=await interact(groupAction('add',[labelName]),actor,'0');if(!text(labelDenied).includes('Manage'))throw Error('Label permission bypass');
   const labelCreated=await interact(groupAction('add',[labelName]),actor,'32');if(!text(labelCreated).includes('Created'))throw Error('Label create failed '+text(labelCreated));
   const label=(await db.query('SELECT id FROM roster_member_groups WHERE server_id=$1 AND name=$2',[server,'War starters'])).rows[0];
   const labelOption={name:'group',type:3,value:label.id};
   const assigned=await interact(command('roster','group-player',[rosterOption,playerInput,labelOption]),actor,'32');if(!text(assigned).includes('Updated'))throw Error('Label assign failed '+text(assigned));
   const labeledView=await interact(command('roster','view',[rosterOption]),actor,'32');if(!text(labeledView).includes('War starters'))throw Error('Roster label absent from view');
   const blockedDelete=await interact(groupAction('delete',[labelOption]),actor,'32');if(text(blockedDelete).includes('Deleted'))throw Error('Assigned label deletion accepted');
   const foreignLabel=(await db.query("INSERT INTO roster_member_groups(server_id,name) VALUES($1,'Foreign label') RETURNING id",[elsewhere])).rows[0];
   const crossLabel=await interact(command('roster','group-player',[rosterOption,playerInput,{...labelOption,value:foreignLabel.id}]),actor,'32');if(text(crossLabel).includes('Updated'))throw Error('Foreign label assignment accepted');
   const invalidBatch=await interact(command('roster','group-player',[rosterOption,{...playerInput,value:`${tag} #QQQ`},labelOption]),actor,'32');if(text(invalidBatch).includes('Updated'))throw Error('Unknown member label assignment accepted');
   const renamed=await interact(groupAction('rename',[labelOption,{...labelName,value:'First team'}]),actor,'32');if(!text(renamed).includes('Renamed'))throw Error('Label rename failed');
   if(!text(await interact(command('roster','view',[rosterOption]),actor,'32')).includes('First team'))throw Error('Renamed label absent');
   const main=await interact(command('roster','group-player',[rosterOption,playerInput]),actor,'32');if(!text(main).includes('to Main'))throw Error('Move to Main failed');
   const labelDeleted=await interact(groupAction('delete',[labelOption]),actor,'32');if(!text(labelDeleted).includes('Deleted'))throw Error('Unused label deletion failed');
   if((await db.query('SELECT member_group_id FROM roster_members WHERE roster_id=$1 AND tag=$2',[created.roster_id,tag])).rows[0].member_group_id!==null)throw Error('Main retained label');
   await interact(groupAction('add',[{...labelName,value:'Preserved label'}]),actor,'32');
   const preserved=(await db.query('SELECT id FROM roster_member_groups WHERE server_id=$1 AND name=$2',[server,'Preserved label'])).rows[0];
   await interact(command('roster','group-player',[rosterOption,playerInput,{...labelOption,value:preserved.id}]),actor,'32');
   const moveOptions=[rosterOption,playerInput,{name:'destination',type:3,value:destination.roster_id}];
   const moved=await interact(command('roster','move-player',moveOptions),actor,'32');if(!text(moved).includes('Moved 1'))throw Error('Roster move failed '+text(moved));
   if((await db.query('SELECT 1 FROM roster_members WHERE roster_id=$1 AND tag=$2',[created.roster_id,tag])).rowCount||!(await db.query('SELECT 1 FROM roster_members WHERE roster_id=$1 AND tag=$2',[destination.roster_id,tag])).rowCount)throw Error('Move was not atomic');
   if((await db.query('SELECT member_group_id FROM roster_members WHERE roster_id=$1 AND tag=$2',[destination.roster_id,tag])).rows[0]?.member_group_id!==preserved.id)throw Error('Move discarded label');
   const foreign=await interact(command('roster','move-player',[{...rosterOption,value:destination.roster_id},playerInput,{name:'destination',type:3,value:foreignRoster.roster_id}]),actor,'32');if(text(foreign).includes('Moved 1'))throw Error('Moved across server boundary');
   const copied=await interact(command('roster','copy',[{...rosterOption,value:destination.roster_id},{name:'name',type:3,value:'Copied roster'},{name:'members',type:5,value:true}]),actor,'32');if(!text(copied).includes('1 members copied'))throw Error('Copy failed '+text(copied));
   const copy=(await db.query("SELECT id FROM rosters WHERE server_id=$1 AND alias='Copied roster'",[server])).rows[0];
   if((await db.query('SELECT member_group_id FROM roster_members WHERE roster_id=$1 AND tag=$2',[copy.id,tag])).rows[0]?.member_group_id!==preserved.id)throw Error('Copy discarded label');
   const copyOption={...rosterOption,value:copy.id};
   const notConfirmed=await interact(command('roster','delete',[copyOption,{name:'type',type:3,value:'roster'},{name:'confirm',type:5,value:false}]),actor,'32');if(!text(notConfirmed).includes('confirm'))throw Error('Delete lacked confirmation');
   const removed=await interact(command('roster','remove-player',[copyOption,playerInput]),actor,'32');if(!text(removed).includes('Removed 1'))throw Error('Remove failed '+text(removed));
   const cleared=await interact(command('roster','delete',[{...rosterOption,value:destination.roster_id},{name:'type',type:3,value:'members'},{name:'confirm',type:5,value:true}]),actor,'32');if(!text(cleared).includes('Cleared members'))throw Error('Clear failed '+text(cleared));
   rosterProfileFailure=true;
   const failedAdd=await interact(command('roster','add-player',[{...rosterOption,value:destination.roster_id},{name:'players',type:3,value:`${tag} ${tags[1]}`}]),actor,'32');
   if(!text(failedAdd).includes('no players were added')||(await db.query('SELECT 1 FROM roster_members WHERE roster_id=$1',[destination.roster_id])).rowCount)throw Error('Failed profile partially added roster batch');
   rosterProfileFailure=false;
   const deleted=await interact(command('roster','delete',[copyOption,{name:'type',type:3,value:'roster'},{name:'confirm',type:5,value:true}]),actor,'32');if(!text(deleted).includes('Deleted roster')||(await db.query('SELECT 1 FROM rosters WHERE id=$1',[copy.id])).rowCount)throw Error('Delete failed '+text(deleted));
   console.log(JSON.stringify({rosterReads:'passed',checks:['label create/rename/assign/display','foreign label rejected','in-use deletion rejected','Main and unused label deletion','actual API-created rosters','server-scoped list and selection','direct view','player and self search','search refresh','permission gate','failed profile retained','actual stored profile update','cooldown reuse','permission-checked add','hydrated profile','atomic move','foreign server move rejected','copy members','remove members','clear and delete confirmation'],externalDiscordWrites:0}));
  }finally{if(quickPanelMode){await db.query('DELETE FROM discord_cache.guilds WHERE id=$1',[server]);await db.query('DELETE FROM discord_cache.gateway_shards WHERE application_id=$1',[app]);}await db.query('DELETE FROM servers WHERE id=ANY($1::text[])',[[server,elsewhere]]);await db.query('DELETE FROM basic_clan WHERE tag=$1',[group]);}
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
 }else if(activityMode){
  const server='999999999999996510',clans=[group,'#PYLQGRJJ'],players=['#VQQQQY','#VQQQQU'];
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount||(await db.query('SELECT 1 FROM basic_clan WHERE tag=ANY($1::text[])',[clans])).rowCount||(await db.query('SELECT 1 FROM basic_player WHERE tag=ANY($1::text[])',[players])).rowCount||(await db.query('SELECT 1 FROM player_online_events WHERE tag=ANY($1::text[])',[players])).rowCount)throw Error('Activity fixture exists');
  const requestActivity=(body,auth=true)=>fetch(`http://127.0.0.1:${port}/v2/bot/clans/activity`,{method:'POST',headers:{'Content-Type':'application/json',...(auth?{Authorization:`Bearer ${keys.API_BOT_TOKEN}`}:{})},body:JSON.stringify(body)});
  try{
   await db.query("INSERT INTO servers(id,name) VALUES($1,'Activity')",[server]);
   for(const [i,clan] of clans.entries()){await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,$2,true,0,0,'',0,0)",[clan,'Activity Clan '+i]);await db.query('INSERT INTO server_clans(tag,server_id) VALUES($1,$2)',[clan,server]);}
   await db.query("INSERT INTO basic_player(tag,name,clan_tag,townhall_level) VALUES($1,'Active Alpha','#QQQQ',16),($2,'Quiet Zulu','#QQQQ',18)",players);
   const window=await (await fetch(`http://127.0.0.1:${port}/v2/bot/clans/${encodeURIComponent(group)}/season-stats`,{headers:{Authorization:`Bearer ${keys.API_BOT_TOKEN}`}})).json();
   if(!window.current)throw Error('Expected current activity season');
   const start=new Date(window.start),end=new Date(window.end),recent=new Date(Date.now()-3600000),older=new Date(Date.now()-7200000);
   await db.query("INSERT INTO player_online_events(tag,clan_tag,seen_at) VALUES($1,$3,$5),($1,$4,$6),($2,$3,$6),($1,$3,$7),($1,$3,$8),($1,'#QQQQ',$9)",[...players,...clans,older,recent,new Date(+start-1000),end,new Date(Date.now()-60000)]);
   const response=await requestActivity({clanTags:[...clans,group]}),data=await response.json();
   if(!response.ok||data.items.length!==2||data.items.find(row=>row.tag===players[0]).activity!==2||data.clanTotals.find(row=>row.tag===group).activity!==2||data.clanTotals.find(row=>row.tag===clans[1]).activity!==1)throw Error('Activity attribution/deduplication failed '+JSON.stringify(data));
   if(Date.parse(data.items.find(row=>row.tag===players[0]).lastObservedAt)<+recent)throw Error('Latest activity outside family not retained');
   const family=await interact(command('family','activity'));
   if(family.embeds.length!==2||!text(family).includes('Active Alpha')||!text(family).includes('Clan activity totals')||text(family).includes('No recorded activity'))throw Error('Family activity missing '+text(family));
   if(family.embeds[0].description.match(/Active Alpha/g)?.length!==1||family.embeds[0].description.indexOf('Active Alpha')>family.embeds[0].description.indexOf('Quiet Zulu'))throw Error('Player not deduplicated or activity sort wrong');
   const refresh=await interact({type:3,data:{custom_id:family.components[0].components[0].custom_id,component_type:2}},other);
   if(!text(refresh).includes('Clan activity totals'))throw Error('Public activity refresh failed');
   const filtered=await interact(command('clan','activity',[{name:'clan',type:3,value:group},{name:'townhall',type:4,value:18},{name:'sort_by',type:3,value:'online'}]));
   if(!text(filtered).includes('Quiet Zulu')||text(filtered).includes('Active Alpha'))throw Error('Activity townhall filter failed');
   const ascending=await interact(command('family','activity',[{name:'sort_order',type:3,value:'asc'},{name:'limit',type:4,value:1}]));
   if(!ascending.embeds[0].description.includes('Quiet Zulu')||ascending.embeds[0].description.includes('Active Alpha'))throw Error('Ascending order or limit failed');
   const oldWindow=await (await fetch(`http://127.0.0.1:${port}/v2/bot/clans/${encodeURIComponent(group)}/season-stats?season=2024-01`,{headers:{Authorization:`Bearer ${keys.API_BOT_TOKEN}`}})).json();
   await db.query('INSERT INTO player_online_events(tag,clan_tag,seen_at) VALUES($1,$2,$3),($1,$2,$4)',[players[0],group,new Date(oldWindow.start),new Date(oldWindow.end)]);
   const historical=await (await requestActivity({clanTags:clans,season:'2024-01'})).json();
   if(historical.current||historical.items.length!==1||historical.items[0].activity!==1||historical.items.some(row=>row.lastObservedAt!==null))throw Error('Historical online or season boundary leakage');
   const pastMessage=await interact(command('family','activity',[{name:'season',type:3,value:'2024-01'}]));
   if(!pastMessage.embeds[0].description.includes('Active Alpha')||pastMessage.embeds[0].description.includes(' LO '))throw Error('Historical display omitted count or showed online');
   const badSort=await interact(command('family','activity',[{name:'season',type:3,value:'2024-01'},{name:'sort_by',type:3,value:'online'}]));
   if(!text(badSort).includes('current season'))throw Error('Historical online sort accepted');
   if((await requestActivity({clanTags:clans},false)).status!==401||(await requestActivity({clanTags:[]})).status!==400||(await requestActivity({clanTags:Array(201).fill(group)})).status!==400||(await requestActivity({clanTags:clans,season:'2099-01'})).status!==400)throw Error('Activity auth/bounds failed');
   for(const message of [family,filtered,refresh])if(message.embeds.reduce((n,e)=>n+(e.title?.length??0)+(e.description?.length??0)+(e.footer?.text?.length??0),0)>6000)throw Error('Activity Discord size limit');
   console.log(JSON.stringify({activity:'passed',checks:['real Bot/API/SQL','former members included','family moves deduplicated','event clan attribution','exclusive season boundaries','current last observed anywhere','historical online hidden','Town Hall filter','sort and public refresh','clan totals','authentication and bounds','Discord size'],externalDiscordWrites:0}));
  }finally{await db.query('DELETE FROM player_online_events WHERE tag=ANY($1::text[])',[players]);await db.query('DELETE FROM basic_player WHERE tag=ANY($1::text[])',[players]);await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[clans]);}
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
  if((await db.query('SELECT 1 FROM basic_clan WHERE tag=$1',[group])).rowCount)throw Error('Synthetic role clan exists');
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
   const configRequest=async(method,path,body)=>{
    const response=await fetch(`http://127.0.0.1:${port}/v2/server/${roleServer}${path}`,{method,headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
    const value=await response.json();if(!response.ok)throw Error('Clan configuration failed: '+response.status+' '+JSON.stringify(value));return value;
   };
   const jobRevision=async()=>Number((await db.query('SELECT revision FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0].revision);
   const familyRule=await ruleRequest('POST','',{type:'family',option:'family',role_id:oldRole});
   await flushRuleChange();
   if(memberRoles.has(oldRole))throw Error('Player was unexpectedly in configured family');
   await configRequest('POST','/clans',{tag:group});
   await flushRuleChange();if(!memberRoles.has(oldRole))throw Error('Adding a clan did not reconcile family role');
   let beforeConfig=await jobRevision();
   await configRequest('POST','/clans',{tag:group});
   if(await jobRevision()!==beforeConfig)throw Error('Duplicate clan add requeued roles');
   await settings({nickname_rule:'{player_name} {clan_abbr}'});await flushRuleChange();
   await configRequest('PATCH',`/clan/${encodeURIComponent(group)}/settings`,{abbreviation:'CK',category:'Main'});
   await flushRuleChange();if(!nickname.endsWith('CK'))throw Error('Clan abbreviation did not refresh nickname');
   beforeConfig=await jobRevision();
   await configRequest('PATCH',`/clan/${encodeURIComponent(group)}/settings`,{abbreviation:'CK',category:'Main'});
   if(await jobRevision()!==beforeConfig)throw Error('Identical clan settings requeued roles');
   const category=(await configRequest('GET','/clan-categories')).items.find(row=>row.name==='Main');
   await ruleRequest('POST','',{type:'clan_category',option:'Main',role_id:oldRole});await flushRuleChange();
   // Remove the overlapping rule through the API to isolate category matching.
   await ruleRequest('DELETE','/'+familyRule.role.id);await flushRuleChange();
   await configRequest('PATCH','/clan-categories/'+category.id,{name:'Other'});await flushRuleChange();
   if(memberRoles.has(oldRole))throw Error('Renamed category left stale role');
   beforeConfig=await jobRevision();
   await configRequest('PATCH','/clan-categories/'+category.id,{name:'Other'});
   if(await jobRevision()!==beforeConfig)throw Error('Unchanged category rename requeued roles');
   await ruleRequest('POST','',{type:'clan_category',option:'Other',role_id:oldRole});await flushRuleChange();
   if(!memberRoles.has(oldRole))throw Error('Category role was not applied');
   await db.query("UPDATE role_refresh_jobs SET grace_until=now()+interval '10 minutes',due_at=now()+interval '10 minutes',completed_at=NULL WHERE id=$1",[jobId]);
   await configRequest('DELETE','/clan-categories/'+category.id);
   const grace=(await db.query('SELECT grace_until,due_at FROM role_refresh_jobs WHERE id=$1',[jobId])).rows[0];
   if(!grace.grace_until||+grace.grace_until!==+grace.due_at)throw Error('Category change bypassed leave grace');
   await db.query('UPDATE role_refresh_jobs SET grace_until=NULL,due_at=now() WHERE id=$1',[jobId]);await flushRuleChange();
   if(memberRoles.has(oldRole))throw Error('Deleted category left stale role');
   await ruleRequest('POST','',{type:'family',option:'family',role_id:oldRole});await flushRuleChange();
   await configRequest('DELETE','/clans/'+encodeURIComponent(group));await flushRuleChange();
   if(memberRoles.has(oldRole))throw Error('Removed clan left stale family role');
   beforeConfig=await jobRevision();await configRequest('DELETE','/clans/'+encodeURIComponent(group));
   if(await jobRevision()!==beforeConfig)throw Error('Missing clan removal requeued roles');
   await settings({auto_eval_status:false});
   const joined=new Date();joined.setUTCFullYear(joined.getUTCFullYear()-2);joined.setUTCDate(joined.getUTCDate()-1);roleJoinedAt=joined.toISOString();
   await db.query("UPDATE discord_cache.members SET data=jsonb_set(data,'{joined_at}',to_jsonb($3::text)) WHERE guild_id=$1 AND user_id=$2",[roleServer,actor,roleJoinedAt]);
   const tenureOptions=[{name:'mode',type:3,value:'add'},{name:'months',type:4,value:12},{name:'role',type:8,value:oldRole}];
   const deniedTenure=await interact(command('roles','tenure',tenureOptions));if(!text(deniedTenure).includes('Manage Server'))throw Error('Tenure configuration permission bypassed');
   const savedTenure=await interact(command('roles','tenure',tenureOptions),actor,'32');if(!text(savedTenure).includes('Saved the 12-month'))throw Error('Tenure command did not save rule '+text(savedTenure));
   await ruleRequest('POST','',{type:'status',option:'36',role_id:newRole});
   const tenureId=`tenure:${roleServer}:${actor}`;
   const legacyClaim=await fetch(`http://127.0.0.1:${port}/v2/bot/role-refresh/claim`,{method:'POST',headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},body:JSON.stringify({serverId:roleServer})});if(!legacyClaim.ok||(await db.query('SELECT 1 FROM role_refresh_jobs WHERE id=$1',[tenureId])).rowCount)throw Error('Old consumer scheduled unsupported tenure work');
   await (await bot.getWorker()).scheduled({cron:'* * * * *'});
   await wait(async()=>Boolean((await db.query('SELECT completed_at FROM role_refresh_jobs WHERE id=$1',[tenureId])).rows[0]?.completed_at),'tenure with game automation disabled');
   if(!memberRoles.has(oldRole)||!memberRoles.has(newRole))throw Error('Tenure milestone missing or shared role removed');
   joined.setUTCFullYear(joined.getUTCFullYear()-2);roleJoinedAt=joined.toISOString();
   await db.query("UPDATE discord_cache.members SET data=jsonb_set(data,'{joined_at}',to_jsonb($3::text)) WHERE guild_id=$1 AND user_id=$2",[roleServer,actor,roleJoinedAt]);
   await db.query("UPDATE role_refresh_jobs SET completed_at=NULL,attempts=12,updated_at=now()-interval '2 hours' WHERE id=$1",[tenureId]);
   await (await bot.getWorker()).scheduled({cron:'* * * * *'});
   await wait(async()=>{const value=(await db.query('SELECT completed_at FROM role_refresh_jobs WHERE id=$1',[tenureId])).rows[0]?.completed_at;return value&&+value>Date.now()-60000;},'tenure progression');
   if(memberRoles.has(oldRole)||!memberRoles.has(newRole)||!memberRoles.has(unmanagedRole))throw Error('Highest tenure threshold not applied safely');
   roleJoinedAt=undefined;memberRoles.add(oldRole);
   const missingJoin=await interact({type:2,data:{name:'refresh'}});
   if(!text(missingJoin).includes('1/1 refreshes completed')||!memberRoles.has(oldRole))throw Error('Missing join date revoked tenure');
   // Roster roles share the existing refresh planner, even when game autoeval is off.
   await db.query('DELETE FROM role_refresh_jobs WHERE server_id=$1',[roleServer]);
   await db.query('DELETE FROM server_roles WHERE server_id=$1',[roleServer]);
   await db.query('INSERT INTO server_clans(server_id,tag) VALUES($1,$2) ON CONFLICT DO NOTHING',[roleServer,group]);
   memberRoles.delete(oldRole);memberRoles.delete(newRole);
   const rosterApi=async(path,body,method='POST')=>{const response=await fetch(`http://127.0.0.1:${port}`+path,{method,headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},body:JSON.stringify(body)});const value=await response.json();if(!response.ok)throw Error('Roster role API '+response.status+' '+JSON.stringify(value));return value;};
   const roster1=await rosterApi('/v2/roster?server_id='+roleServer,{alias:'Role one',roster_type:'family',members:[{tag:tags[0],name:'Roster member',townhall:16}]});
   const roster2=await rosterApi('/v2/roster?server_id='+roleServer,{alias:'Role two',roster_type:'family',members:[{tag:tags[0],name:'Roster member',townhall:16}]});
   const ropt=id=>({name:'roster',type:3,value:id});
   const roleopt=id=>({name:'role',type:8,value:id});
   const deniedRosterRole=await interact(command('roster','role',[ropt(roster1.roster_id),roleopt(oldRole)]),actor,'0');if(!text(deniedRosterRole).includes('Manage'))throw Error('Roster role permission bypass');
   const setRosterRole=async(id,role,extra=[])=>{const response=await interact(command('roster','role',[ropt(id),...(role?[roleopt(role)]:[]),...extra]),actor,'32');if(!text(response).includes('saved'))throw Error('Roster role config failed '+text(response));};
   const drainRoster=async()=>{const response=await interact(command('roster','role-refresh',[ropt(roster1.roster_id)]),actor,'32');if(!text(response).includes('Queued'))throw Error('Roster role refresh failed '+text(response));};
   await setRosterRole(roster1.roster_id,oldRole);
   const oldConsumer=await fetch(`http://127.0.0.1:${port}/v2/bot/role-refresh/claim`,{method:'POST',headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},body:JSON.stringify({serverId:roleServer})});
   if((await oldConsumer.json()).jobs.some(job=>job.categories.includes('roster')))throw Error('Old consumer claimed unsupported roster job');
   const queuedRosterId=`roster:${roleServer}:${actor}`;
   const revisionBefore=(await db.query('SELECT revision FROM role_refresh_jobs WHERE id=$1',[queuedRosterId])).rows[0].revision;
   await setRosterRole(roster1.roster_id,oldRole);
   if((await db.query('SELECT revision FROM role_refresh_jobs WHERE id=$1',[queuedRosterId])).rows[0].revision!==revisionBefore)throw Error('Unchanged role requeued');
   const claimResponse=await rosterApi('/v2/bot/role-refresh/claim',{serverId:roleServer,includeRoster:true});
   const claimed=claimResponse.jobs.find(job=>job.id===queuedRosterId);if(!claimed)throw Error('Missing claimed roster job');
   await setRosterRole(roster1.roster_id,newRole);
   const stale=await rosterApi('/v2/bot/role-refresh/validate',{id:claimed.id,token:claimed.token,accountTags:tags});if(stale.valid)throw Error('Stale roster lease accepted');
   await rosterApi('/v2/bot/role-refresh/complete',{id:claimed.id,token:claimed.token,success:false,result:{error:'local stale fixture'}});
   await setRosterRole(roster1.roster_id,oldRole);
   await drainRoster();if(!memberRoles.has(oldRole))throw Error('Roster role was not added');
   await setRosterRole(roster2.roster_id,oldRole);await drainRoster();
   await rosterApi(`/v2/roster/${roster1.roster_id}/members?server_id=${roleServer}`,{operation:'remove',player_tags:[tags[0]]});await drainRoster();if(!memberRoles.has(oldRole))throw Error('Other roster did not preserve shared role');
   await rosterApi(`/v2/roster/${roster2.roster_id}/members?server_id=${roleServer}`,{operation:'remove',player_tags:[tags[0]]});await drainRoster();if(memberRoles.has(oldRole))throw Error('Last roster removal left role');
   await rosterApi(`/v2/roster/${roster1.roster_id}/members?server_id=${roleServer}`,{members:[{tag:tags[0],name:'Roster member',townhall:16}]});await drainRoster();
   await setRosterRole(roster1.roster_id,newRole);await drainRoster();if(memberRoles.has(oldRole)||!memberRoles.has(newRole))throw Error('Changed role did not clean up old role');
   await setRosterRole(roster1.roster_id,null);await drainRoster();if(memberRoles.has(newRole))throw Error('Cleared role left assignment');
   const label=await rosterApi(`/v2/server/${roleServer}/roster-member-groups`,{name:'Assigned squad'});
   await setRosterRole(roster1.roster_id,oldRole,[{name:'group',type:3,value:label.group.id}]);
   await rosterApi(`/v2/server/${roleServer}/rosters/${roster1.roster_id}/member-label`,{playerTags:[tags[0]],memberGroupId:label.group.id},'PATCH');await drainRoster();if(!memberRoles.has(oldRole))throw Error('Label role not granted');
   await rosterApi(`/v2/server/${roleServer}/rosters/${roster1.roster_id}/member-label`,{playerTags:[tags[0]],memberGroupId:null},'PATCH');await drainRoster();if(memberRoles.has(oldRole))throw Error('Label removal left role');
   await rosterApi(`/v2/server/${roleServer}/rosters/${roster1.roster_id}/member-label`,{playerTags:[tags[0]],memberGroupId:label.group.id},'PATCH');await drainRoster();
   await ruleRequest('POST','',{type:'family',option:'family',role_id:oldRole});
   await rosterApi(`/v2/server/${roleServer}/rosters/${roster1.roster_id}/member-label`,{playerTags:[tags[0]],memberGroupId:null},'PATCH');await drainRoster();
   if(!memberRoles.has(oldRole))throw Error('Ordinary family rule did not preserve shared roster role');
   await db.query('DELETE FROM server_roles WHERE server_id=$1',[roleServer]);
   await rosterApi(`/v2/server/${roleServer}/rosters/${roster1.roster_id}/member-label`,{playerTags:[tags[0]],memberGroupId:label.group.id},'PATCH');await drainRoster();
   const unlinked=await interact(command('link','remove',[{name:'player',type:3,value:tags[0]}]),actor,'32');
   if(!(await db.query('SELECT user_id FROM player_links WHERE tag=$1',[tags[0]])).rows.every(row=>row.user_id!==actor))throw Error('Fixture unlink failed '+text(unlinked));
   await drainRoster();if(memberRoles.has(oldRole))throw Error('Unlinked account retained roster role');
   if(!memberRoles.has(unmanagedRole))throw Error('Roster reconciliation removed unrelated role');
   console.log(JSON.stringify({rosterRoles:'passed',checks:['permission check','grant while game autoeval disabled','shared roster union','last membership removal','changed and cleared role cleanup','label role add/remove','unmanaged role preservation','shared ordinary rule preserved','unlink revokes roster role','old consumer capability gate','unchanged configuration no-op','stale job rejected']}));
   console.log(JSON.stringify({roleRefresh:'passed',checks:['actual signed command/API/SQL flow','null nickname defaults','preview performs no Discord edits','role add/remove preserves unmanaged role','repeat no-op','role hierarchy protection','settings enable enqueues human members','unchanged settings no-op','leave grace retained','disabled settings do not enqueue','scheduled automatic job completion','completed job reopened','new nickname applied automatically','cosmetic settings do not enqueue','created and updated rule application','unchanged rule no-op','deleted rule reconciliation','clan add/remove family role reconciliation','clan abbreviation nickname refresh','category rename/delete reconciliation','unchanged clan/category no-op','category mutation preserves leave grace','tenure independent of game automation','highest earned tenure threshold','shared and unmanaged role preservation','missing join date safe','tenure capability gate','exhausted tenure job reopens after cooldown'],externalDiscordWrites:0,localProviderWrites:roleWrites.length}));
  }finally{
   await db.query('DELETE FROM servers WHERE id=$1',[roleServer]);
   await db.query('DELETE FROM basic_clan WHERE tag=$1',[group]);
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
