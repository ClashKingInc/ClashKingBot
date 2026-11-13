// Real Bot Worker -> API Worker -> disposable Timescale, with a local Discord provider.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { spawn, execFileSync } from 'node:child_process';
import { randomBytes, randomUUID } from 'node:crypto';
import { copyFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { bundleWorker } from './bundle-worker.mjs';

assert.equal(process.env.CLASHKING_DISPOSABLE_TIMESCALE, '1');
const dsn = new URL(process.env.TEST_DATABASE_URL);
assert.equal(dsn.hostname, '127.0.0.1');
assert.equal(dsn.pathname, '/clashking_test');
assert(process.env.CLASHKING_LAB_MIGRATION_PATH);
const migrationDir = mkdtempSync(join(tmpdir(), 'ck-lab-migration-'));
// The retained API fixture skips these independent migrations, but the
// current settings route and refresh worker require both of them.
copyFileSync(join(dirname(process.env.CLASHKING_LAB_MIGRATION_PATH), '066_manual_refresh_requests.sql'), join(migrationDir, '066_manual_refresh_requests.sql'));
copyFileSync(join(dirname(process.env.CLASHKING_LAB_MIGRATION_PATH), '074_countdown_disable.sql'), join(migrationDir, '074_countdown_disable.sql'));
copyFileSync(process.env.CLASHKING_LAB_MIGRATION_PATH, join(migrationDir, '082_server_lab_tenure.sql'));
execFileSync('goose', ['-allow-missing', '-dir', migrationDir, 'postgres', dsn.href, 'up'], { stdio: 'pipe' });
const apiRoot = resolve(process.env.CLASHKING_E2E_API_REPO);
const require = createRequire(join(apiRoot, 'package.json'));
const { Client } = require('pg');
const { Miniflare, convertV4MiniflareOptions } = require('miniflare');
const { SignJWT } = await import(require.resolve('jose'));
const db = new Client({ connectionString: dsn.href });
await db.connect();
const app='999999999999993001', guild='999999999999993002', manager='999999999999993003', viewer='999999999999993004', rolesOnly='999999999999993005';
const top='999999999999993010', managerRole='999999999999993011', viewRole='999999999999993012', rolesRole='999999999999993013', tenureRole='999999999999993014', otherRole='999999999999993015';
const joined = new Date(); joined.setUTCFullYear(joined.getUTCFullYear()-2); joined.setUTCDate(joined.getUTCDate()-1);
const roleDefinitions = [
  { id:guild, name:'@everyone', position:0, permissions:'0' },
  { id:top, name:'Bot', position:20, permissions:String(1<<28) },
  ...[managerRole,viewRole,rolesRole,tenureRole,otherRole].map((id,i)=>({ id, name:id, position:i+1, permissions:'0' })),
];
const members = new Map([
  [manager, { user:{id:manager,username:'Manager'}, roles:[managerRole,otherRole], joined_at:joined.toISOString() }],
  [viewer, { user:{id:viewer,username:'Viewer'}, roles:[viewRole] }],
  [rolesOnly, { user:{id:rolesOnly,username:'Roles only'}, roles:[rolesRole] }],
]);
const patches=[];
const provider=createServer(async(req,res)=>{
  let raw=''; for await (const chunk of req) raw+=chunk;
  const path=new URL(req.url,'http://local').pathname.replace(/^\/api\/v10/,'');
  const send=(data,status=200)=>{res.statusCode=status;res.setHeader('content-type','application/json');res.end(JSON.stringify(data));};
  if(path===`/guilds/${guild}`)return send({id:guild,name:'Lab E2E',owner_id:'999999999999993099'});
  if(path===`/guilds/${guild}/roles`)return send(roleDefinitions);
  if(path==='/users/@me')return send({id:app,username:'Bot'});
  if(path===`/guilds/${guild}/members/${app}`)return send({user:{id:app,bot:true},roles:[top]});
  const match=new RegExp(`^/guilds/${guild}/members/(\\d+)$`).exec(path);
  if(match && members.has(match[1])){
    const member=members.get(match[1]);
    if(req.method==='GET')return send(member);
    if(req.method==='PATCH'){
      const body=JSON.parse(raw);if(body.roles)member.roles=body.roles;
      patches.push({id:match[1],body});
      await db.query('UPDATE discord_cache.members SET data=$3 WHERE guild_id=$1 AND user_id=$2',[guild,match[1],member]);
      return send(member);
    }
  }
  return send({message:'Unknown local provider path',path},404);
});
await new Promise(r=>provider.listen(0,'127.0.0.1',r));
const providerOrigin=`http://127.0.0.1:${provider.address().port}`;
const port=Number(process.env.CLASHKING_E2E_API_PORT ?? 8838), origin=`http://127.0.0.1:${port}`;
const keys=Object.fromEntries(['DATA_ENCRYPTION_KEY','JWT_ACCESS_SECRET','JWT_REFRESH_SECRET','API_BOT_TOKEN','AI_USAGE_SECRET','STRIPE_WEBHOOK_SECRET'].map(k=>[k,randomBytes(32).toString('base64url')]));
const token=async id=>new SignJWT({}).setProtectedHeader({alg:'HS256'}).setSubject(id).setAudience('clashking-web').setIssuedAt().setExpirationTime('10m').sign(new TextEncoder().encode(keys.JWT_ACCESS_SECRET));
let api,bot,logs='';
const wait=async(fn,label)=>{for(let i=0;i<200;i++){if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error(label+' '+logs.slice(-3000));};
const call=async(path,{method='GET',body,credential=keys.API_BOT_TOKEN,status=200}={})=>{
  const response=await fetch(origin+path,{method,headers:{authorization:`Bearer ${credential}`,'content-type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const data=await response.json();assert.equal(response.status,status,JSON.stringify(data));return data;
};
try{
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Lab E2E')",[guild]);
  for(const id of members.keys())await db.query("INSERT INTO auth_users(user_id,provider) VALUES($1,'discord')",[id]);
  const generation=randomUUID();
  await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
  await db.query('INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,$2,$3,0,$4,true,true,true)',[guild,{owner_id:'999999999999993099'},app,generation]);
  for(const [id,member] of members)await db.query('INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,$3)',[guild,id,member]);
  for(const role of roleDefinitions)await db.query('INSERT INTO discord_cache.roles(guild_id,id,data) VALUES($1,$2,$3)',[guild,role.id,role]);
  for(const [role,section,level] of [[managerRole,'settings','manage'],[managerRole,'roles','manage'],[managerRole,'tickets','manage'],[viewRole,'settings','view'],[rolesRole,'roles','manage']])await db.query('INSERT INTO dashboard_role_grants(server_id,role_id,section,access_level) VALUES($1,$2,$3,$4)',[guild,role,section,level]);
  const env={PATH:process.env.PATH,HOME:process.env.HOME,TMPDIR:process.env.TMPDIR,CLASHKING_DISPOSABLE_TIMESCALE:'1',TEST_DATABASE_URL:dsn.href,CLASHKING_LOCAL_DATABASE_URL:dsn.href,CLASHKING_LOCAL_API_PORT:String(port),CLASHKING_LOCAL_DISCORD_CLIENT_ID:app,CLASHKING_LOCAL_DISCORD_BOT_TOKEN:'local-only',CLASHKING_LOCAL_DISCORD_TEST_ORIGIN:providerOrigin,CLASHKING_LOCAL_DISCORD_CLIENT_SECRET:'local',CLASHKING_LOCAL_DISCORD_PUBLIC_KEY:'0'.repeat(64),CLASHKING_LOCAL_ARCHIVE_BRIDGE:'0',CLASHKING_LOCAL_CLASH_PROXY_ORIGIN:providerOrigin,CLASHKING_LOCAL_STATIC_ASSETS_ROOT:process.env.CLASHKING_E2E_STATIC_ASSETS_ROOT,CLASHKING_LOCAL_STORAGE_ROOT:mkdtempSync(join(tmpdir(),'ck-lab-storage-')),...Object.fromEntries(Object.entries(keys).map(([k,v])=>[`CLASHKING_E2E_${k}`,v]))};
  api=spawn(process.execPath,['scripts/start-local-rewrite-api.mjs'],{cwd:apiRoot,env,stdio:['ignore','pipe','pipe']});api.stdout.on('data',d=>logs+=d);api.stderr.on('data',d=>logs+=d);
  await wait(async()=>{try{return (await fetch(origin+'/v2/health')).ok&&logs.includes('local_static_assets_seeded');}catch{return false;}},'API readiness');
  const managerToken=await token(manager),viewerToken=await token(viewer),rolesToken=await token(rolesOnly);
  const settingsPath=`/v2/server/${guild}/settings`, rulesPath=`/v2/server/${guild}/server-roles`;
  if(process.env.CLASHKING_E2E_DASHBOARD_REPO){
    const dashboard=resolve(process.env.CLASHKING_E2E_DASHBOARD_REPO),output=join(tmpdir(),`ck-lab-client-${randomUUID()}.mjs`);
    await require('esbuild').build({entryPoints:[join(dashboard,'lib/api/clients/server-client.ts')],outfile:output,bundle:true,platform:'node',format:'esm',alias:{'@':dashboard},define:{'import.meta.env':JSON.stringify({DEV:true,VITE_CLASHKING_API_ORIGIN:origin})},logLevel:'silent'});
    const {ServerClient}=await import(pathToFileURL(output).href), client=new ServerClient({baseUrl:origin,accessToken:managerToken});
    const initial=await client.getSettings(guild);assert.equal(initial.data?.lab_tenure_roles_enabled,false,JSON.stringify(initial));
    assert(!(await client.updateSettings(guild,{lab_tenure_roles_enabled:true})).error,'Dashboard client enables Lab');
    assert.equal((await client.getSettings(guild)).data?.lab_tenure_roles_enabled,true,'Dashboard client decodes saved choice');
    assert(!(await client.updateSettings(guild,{lab_tenure_roles_enabled:false})).error,'Dashboard client disables Lab');
    client.setAccessToken(viewerToken);assert.equal((await client.updateSettings(guild,{lab_tenure_roles_enabled:true})).status,403,'Dashboard view-only cannot enable Lab');
    const ticketOutput=join(tmpdir(),`ck-ticket-client-${randomUUID()}.mjs`);
    await require('esbuild').build({entryPoints:[join(dashboard,'lib/api/clients/tickets-client.ts')],outfile:ticketOutput,bundle:true,platform:'node',format:'esm',alias:{'@':dashboard},define:{'import.meta.env':JSON.stringify({DEV:true,VITE_CLASHKING_API_ORIGIN:origin})},logLevel:'silent'});
    const {TicketsClient}=await import(pathToFileURL(ticketOutput).href), tickets=new TicketsClient({baseUrl:origin,accessToken:managerToken});
    assert(!(await tickets.createPanel(guild,{name:'Client E2E'})).error,'Dashboard client creates ticket panel');
    assert(!(await tickets.createButton(guild,'Client E2E',{label:'Apply',style:1})).error,'Dashboard client creates button');
    const panel=(await tickets.getPanels(guild)).data.items.find(item=>item.name==='Client E2E');
    const customId=panel.components[0].custom_id,initialSettings=panel.button_settings[customId];
    const questions=Array.from({length:6},(_,i)=>({id:`migrated-${i}`,label:i===0?'A migrated question longer than forty-five characters remains saved':`Question ${i}`,type:'text',required:true,options:[],order:i}));
    const firstSave=await tickets.updateButtonSettings(guild,'Client E2E',customId,{...initialSettings,application_questions:questions,roles_to_add:[otherRole]});
    assert(!firstSave.error,JSON.stringify(firstSave));
    const saved=(await tickets.getPanels(guild)).data.items.find(item=>item.name==='Client E2E').button_settings[customId];
    assert.deepEqual(saved.application_questions,questions,'Dashboard client retains multi-page and long migrated questions');
    const secondSave=await tickets.updateButtonSettings(guild,'Client E2E',customId,{...saved,roles_to_remove:[tenureRole]});
    assert(!secondSave.error,JSON.stringify(secondSave));
    const reread=(await tickets.getPanels(guild)).data.items.find(item=>item.name==='Client E2E').button_settings[customId];
    assert.deepEqual(reread.application_questions,questions);assert.deepEqual(reread.roles_to_add,[otherRole]);assert.deepEqual(reread.roles_to_remove,[tenureRole]);
  }
  assert.equal((await call(settingsPath,{credential:managerToken})).lab_tenure_roles_enabled,false,'new servers default off');
  const toggle=(credential,value,status=200)=>call(settingsPath,{method:'PATCH',credential,body:{lab_tenure_roles_enabled:value},status});
  const create=(credential,status=201)=>call(rulesPath,{method:'POST',credential,body:{type:'status',option:'12',role_id:tenureRole},status});
  await toggle(viewerToken,true,403); await toggle(rolesToken,true,403); await create(managerToken,403);
  await toggle(managerToken,true); assert.equal((await call(settingsPath,{credential:managerToken})).lab_tenure_roles_enabled,true);
  const tenure=(await create(rolesToken)).role;
  const bundle=await bundleWorker();
  bot=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{name:'lab-tenure',...bundle,compatibilityDate:'2026-09-02',compatibilityFlags:['nodejs_compat'],bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:origin,CLASHKING_API_TOKEN:keys.API_BOT_TOKEN,DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:'local-only',DISCORD_PUBLIC_KEY:'0'.repeat(64)},outboundService:async req=>{
    const u=new URL(req.url);assert([new URL(origin).host,'discord.com'].includes(u.host),'External request blocked');
    return fetch(u.host==='discord.com'?providerOrigin+u.pathname+u.search:req.url,{method:req.method,headers:Object.fromEntries(req.headers),...(!['GET','HEAD'].includes(req.method)?{body:await req.arrayBuffer()}:{})});
  }}]}));
  await (await bot.getWorker()).scheduled({cron:'* * * * *'});
  await wait(async()=>members.get(manager).roles.includes(tenureRole),'enabled tenure assignment');
  assert(members.get(manager).roles.includes(otherRole),'unmanaged role preserved');
  // An already claimed plan is fenced if the setting changes before validation.
  await db.query("INSERT INTO role_refresh_jobs(id,server_id,user_id,categories) VALUES('lab-fence',$1,$2,ARRAY['tenure'])",[guild,manager]);
  const claimed=(await call('/v2/bot/role-refresh/claim',{method:'POST',body:{serverId:guild,includeTenure:true,supportsLabTenure:true}})).jobs.find(job=>job.id==='lab-fence');
  assert(claimed,'capable worker claims tenure');
  const validate=()=>call('/v2/bot/role-refresh/validate',{method:'POST',body:{id:claimed.id,token:claimed.token,accountTags:[],tenureRolesEnabled:true}});
  assert.equal((await validate()).valid,true); await toggle(managerToken,false); assert.equal((await validate()).valid,false,'disable fences an existing plan');
  await call(`${rulesPath}/${tenure.id}`,{method:'DELETE',credential:rolesToken,status:403});
  assert.equal(Number((await db.query("SELECT count(*) AS n FROM server_roles WHERE server_id=$1 AND type='status'",[guild])).rows[0].n),1,'saved rules retained');
  assert(members.get(manager).roles.includes(tenureRole),'disable did not remove assigned role');
  const legacy=await call('/v2/bot/role-refresh/claim',{method:'POST',body:{serverId:guild,includeTenure:true}});
  assert.equal(legacy.jobs.length,0,'old worker cannot claim while saved tenure rules exist');
  // Another rule may share this ID. A disabled experiment must still protect the
  // current assignment when a different category would otherwise remove it.
  await db.query("INSERT INTO server_roles(server_id,type,option,role_id) VALUES($1,'townhall','16',$2)",[guild,tenureRole]);
  await db.query('UPDATE servers SET autoeval_enabled=true WHERE id=$1',[guild]);
  await db.query("DELETE FROM role_refresh_leases WHERE job_id='lab-fence'");
  await db.query("UPDATE role_refresh_jobs SET completed_at=now() WHERE id='lab-fence'");
  await db.query("INSERT INTO role_refresh_jobs(id,server_id,user_id,categories) VALUES('lab-shared',$1,$2,ARRAY['townhall','tenure'])",[guild,manager]);
  const before=patches.length;
  await (await bot.getWorker()).scheduled({cron:'* * * * *'});
  await wait(async()=>Boolean((await db.query("SELECT completed_at FROM role_refresh_jobs WHERE id='lab-shared'")).rows[0]?.completed_at),'disabled shared role job');
  assert(members.get(manager).roles.includes(tenureRole),'disabled shared role remains assigned');
  assert.equal(patches.length,before,'disabled shared role did not trigger a Discord edit');
  console.log('PASS Lab: Goose migration and default-off, manager/viewer/role-only authorization, Dashboard client settings/ticket round trips, multi-page question preservation, rule gate, enabled Bot/API/SQL assignment, stale plan fence, old consumer gate, disable preserves rules and shared assigned role');
}catch(error){
  console.error(logs.slice(-8000));
  throw error;
}finally{
  if(bot)await bot.dispose();if(api&&api.exitCode===null){api.kill('SIGTERM');await new Promise(r=>api.once('exit',r));}
  await new Promise(r=>provider.close(r));await db.end();
}
