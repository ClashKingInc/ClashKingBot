// Actual signed Bot Worker -> API Worker -> local SQL. No production requests.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {generateKeyPairSync,randomBytes,randomUUID,sign} from 'node:crypto';
import {createRequire} from 'node:module';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundleWorker} from './bundle-worker.mjs';
const root=resolve(fileURLToPath(new URL('../../',import.meta.url))),apiRoot=resolve(process.env.CLASHKING_E2E_API_REPO??join(root,'../clashking_api'));
const require=createRequire(join(apiRoot,'package.json')),{Client}=require('pg'),{Miniflare,convertV4MiniflareOptions}=require('miniflare');
const database=process.env.CLASHKING_E2E_DATABASE_URL??'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev';
const url=new URL(database);assert.equal(url.hostname,'127.0.0.1');assert.equal(url.pathname,'/clashking_dev');
const db=new Client({connectionString:database});await db.connect();
const app='999999999999993501',actor='999999999999993502',guild='999999999999993503',other='999999999999993504',absent='999999999999993505',ids=[guild,other,absent];
const {publicKey,privateKey}=generateKeyPairSync('ed25519'),publicHex=publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex');
const keys=Object.fromEntries(['DATA_ENCRYPTION_KEY','JWT_ACCESS_SECRET','JWT_REFRESH_SECRET','API_BOT_TOKEN','AI_USAGE_SECRET','STRIPE_WEBHOOK_SECRET'].map(k=>[k,randomBytes(32).toString('base64url')]));
const port=8806,origin=`http://127.0.0.1:${port}`,generation=randomUUID();let api,bot,owned=false,logs='',activityCalls=0;
const wait=async fn=>{for(let i=0;i<100;i++){if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('Local service timeout '+logs.slice(-1500));};
const payload=(override={})=>({id:'999999999999993506',application_id:app,guild_id:guild,channel_id:'999999999999993507',member:{user:{id:actor,username:'Local'},roles:[]},type:2,data:{name:'meme'},token:'local-only',version:1,...override});
const proof=(value,at=String(Math.floor(Date.now()/1000)))=>{const rawBody=JSON.stringify(value);return {interaction:{rawBody,timestamp:at,signature:sign(null,Buffer.from(at+rawBody),privateKey).toString('hex')}};};
const state=async id=>(await db.query('SELECT last_command_at FROM servers WHERE id=$1',[id])).rows[0].last_command_at;
async function apiRequest(body,status=200,token=keys.API_BOT_TOKEN){const r=await fetch(origin+'/v2/bot/server-activity',{method:'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},body:JSON.stringify(body)});const data=await r.json();assert.equal(r.status,status,JSON.stringify(data));return data;}
try{
 assert.equal((await db.query('SELECT 1 FROM servers WHERE id=ANY($1::text[])',[ids])).rowCount,0);
 assert.equal((await db.query('SELECT 1 FROM discord_cache.gateway_shards WHERE application_id=$1',[app])).rowCount,0);
 await db.query("INSERT INTO servers(id,name,last_command_at) SELECT id,'Activity E2E','2000-01-01'::timestamptz FROM unnest($1::text[]) id",[ids]);owned=true;
 await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
 await db.query("INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete) SELECT id,'{}'::jsonb,$2,0,$3,true,true FROM unnest($1::text[]) id",[[guild,other],app,generation]);
 const env={PATH:process.env.PATH,HOME:process.env.HOME,TMPDIR:process.env.TMPDIR,CLASHKING_PERSISTENT_LOCAL_API:'1',CLASHKING_LOCAL_DATABASE_URL:database,CLASHKING_LOCAL_API_PORT:String(port),CLASHKING_LOCAL_DISCORD_CLIENT_ID:app,CLASHKING_LOCAL_DISCORD_CLIENT_SECRET:'local',CLASHKING_LOCAL_DISCORD_PUBLIC_KEY:publicHex,CLASHKING_LOCAL_ARCHIVE_BRIDGE:'0',CLASHKING_LOCAL_CLASH_PROXY_ORIGIN:'http://127.0.0.1:65534',CLASHKING_LOCAL_STATIC_ASSETS_ROOT:resolve(apiRoot,'../clashking_assets/assets/static_data'),CLASHKING_LOCAL_STORAGE_ROOT:mkdtempSync(join(tmpdir(),'ck-activity-')),...Object.fromEntries(Object.entries(keys).map(([k,v])=>[`CLASHKING_LOCAL_${k}`,v]))};
 api=spawn(process.execPath,['scripts/start-local-rewrite-api.mjs'],{cwd:apiRoot,env,stdio:['ignore','pipe','pipe']});api.stdout.on('data',d=>logs+=d);api.stderr.on('data',d=>logs+=d);
 await wait(async()=>{try{return (await fetch(origin+'/v2/health')).ok&&logs.includes('local_static_assets_seeded');}catch{return false;}});
 await apiRequest(proof(payload()),401,'');
 const tampered=proof(payload());tampered.interaction.rawBody=JSON.stringify(payload({guild_id:other}));await apiRequest(tampered,401);
 await apiRequest(proof(payload({application_id:other})),403);
 await apiRequest(proof(payload(),String(Math.floor(Date.now()/1000)-600)),401);
 await apiRequest(proof(payload({type:3,data:{custom_id:'noop'}})),400);
 assert.equal((await apiRequest(proof(payload({guild_id:absent})))).recorded,false);
 assert.equal((await state(guild)).getUTCFullYear(),2000);
 const bundle=await bundleWorker();
 bot=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{name:'activity-e2e',...bundle,compatibilityDate:'2026-08-22',compatibilityFlags:['nodejs_compat'],bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:origin,CLASHKING_API_TOKEN:keys.API_BOT_TOKEN,DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:'local-only',DISCORD_PUBLIC_KEY:publicHex},outboundService:async request=>{const u=new URL(request.url);assert.equal(u.origin,origin,'External request blocked');if(u.pathname==='/v2/bot/server-activity')activityCalls++;return fetch(request.url,{method:request.method,headers:Object.fromEntries(request.headers),body:await request.arrayBuffer()});}}]}));
 const invoke=async value=>{const p=proof(value).interaction;return bot.dispatchFetch('http://localhost/interactions',{method:'POST',headers:{'X-Signature-Ed25519':p.signature,'X-Signature-Timestamp':p.timestamp},body:p.rawBody});};
 const command=proof(payload());const r=await bot.dispatchFetch('http://localhost/interactions',{method:'POST',headers:{'X-Signature-Ed25519':command.interaction.signature,'X-Signature-Timestamp':command.interaction.timestamp},body:command.interaction.rawBody});assert.equal(r.status,200);assert.match(JSON.stringify(await r.json()),/Make a meme/);
 await wait(async()=>(await state(guild)).getUTCFullYear()>2000);const recorded=await state(guild);assert.equal(recorded.getTime(),Number(command.interaction.timestamp)*1000);assert.equal(activityCalls,1);
 assert.equal((await state(other)).getUTCFullYear(),2000);
 assert.equal((await apiRequest({...command,serverId:other})).recorded,false);assert.equal((await state(other)).getUTCFullYear(),2000);
 await apiRequest(proof(payload(),String(Number(command.interaction.timestamp)-1)));assert.equal((await state(guild)).getTime(),recorded.getTime());
 await invoke(payload({type:4}));await invoke(payload({guild_id:undefined,member:undefined,user:{id:actor}}));await new Promise(r=>setTimeout(r,200));assert.equal(activityCalls,1);
 console.log('PASS actual Bot /meme -> API -> SQL; fresh signed guild only; replay/older proof monotonic; wrong auth/signature/app rejected; absent guild/DM/autocomplete excluded');
}finally{
 if(bot)await bot.dispose();if(api){api.kill('SIGTERM');await new Promise(r=>api.once('exit',r));}
 if(owned){await db.query('DELETE FROM discord_cache.guilds WHERE id=ANY($1::text[])',[ids]);await db.query('DELETE FROM discord_cache.gateway_shards WHERE application_id=$1',[app]);await db.query('DELETE FROM servers WHERE id=ANY($1::text[])',[ids]);}await db.end();
}
