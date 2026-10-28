// Actual API HTTP -> server authorization -> PostgreSQL. Only Discord is a
// loopback provider. No real Discord writes and no shared process restart.
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {randomBytes,randomUUID,createHash,createCipheriv,createHmac} from 'node:crypto';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createRequire} from 'node:module';
const api=resolve(process.env.CLASHKING_E2E_API_REPO??'/Users/matthewanderson/PycharmProjects/clashking_api');
const require=createRequire(join(api,'package.json')),pg=require('pg');
const {SignJWT}=await import(require.resolve('jose'));
const appRequire=createRequire('/Users/matthewanderson/IdeaProjects/ClashKingApp/expo/package.json');
const {Effect:AppEffect,Schema:AppSchema}=await import(appRequire.resolve('effect'));
const {ClanCapitalRankingListResponse}=await import('/Users/matthewanderson/IdeaProjects/ClashKingApp/expo/node_modules/@clashking/clash-contract/dist/effect.js');
const database='postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev';
const db=new pg.Client({connectionString:database});await db.connect();
const actor='999999999999992601',server='999999999999992602',app='999999999999992603',channel='999999999999992604',hook='999999999999992605';
const inviteOwner='999999999999992621',inviteManager='999999999999992622',ordinaryMember='999999999999992623';
const activityTag='#'+[...randomBytes(14)].map(value=>'0289PYLQGRJCUV'[value%13]).join('');
const secret=randomBytes(32).toString('base64url');
const token=await new SignJWT({device:'e2e-device'}).setProtectedHeader({alg:'HS256'}).setSubject(actor).setAudience('clashking-web').setIssuedAt().setExpirationTime('10m').sign(new TextEncoder().encode(secret));
let writes=0,child,seeded=false,logs='',lastResponseHeaders;
const provider=createServer((req,res)=>{res.setHeader('content-type','application/json');const path=new URL(req.url,'http://local').pathname;
 if(req.method!=='GET')writes++;
 if(path==='/v1/locations/global/rankings/capitals')return res.end(JSON.stringify({items:[
  {tag:'#P09LP8CY',name:'Located clan',clanLevel:18,members:50,rank:1,previousRank:2,clanCapitalPoints:6500,location:{id:32000249,name:'United States',isCountry:true,countryCode:'US'}},
  {tag:'#UL0Y9G9Y',name:'No location clan',clanLevel:17,members:49,rank:2,previousRank:1,clanCapitalPoints:6490},
 ]}));
 if(path==='/api/v10/users/@me/guilds')return res.end(JSON.stringify([
  {id:server,name:'Installed',owner:true,permissions:'8'},
  {id:inviteOwner,name:'Installable owner',owner:true,permissions:'0'},
  {id:inviteManager,name:'Installable manager',owner:false,permissions:'32'},
  {id:ordinaryMember,name:'Not manageable',owner:false,permissions:'0'},
 ]));
 if(path===`/api/v10/channels/${channel}`)return res.end(JSON.stringify({id:channel,type:0,guild_id:server}));
 if(path==='/api/v10/users/@me')return res.end(JSON.stringify({id:app}));
 if(path===`/api/v10/guilds/${server}/webhooks`)return res.end(JSON.stringify([{id:hook,type:1,channel_id:channel,user:{id:app}}]));
 if(path===`/api/v10/webhooks/${hook}`)return res.end(JSON.stringify({id:hook,type:1,channel_id:channel}));
 res.statusCode=404;res.end('{}');
});await new Promise(r=>provider.listen(0,'127.0.0.1',r));
const origin='http://127.0.0.1:8824';
const assert=(value,message)=>{if(!value)throw Error(message)};
const request=async(path,method='GET',body,expected=200,credential=token)=>{const r=await fetch(origin+path,{method,headers:{authorization:`Bearer ${credential}`,'content-type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});lastResponseHeaders=r.headers;const value=await r.json();assert(r.status===expected,`${method} ${path}: ${r.status} ${JSON.stringify(value)}`);return value};
try {
 assert(!(await db.query('SELECT 1 FROM auth_users WHERE user_id=$1',[actor])).rowCount,'Synthetic user exists');
 assert(!(await db.query('SELECT 1 FROM servers WHERE id=$1',[server])).rowCount,'Synthetic server exists');
 await db.query("INSERT INTO auth_users(user_id,provider) VALUES($1,'discord')",[actor]);seeded=true;
 await db.query("INSERT INTO auth_refresh_tokens(token_hash,user_id,device_id,expires_at) VALUES($1,$2,'e2e-device',now()+interval '1 day')",[createHash('sha256').update(randomBytes(32)).digest('hex'),actor]);
 await db.query("INSERT INTO servers(id,name,autoboard_limit) VALUES($1,'Farming API E2E',3)",[server]);
 const generation=randomUUID();
 await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
 await db.query('INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,$2,$3,0,$4,true,true,true)',[server,JSON.stringify({owner_id:actor}),app,generation]);
 await db.query("INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,'{}')",[server,actor]);
 const keys=Object.fromEntries(['DATA_ENCRYPTION_KEY','JWT_REFRESH_SECRET','API_BOT_TOKEN','AI_USAGE_SECRET','STRIPE_WEBHOOK_SECRET'].map(k=>['CLASHKING_LOCAL_'+k,randomBytes(32).toString('base64url')]));
 // Encrypt only a synthetic OAuth token using this isolated worker's random key.
 const encryptionKey=Buffer.from(keys.CLASHKING_LOCAL_DATA_ENCRYPTION_KEY,'base64url');
 const stamp=Buffer.alloc(9);stamp[0]=0x80;stamp.writeBigUInt64BE(BigInt(Math.floor(Date.now()/1000)),1);
 const iv=randomBytes(16),cipher=createCipheriv('aes-128-cbc',encryptionKey.subarray(16),iv);
 const ciphertext=Buffer.concat([cipher.update('synthetic-discord-token'),cipher.final()]);
 const signed=Buffer.concat([stamp,iv,ciphertext]);
 const encoded=Buffer.concat([signed,createHmac('sha256',encryptionKey.subarray(0,16)).update(signed).digest()]).toString('base64url');
 const storedToken=Buffer.from(encoded).toString('base64url');
 await db.query("INSERT INTO auth_discord_tokens(user_id,device_id,access_token_ciphertext,refresh_token_ciphertext,expires_at) VALUES($1,'e2e-device',$2,$2,now()+interval '1 day')",[actor,storedToken]);
 child=spawn(process.execPath,['scripts/start-local-rewrite-api.mjs'],{cwd:api,env:{...process.env,...keys,CLASHKING_LOCAL_JWT_ACCESS_SECRET:secret,CLASHKING_PERSISTENT_LOCAL_API:'1',CLASHKING_LOCAL_DATABASE_URL:database,CLASHKING_LOCAL_API_PORT:'8824',CLASHKING_LOCAL_DISCORD_CLIENT_ID:app,CLASHKING_LOCAL_DISCORD_CLIENT_SECRET:'local',CLASHKING_LOCAL_DISCORD_BOT_TOKEN:'local.fake.token',CLASHKING_LOCAL_ARCHIVE_BRIDGE:'0',CLASHKING_LOCAL_CLASH_PROXY_ORIGIN:`http://127.0.0.1:${provider.address().port}`,CLASHKING_LOCAL_DISCORD_TEST_ORIGIN:`http://127.0.0.1:${provider.address().port}`,CLASHKING_LOCAL_STORAGE_ROOT:mkdtempSync(join(tmpdir(),'ck-farming-api-'))},stdio:['ignore','pipe','pipe']});
 child.stdout.on('data',b=>logs+=b);child.stderr.on('data',b=>logs+=b);
 for(let i=0;i<200;i++){try{if((await fetch(origin+'/v2/health')).ok)break}catch{}if(child.exitCode!==null)throw Error(logs.slice(-1800));if(i===199)throw Error('API start timeout '+logs.slice(-1800));await new Promise(r=>setTimeout(r,100))}
 const path=`/v2/server/${server}/autoboards`;
 const directory=await request('/v2/guilds');
 assert(directory.some(g=>g.id===server&&g.has_bot),'Installed server missing from directory');
 assert(directory.some(g=>g.id===inviteOwner&&!g.has_bot),'Owner invite candidate missing');
 assert(directory.some(g=>g.id===inviteManager&&!g.has_bot),'Manage Server invite candidate missing');
 assert(!directory.some(g=>g.id===ordinaryMember),'Ordinary membership exposed as installable');
 console.log('PASS server directory: installed dashboard, owner/manager invite candidates, ordinary member excluded');
 const capital=await request('/proxy/v1/locations/global/rankings/capitals?limit=200');
 const capitalDecoded=await AppEffect.runPromise(AppSchema.decodeUnknownEffect(ClanCapitalRankingListResponse)(capital));
 assert(capitalDecoded.items.length===2&&capitalDecoded.items[1].location===undefined,'Capital ranking dropped a clan without location');
 console.log('PASS local Capital ranking HTTP response -> app wire contract, including missing location');
 const cap=await request(path+'/capabilities');assert(cap.boardTypes.some(b=>b.boardType==='farming'&&b.refreshSeconds.default===30),'Missing farming capability');
 const body={boardType:'farming',rowLimit:5,targetScope:'custom',targets:['#P09LP8CY'],deliveryMode:'refresh',channelId:channel,enabled:false,intervalSeconds:30,farming:{window:'since_start',timezone:'UTC'}};
 await request(path,'POST',{...body,rowLimit:6},400);
 await request(path,'POST',{...body,intervalSeconds:29},400);
 await request(path,'POST',{...body,farming:{window:'since_start',timezone:'not/a/timezone'}},400);
 const created=(await request(path,'POST',body,201)).item;
 assert(created.intervalSeconds===30&&created.farming.countingFrom,'Farming persistence failed');
 await db.query("UPDATE autoboards SET message_id='999999999999992606' WHERE id=$1",[created.id]);
 const changed=(await request(path+'/'+created.id,'PUT',{...body,rowLimit:3,farming:{window:'calendar_month',timezone:'UTC'}})).item;
 assert(changed.messageId==='999999999999992606','Ordinary edit detached message');
 assert(changed.farming.countingFrom===created.farming.countingFrom,'Counting start reset');
 assert((await request(path)).items.length===1,'List mismatch');
 await request(path+'/'+created.id,'DELETE');
 assert(!(await db.query('SELECT 1 FROM autoboard_farming_settings WHERE autoboard_id=$1',[created.id])).rowCount,'Settings not cascaded');
 const donation={boardType:'donations',rowLimit:10,targetScope:'family',targets:[],deliveryMode:'refresh',channelId:channel,enabled:false,intervalMinutes:1};
 const donationBoard=(await request(path,'POST',donation,201)).item;
 assert(donationBoard.boardType==='donations'&&donationBoard.targetScope==='family'&&donationBoard.intervalMinutes===1,'Donation board persistence failed');
 const donationEdited=(await request(path+'/'+donationBoard.id,'PUT',{...donation,rowLimit:30})).item;
 assert(donationEdited.rowLimit===30,'Donation row limit edit failed');
 assert((await request(path)).items.some(item=>item.id===donationBoard.id),'Donation board not listed');
 await request(path+'/'+donationBoard.id,'DELETE');
 await request(`/v2/server/${server}/logs`,'PUT',{log_types:['donation_log'],channel_id:channel,clan_tag:'#P09LP8CY'},400);
 console.log('PASS donation autoboard create/edit/list/delete and retired donation-log setup rejection');
 const initial=await request('/v2/users/me/home-layout');assert(initial.revision===0&&initial.items.length===4,'Initial cards missing');
 const items=[initial.items[2],initial.items[3],initial.items[0],initial.items[1]];
 const saved=await request('/v2/users/me/home-layout','PUT',{revision:0,items});assert(saved.revision===1,'Layout not saved');
 await request('/v2/users/me/home-layout','PUT',{revision:0,items},409);
 await request('/v2/users/me/home-layout','PUT',{revision:1,items:items.slice(0,2)},400);
 await request('/v2/users/me/home-layout','PUT',{revision:1,items:[...items,{id:randomUUID(),kind:'player_farming',entityTag:'#PYLQGRJ',size:'wide'}]},400);
 const roundtrip=await request('/v2/users/me/home-layout');assert(roundtrip.items[1].kind==='activity'&&roundtrip.items[0].kind==='upgrade','Layout order changed');
 await db.query("INSERT INTO battles_farming(player_tag,battle_time,stars,destruction_percentage,duration_seconds,looted_resources) VALUES($1,now()-interval '1 day',3,100,90,$2)",[activityTag,JSON.stringify({gold:1234,elixir:5678,darkElixir:90})]);
 await db.query("INSERT INTO battles_ranked(player_tag,opponent_tag,battle_time,direction,battle_mode,player_town_hall,opponent_town_hall,stars,destruction_percentage,duration_seconds,looted_resources) VALUES($1,'#PYLQGRJ',now()-interval '1 day',1,1,18,18,3,100,90,'{}'),($1,'#PYLQGRJ',now()-interval '2 days',1,2,18,18,2,80,90,'{}'),($1,'#PYLQGRJ',now()-interval '3 days',2,1,18,18,3,100,90,NULL)",[activityTag]);
 await db.query("INSERT INTO player_stat_changes(player_tag,event_time,stat_type,previous_value,current_value,delta) VALUES($1,now()-interval '1 day','donated',0,321,321),($1,now()-interval '31 days','donated',0,999,999),($1,now()-interval '1 day','received',0,42,42)",[activityTag]);
 await db.query("INSERT INTO player_change_history(player_tag,event_time,change_type,item_id,previous_value,current_value) VALUES($1,now()-interval '1 day',1,0,'3','5'),($1,now()-interval '1 day',3,0,'40','41'),($1,now()-interval '1 day',2,0,'0','1'),($1,now()-interval '1 day',12,NULL,'Old name','New name')",[activityTag]);
 const activity=await request('/v2/player/'+encodeURIComponent(activityTag)+'/activity-summary');
 assert(Date.parse(activity.until)-Date.parse(activity.from)===30*86400000,'Activity is not rolling 30 days');
 assert(typeof activity.gold==='string'&&typeof activity.donated==='string'&&Number.isInteger(activity.upgradeLevels),'Activity contract mismatch');
 assert(activity.gold==='1234'&&activity.elixir==='5678'&&activity.darkElixir==='90'&&activity.farmingAttacks===1,'Farming totals differ from stored battles');
 assert(activity.donated==='321'&&activity.received==='42','Donation window is not rolling 30 days');
 assert(activity.upgradeLevels===3,'Upgrades included boosts or missed multi-level gains');
 assert(activity.days.length>=30&&activity.days.length<=31,'Missing rolling-window daily buckets');
 for(const key of ['gold','elixir','darkElixir','donated','received'])assert(activity.days.reduce((n,d)=>n+BigInt(d[key]),0n).toString()===activity[key],`Daily ${key} differs from total`);
 for(const key of ['farmingAttacks','rankedAttacks','legendAttacks','upgradeLevels'])assert(activity.days.reduce((n,d)=>n+d[key],0)===activity[key],`Daily ${key} differs from total`);
 assert(activity.days.some(d=>d.gold==='0')&&activity.days.some(d=>d.gold==='1234'),'Expected empty and observed daily buckets');
 assert(activity.days[0].from===activity.from&&activity.days.at(-1).until===activity.until,'Partial-day boundaries changed the rolling window');
 for(let i=1;i<activity.days.length;i++)assert(activity.days[i-1].until===activity.days[i].from,'Daily buckets have a gap or overlap');
 console.log('PASS daily activity: all nine metric totals reconcile, empty dates retained, exact rolling-window boundaries');
 assert(activity.rankedAttacks===1&&activity.legendAttacks===1,'Attack totals included defensive perspectives');
 await request('/v2/player/not-valid/activity-summary','GET',undefined,400);
 const verifier=randomBytes(32).toString('base64url'),pkceChallenge=createHash('sha256').update(verifier).digest('base64url');
 await request('/v2/server/'+server+'/reminders','POST',{type:'War',clan_tag:'#P09LP8CY',channel_id:channel,time:'1hr'},200);
 const grant=await request(`/v2/server/${server}/dashboard-access-grants`,'POST',{source:'app',pkceChallenge},201);
 const botGrant=await request(`/v2/server/${server}/dashboard-access-grants`,'POST',{source:'bot',userId:actor},201,keys.CLASHKING_LOCAL_API_BOT_TOKEN);
 await request('/v2/auth/server-dashboard/exchange','POST',{code:botGrant.code},401,keys.CLASHKING_LOCAL_API_BOT_TOKEN);
 const botSession=await request('/v2/auth/server-dashboard/exchange','POST',{code:botGrant.code});
 await request(path,'GET',undefined,200,botSession.access_token);
 await request('/v2/auth/server-dashboard/exchange','POST',{code:grant.code,codeVerifier:randomBytes(32).toString('base64url')},401);
 const session=await request('/v2/auth/server-dashboard/exchange','POST',{code:grant.code,codeVerifier:verifier});
 const sessionCookie=lastResponseHeaders.get('set-cookie').split(';')[0];
 const reminders=await request('/v2/server/'+server+'/reminders','GET',undefined,200,session.access_token);
 assert(reminders.war_reminders.length===1&&Array.isArray(reminders.capital_reminders)&&Array.isArray(reminders.clan_games_reminders)&&Array.isArray(reminders.roster_reminders),'Scoped reminders failed to load the saved reminder');
 await request('/v2/auth/server-dashboard/exchange','POST',{code:grant.code,codeVerifier:verifier},401);
 await request(path,'GET',undefined,200,session.access_token);
 await request('/v2/users/me/home-layout','GET',undefined,403,session.access_token);
 await request('/v2/server/999999999999992699/autoboards','GET',undefined,403,session.access_token);
 const refresh=async(cookieValue,requestOrigin='http://localhost:3002')=>fetch(origin+'/v2/auth/server-dashboard/refresh',{method:'POST',headers:{cookie:cookieValue,origin:requestOrigin,'content-type':'application/json'},body:JSON.stringify({serverId:server})});
 assert((await refresh(sessionCookie,'https://untrusted.invalid')).status===403,'Foreign refresh origin accepted');
 const rotated=await refresh(sessionCookie);if(rotated.status!==200){const failure=await rotated.json();throw Error(`Scoped refresh failed ${rotated.status}: ${failure.code} ${failure.message}`);}
 assert((await refresh(sessionCookie)).status===401,'Old scoped refresh cookie replay accepted');
 await db.query("UPDATE discord_cache.guilds SET data=jsonb_set(data,'{owner_id}','\"999999999999992699\"') WHERE id=$1",[server]);
 await request(path,'GET',undefined,403,session.access_token);
 await db.query("UPDATE discord_cache.guilds SET data=jsonb_set(data,'{owner_id}',to_jsonb($2::text)) WHERE id=$1",[server,actor]);
 await db.query("DELETE FROM auth_refresh_tokens WHERE user_id=$1",[actor]);
 await request(path,'GET',undefined,401,session.access_token);
 assert(writes===0,'Unexpected upstream writes');
 console.log(JSON.stringify({checks:['farming create/validate/edit/list/delete','Home preserves original cards','Home order roundtrip','Home revision conflict','Home cannot delete builtins','grant proof rejection','bot grants require recipient user authentication','one-use exchange','scoped own-server access','cross-server denied','private Home denied','refresh origin enforcement','refresh rotation and replay rejection','permission loss','parent device revocation'],realDiscordWrites:0}));
}finally{
 if(child&&child.exitCode===null){child.kill('SIGTERM');await Promise.race([new Promise(r=>child.once('exit',r)),new Promise(r=>setTimeout(r,6000))]);}
 if(seeded){await db.query('DELETE FROM servers WHERE id=$1',[server]);await db.query('DELETE FROM discord_cache.members WHERE guild_id=$1',[server]);await db.query('DELETE FROM discord_cache.guilds WHERE id=$1',[server]);await db.query('DELETE FROM discord_cache.gateway_shards WHERE application_id=$1',[app]);await db.query('DELETE FROM auth_users WHERE user_id=$1',[actor]);}
 for(const table of ['battles_farming','battles_ranked','player_stat_changes','player_change_history'])await db.query('DELETE FROM '+table+' WHERE player_tag=$1',[activityTag]);
 await db.end();await new Promise(r=>provider.close(r));
}
