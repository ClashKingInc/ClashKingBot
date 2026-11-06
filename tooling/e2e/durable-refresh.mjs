// Signed Bot Worker -> real API Worker -> disposable PostgreSQL -> local HTTP Discord provider.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {generateKeyPairSync,randomBytes,randomUUID,sign} from 'node:crypto';
import {createRequire} from 'node:module';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundleWorker} from './bundle-worker.mjs';
const root=resolve(fileURLToPath(new URL('../../',import.meta.url))),apiRoot=resolve(process.env.CLASHKING_E2E_API_REPO);
const require=createRequire(join(apiRoot,'package.json')),{Client}=require('pg'),{Miniflare,convertV4MiniflareOptions}=require('miniflare');
const database=process.env.TEST_DATABASE_URL;assert(database);const url=new URL(database);assert.equal(url.hostname,'127.0.0.1');assert.equal(url.pathname,'/clashking_test');
const db=new Client({connectionString:database});await db.connect();
const app='999999999999994501',actor='999999999999994502',guild='999999999999994503',user='999999999999994504',channel='999999999999994505',requestId='999999999999994506',messageId='999999999999994507';
const top='999999999999994510',add='999999999999994511',remove='999999999999994512',keep='999999999999994513',late='999999999999994514';
const definitions=[{id:guild,name:'@everyone',position:0,permissions:'0'},{id:top,name:'Bot',position:20,permissions:String((1<<28)+(1<<27))},...[add,remove,keep,late].map((id,i)=>({id,name:id,position:i+1,permissions:id===keep?'32':'0'}))];
const members=new Map([actor,user].map(id=>[id,{user:{id,username:'Before'},nick:'Before',roles:[remove,keep]}]));
let api,bot,logs='',expired=false,throttle=true,first429=0,rolePatches=[],messages=[],ackEdits=0,earlyRetries=0;
const provider=createServer(async(req,res)=>{
 let raw='';for await(const chunk of req)raw+=chunk;const body=raw?JSON.parse(raw):undefined;
 const path=new URL(req.url,'http://local').pathname.replace(/^\/api\/v10/,'');res.setHeader('content-type','application/json');
 const send=(data,status=200)=>{res.statusCode=status;res.end(JSON.stringify(data));};
 if(path.startsWith('/v1/players/'))return send({tag:decodeURIComponent(path.split('/').at(-1)),name:'Updated',townHallLevel:16,trophies:5000});
 if(path===`/guilds/${guild}`)return send({id:guild,name:'Local refresh',owner_id:'999999999999994599'});
 if(path===`/guilds/${guild}/roles`)return send(definitions);
 if(path==='/users/@me')return send({id:app,username:'Bot'});
 if(path===`/guilds/${guild}/members/${app}`)return send({user:{id:app,username:'Bot',bot:true},roles:[top]});
 if(path===`/channels/${channel}`)return send({id:channel,guild_id:guild,type:0,name:'refresh'});
 if(path===`/applications/${app}/emojis`)return send({items:[]});
 if(path.startsWith('/webhooks/')){if(expired)return send({message:'Unknown webhook',code:10015},404);if(req.method==='PATCH'){ackEdits++;messages.push(body);}return send({id:messageId,channel_id:channel});}
 if(path===`/channels/${channel}/messages`&&req.method==='POST')throw Error('Refresh must reuse the original interaction message');
 if(path===`/channels/${channel}/messages/${messageId}`&&req.method==='PATCH'){assert.equal(req.headers.authorization,'Bot local-only');assert.deepEqual(body.allowed_mentions,{parse:[]});messages.push(body);return send({id:messageId});}
 const match=new RegExp(`^/guilds/${guild}/members/(\\d+)$`).exec(path);
 if(match&&members.has(match[1])){
  const member=members.get(match[1]);
  if(req.method==='GET'){if(!member.roles.includes(late))member.roles.push(late);return send(member);}
  if(req.method==='PATCH'){
   if(throttle){throttle=false;first429=Date.now();res.setHeader('retry-after','2');res.setHeader('x-ratelimit-bucket','member-edits');return send({retry_after:2,global:false},429);}
   if(Date.now()-first429<2000)earlyRetries++;
   assert(body.roles.includes(keep)&&body.roles.includes(late));assert(body.roles.includes(add)&&!body.roles.includes(remove));assert.equal(body.nick,'Updated');
   rolePatches.push({id:match[1],body});Object.assign(member,{roles:body.roles,nick:body.nick});res.setHeader('x-ratelimit-bucket','member-edits');res.setHeader('x-ratelimit-remaining','0');res.setHeader('x-ratelimit-reset-after','0.05');return send(member);
  }
 }
 send({message:'Unrecognized local provider route',path},404);
});await new Promise(r=>provider.listen(0,'127.0.0.1',r));const providerOrigin=`http://127.0.0.1:${provider.address().port}`;
const {publicKey,privateKey}=generateKeyPairSync('ed25519'),publicHex=publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex');
const keys=Object.fromEntries(['DATA_ENCRYPTION_KEY','JWT_ACCESS_SECRET','JWT_REFRESH_SECRET','API_BOT_TOKEN','AI_USAGE_SECRET','STRIPE_WEBHOOK_SECRET'].map(k=>[k,randomBytes(32).toString('base64url')]));
const port=8816,origin=`http://127.0.0.1:${port}`,generation=randomUUID();
const wait=async(fn,label)=>{for(let i=0;i<150;i++){if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error(label+' '+logs.slice(-2500));};
const request=async(path,body)=>{const r=await fetch(origin+path,{method:body?'POST':'GET',headers:{authorization:`Bearer ${keys.API_BOT_TOKEN}`,'content-type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});const json=await r.json();assert.equal(r.status,200,JSON.stringify(json));return json;};
let bundle;
async function startBot(){return new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{name:'durable-refresh',...bundle,compatibilityDate:'2026-09-02',compatibilityFlags:['nodejs_compat'],bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:origin,CLASHKING_API_TOKEN:keys.API_BOT_TOKEN,DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:'local-only',DISCORD_PUBLIC_KEY:publicHex},outboundService:async req=>{
 const u=new URL(req.url);assert([new URL(origin).host,'discord.com'].includes(u.host),'External request blocked');const destination=u.host==='discord.com'?providerOrigin+u.pathname+u.search:req.url;
 return fetch(destination,{method:req.method,headers:Object.fromEntries(req.headers),...(!['GET','HEAD'].includes(req.method)?{body:await req.arrayBuffer()}:{})});
 }}]}));}
try{
 await db.query("INSERT INTO servers(id,name,flair_non_family,change_nickname,non_family_nickname_rule) VALUES($1,'Refresh E2E',true,true,'{player_name}')",[guild]);
 await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
 await db.query("INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,$2,$3,0,$4,true,true,true)",[guild,{owner_id:'999999999999994599'},app,generation]);
 for(const member of members.values())await db.query('INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,$3)',[guild,member.user.id,member]);
 for(const role of definitions)await db.query('INSERT INTO discord_cache.roles(guild_id,id,data) VALUES($1,$2,$3)',[guild,role.id,role]);
 await db.query("INSERT INTO server_roles(server_id,type,option,role_id) VALUES($1,'townhall','16',$2),($1,'townhall','15',$3)",[guild,add,remove]);
 for(const [i,id] of [actor,user].entries())await db.query("INSERT INTO player_links(tag,user_id,source) VALUES($1,$2,'discord')",['#PYLQGR'+(i?'J':'U'),id]);
 const env={PATH:process.env.PATH,HOME:process.env.HOME,TMPDIR:process.env.TMPDIR,CLASHKING_DISPOSABLE_TIMESCALE:'1',TEST_DATABASE_URL:database,CLASHKING_LOCAL_DATABASE_URL:database,CLASHKING_LOCAL_API_PORT:String(port),CLASHKING_LOCAL_DISCORD_CLIENT_ID:app,CLASHKING_LOCAL_DISCORD_BOT_TOKEN:'local-only',CLASHKING_LOCAL_DISCORD_TEST_ORIGIN:providerOrigin,CLASHKING_LOCAL_DISCORD_CLIENT_SECRET:'local',CLASHKING_LOCAL_DISCORD_PUBLIC_KEY:publicHex,CLASHKING_LOCAL_ARCHIVE_BRIDGE:'0',CLASHKING_LOCAL_CLASH_PROXY_ORIGIN:providerOrigin,CLASHKING_LOCAL_STATIC_ASSETS_ROOT:process.env.CLASHKING_E2E_STATIC_ASSETS_ROOT,CLASHKING_LOCAL_STORAGE_ROOT:mkdtempSync(join(tmpdir(),'ck-refresh-')),...Object.fromEntries(Object.entries(keys).map(([k,v])=>[`CLASHKING_E2E_${k}`,v]))};
 api=spawn(process.execPath,['scripts/start-local-rewrite-api.mjs'],{cwd:apiRoot,env,stdio:['ignore','pipe','pipe']});api.stdout.on('data',d=>logs+=d);api.stderr.on('data',d=>logs+=d);
 await wait(async()=>{try{return (await fetch(origin+'/v2/health')).ok&&logs.includes('local_static_assets_seeded');}catch{return false;}},'API readiness');
 bundle=await bundleWorker();bot=await startBot();
 const value={id:requestId,application_id:app,guild_id:guild,channel_id:channel,member:members.get(actor),type:2,data:{name:'refresh',options:[{name:'role_or_user',type:9,value:guild}],resolved:{roles:{[guild]:definitions[0]}}},token:'local-expiring-token',version:1};
 const raw=JSON.stringify(value),timestamp=String(Math.floor(Date.now()/1000)),signature=sign(null,Buffer.from(timestamp+raw),privateKey).toString('hex'),started=Date.now();
 const response=await bot.dispatchFetch('http://local/interactions',{method:'POST',headers:{'x-signature-ed25519':signature,'x-signature-timestamp':timestamp},body:raw});assert.equal((await response.json()).type,5);assert(Date.now()-started<3000,'Immediate deferred acknowledgement');
 await wait(async()=>Boolean((await db.query('SELECT message_id FROM role_refresh_requests WHERE id=$1',[requestId])).rows[0]?.message_id),'stored original response');
 await wait(async()=>ackEdits>0,'initial progress response');
 assert.equal(rolePatches.length,0,'HTTP invocation does not run member work');assert.match(JSON.stringify(messages[0]),/Role Refresh In Progress/);
 assert.equal(Number((await db.query('SELECT count(*) FROM role_refresh_jobs WHERE request_id=$1',[requestId])).rows[0].count),2);
 await request(`/v2/bot/role-refresh/${guild}/manual-start`,{actorId:actor,requestId,channelId:channel,messageId,targetId:guild,targetKind:'role',preview:false,categories:['family','clan','leadership','townhall','builderhall','league','builder_league','category','nicknames','tenure','roster'],treatment:'both'});
 assert.equal(Number((await db.query('SELECT count(*) FROM role_refresh_jobs WHERE request_id=$1',[requestId])).rows[0].count),2,'Idempotent invocation');
 await wait(async()=>ackEdits>0,'initial response');await bot.dispose();expired=true;bot=await startBot();
 await db.query("UPDATE role_refresh_requests SET created_at=now()-interval '20 minutes',published_at=NULL WHERE id=$1",[requestId]);
 await db.query("INSERT INTO role_refresh_jobs(id,server_id,user_id,categories,due_at) VALUES('tenure:paused',$1,$2,ARRAY['tenure'],now()-interval '2 days')",[guild,actor]);
 await db.query("INSERT INTO role_refresh_jobs(id,server_id,user_id,due_at) SELECT 'older-auto-'||i,$1,(999999999999995000::bigint+i)::text,now()-interval '1 day' FROM generate_series(1,40)i",[guild]);
 const before=ackEdits;await (await bot.getWorker()).scheduled({cron:'* * * * *'});
 await wait(async()=>first429>0,'provider throttle');
 await new Promise(r=>setTimeout(r,3500));
 await db.query('UPDATE discord_cache.gateway_shards SET heartbeat_at=now() WHERE application_id=$1',[app]);
 await db.query('UPDATE role_refresh_requests SET published_at=NULL WHERE id=$1',[requestId]);
 await (await bot.getWorker()).scheduled({cron:'* * * * *'});
 await wait(async()=>Number((await db.query('SELECT count(*) FROM role_refresh_jobs WHERE request_id=$1 AND completed_at IS NOT NULL',[requestId])).rows[0].count)===2,'member completion');
 await db.query('UPDATE role_refresh_requests SET published_at=NULL WHERE id=$1',[requestId]);await (await bot.getWorker()).scheduled({cron:'* * * * *'});
 await wait(async()=>Boolean((await db.query('SELECT published_complete FROM role_refresh_requests WHERE id=$1',[requestId])).rows[0]?.published_complete),'final progress');
 assert.equal(ackEdits,before,'Expired interaction token never used by continued work');assert.equal(earlyRetries,0);assert.equal(rolePatches.length,2,'One successful combined member PATCH per member');assert.match(JSON.stringify(messages.at(-1)),/Refresh Complete/);
 assert.equal(Number((await db.query('SELECT max(attempts) AS attempts FROM role_refresh_jobs WHERE request_id=$1',[requestId])).rows[0].attempts),1,'Rate limiting does not spend a failure attempt');
 assert.match(JSON.stringify(messages.at(-1)),/Updated/);assert(!JSON.stringify(messages.at(-1)).includes('None'));
 const repeatId='999999999999994520';
 await request(`/v2/bot/role-refresh/${guild}/manual-start`,{actorId:actor,requestId:repeatId,channelId:channel,messageId,targetId:guild,targetKind:'role',preview:false,categories:['family','clan','leadership','townhall','builderhall','league','builder_league','category','nicknames','tenure','roster'],treatment:'both'});
 await db.query('UPDATE discord_cache.gateway_shards SET heartbeat_at=now() WHERE application_id=$1',[app]);
 await (await bot.getWorker()).scheduled({cron:'* * * * *'});
 await wait(async()=>Number((await db.query('SELECT count(*) FROM role_refresh_jobs WHERE request_id=$1 AND completed_at IS NOT NULL',[repeatId])).rows[0].count)===2,'unchanged members complete');
 await db.query('UPDATE role_refresh_requests SET published_at=NULL WHERE id=$1',[repeatId]);await (await bot.getWorker()).scheduled({cron:'* * * * *'});
 await wait(async()=>Boolean((await db.query('SELECT published_complete FROM role_refresh_requests WHERE id=$1',[repeatId])).rows[0]?.published_complete),'unchanged final progress');
 assert.equal(rolePatches.length,2,'Unchanged members perform no member PATCH');assert.match(JSON.stringify(messages.at(-1)),/No changes needed/);assert(!JSON.stringify(messages.at(-1)).includes('<@'),'Unchanged people omitted');
 const revokedId='999999999999994521';
 await request(`/v2/bot/role-refresh/${guild}/manual-start`,{actorId:actor,requestId:revokedId,channelId:channel,messageId,targetId:guild,targetKind:'role',preview:false,categories:['townhall','nicknames'],treatment:'both'});
 for(const member of members.values()){member.roles=[remove,keep,late];member.nick='Before';}
 await db.query("UPDATE discord_cache.roles SET data=jsonb_set(data,'{permissions}','\"0\"'::jsonb) WHERE guild_id=$1 AND id=$2",[guild,keep]);
 await (await bot.getWorker()).scheduled({cron:'* * * * *'});
 await wait(async()=>Number((await db.query('SELECT sum(attempts) AS attempts FROM role_refresh_jobs WHERE request_id=$1',[revokedId])).rows[0].attempts)>=2,'revoked actor checked');
 assert.equal(rolePatches.length,2,'Revoked manager cannot apply queued changes');
 await db.query('UPDATE role_refresh_jobs SET attempts=12 WHERE request_id=$1',[revokedId]);
 await db.query('UPDATE role_refresh_requests SET published_at=NULL WHERE id=$1',[revokedId]);await (await bot.getWorker()).scheduled({cron:'* * * * *'});
 await wait(async()=>Boolean((await db.query('SELECT published_complete FROM role_refresh_requests WHERE id=$1',[revokedId])).rows[0]?.published_complete),'failure final progress');
 assert.match(JSON.stringify(messages.at(-1)),/Refresh Incomplete/);assert.match(JSON.stringify(messages.at(-1)),/Before/);
 const pausedTenure=(await db.query("SELECT attempts,completed_at FROM role_refresh_jobs WHERE id='tenure:paused'")).rows[0];assert.equal(pausedTenure.attempts,0);assert.equal(pausedTenure.completed_at,null);
 console.log('PASS real signed Bot/API/SQL: immediate defer, durable two-member request, idempotent enqueue, single original progress message, older automatic backlog bypassed, restart after token expiry, provider retry-after, combined roles+nickname PATCH preserving unrelated roles, final progress publication');
}catch(error){console.error(logs.slice(-6000));throw error;}finally{
 if(bot)await bot.dispose();if(api&&api.exitCode===null){api.kill('SIGTERM');await new Promise(r=>api.once('exit',r));}await new Promise(r=>provider.close(r));await db.end();
}
