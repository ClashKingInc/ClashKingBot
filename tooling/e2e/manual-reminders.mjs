// Real API -> PostgreSQL NOTIFY -> reminders process -> Valkey -> Discord delivery.
// Only the external Clash/Discord HTTP boundary is supplied by loopback fixtures.
import { createServer } from 'node:http';
import { randomBytes, randomUUID } from 'node:crypto';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { connect } from 'node:net';
import { spawn, execFileSync } from 'node:child_process';

const botRoot = resolve(fileURLToPath(new URL('../../', import.meta.url)));
const apiRoot = resolve(process.env.CLASHKING_E2E_API_REPO ?? join(botRoot, '../clashking_api'));
const trackingRoot = resolve(process.env.CLASHKING_E2E_TRACKING_REPO ?? join(botRoot, '../clashking_tracking'));
const require = createRequire(join(apiRoot, 'package.json'));
const { Client } = require('pg');
const { SignJWT } = await import(require.resolve('jose'));
if (process.env.CLASHKING_DISPOSABLE_TIMESCALE !== '1') throw Error('Run through the real disposable Timescale migration harness');
const sourceURL = new URL(process.env.TEST_DATABASE_URL ?? '');
if (sourceURL.hostname !== '127.0.0.1' || sourceURL.pathname !== '/clashking_test') throw Error('Only the owned disposable database is allowed');
const setup = new Client({ connectionString: sourceURL.href });
await setup.connect();
try {
  // The real API launcher deliberately accepts only this owned local identity.
  await setup.query("CREATE ROLE clashking_local SUPERUSER LOGIN PASSWORD 'clashking_local'");
  await setup.query('CREATE DATABASE clashking_dev WITH TEMPLATE clashking_test OWNER clashking_local');
} finally { await setup.end(); }
const databaseURL = new URL(sourceURL.href);
databaseURL.username = databaseURL.password = 'clashking_local';
databaseURL.pathname = '/clashking_dev';
const db = new Client({ connectionString: databaseURL.href });
await db.connect();
const directory = mkdtempSync(join(tmpdir(), 'ck-manual-reminder-e2e-'));
const port = Number(process.env.CLASHKING_E2E_API_PORT ?? 8803);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw Error('Invalid local API port');
const occupied = await new Promise(resolve => {
  const socket = connect({ host: '127.0.0.1', port });
  socket.once('connect', () => { socket.destroy(); resolve(true); });
  socket.once('error', () => resolve(false));
});
if (occupied) throw Error('Isolated API port is occupied');
const app = '999999999999994501', actor = '999999999999994502';
const guild = '999999999999994503', otherGuild = '999999999999994504', channel = '999999999999994505';
const clanTag = '#PYLQRRJC', enemy = '#PYLQRRJY';
const tags = ['#PYLQRRJP', '#PYLQRRJQ', '#PYLQRRJG', '#PYLQRRJR'];
const names = ['Eligible Attacker', 'Finished Attacker', 'Wrong Townhall', 'Wrong Role'];
const keys = Object.fromEntries(['DATA_ENCRYPTION_KEY','JWT_ACCESS_SECRET','JWT_REFRESH_SECRET','API_BOT_TOKEN','AI_USAGE_SECRET','STRIPE_WEBHOOK_SECRET'].map(key => [key, randomBytes(32).toString('base64url')]));
const stream = 'ck:e2e:manual:' + randomUUID();
const valkeyPort = Number(process.env.CLASHKING_E2E_VALKEY_PORT ?? 6379);
const valkeyPassword = process.env.CLASHKING_E2E_VALKEY_PASSWORD ?? '';
if (!Number.isInteger(valkeyPort) || valkeyPort < 1 || valkeyPort > 65535) throw Error('Invalid local Valkey port');
async function redis(...args) {
  return new Promise((resolve, reject) => {
    const socket = connect({ host:'127.0.0.1', port:valkeyPort }); let result = '';
    socket.on('error', reject);
    socket.on('connect', () => {
      const commands = valkeyPassword ? [['AUTH',valkeyPassword],args] : [args];
      socket.write(Buffer.concat(commands.flatMap(a => [Buffer.from('*'+a.length+'\r\n'),...a.flatMap(x => { const data=Buffer.from(String(x));return [Buffer.from('$'+data.length+'\r\n'),data,Buffer.from('\r\n')]; })])));
    });
    socket.on('data', data => {
      result += data;
      const lines=result.split('\r\n').filter(Boolean);
      if(lines.some(line=>line.startsWith('-'))){socket.destroy();reject(Error('Local Valkey request failed'));return;}
      if(lines.filter(line=>/^[+:$]/.test(line)).length >= (valkeyPassword?2:1)){socket.end();resolve(result);}
    });
  });
}
const members = tags.map((tag,i)=>({tag,name:names[i],townHallLevel:i===2?15:16,role:i===3?'leader':'member',trophies:5000,expLevel:200,clanRank:i+1,previousClanRank:i+1,donations:0,donationsReceived:0}));
const stamp = date => date.toISOString().replaceAll('-','').replaceAll(':','');
const now = Date.now();
const attacks = [{attackerTag:tags[1],defenderTag:enemy,stars:3,destructionPercentage:100,order:1,duration:120},{attackerTag:tags[1],defenderTag:enemy,stars:2,destructionPercentage:80,order:2,duration:150}];
const war = {state:'inWar',teamSize:4,attacksPerMember:2,preparationStartTime:stamp(new Date(now-172800000)),startTime:stamp(new Date(now-86400000)),endTime:stamp(new Date(now+10800000)),
  clan:{tag:clanTag,name:'Local Reminder Clan',clanLevel:10,attacks:2,stars:5,destructionPercentage:90,members:members.map((member,i)=>({tag:member.tag,name:member.name,townhallLevel:member.townHallLevel,mapPosition:i+1,...(i===1?{attacks}:{})}))},
  opponent:{tag:enemy,name:'Local Opponent',clanLevel:10,attacks:0,stars:0,destructionPercentage:0,members:[]}};
const calls=[];let message=999999999999994600n;
const provider=createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;
  const path=decodeURIComponent(new URL(req.url,'http://loopback').pathname);
  const data=raw?JSON.parse(raw):undefined;calls.push({method:req.method,path,data});res.setHeader('content-type','application/json');
  if(req.method==='GET'&&path===`/v1/clans/${clanTag}`)return res.end(JSON.stringify({tag:clanTag,name:'Local Reminder Clan',type:'inviteOnly',clanLevel:10,clanPoints:0,warWins:0,warWinStreak:0,members:4,memberList:members,badgeUrls:{},clanCapital:{capitalHallLevel:1,districts:[]}}));
  if(req.method==='GET'&&path===`/v1/clans/${clanTag}/currentwar`)return res.end(JSON.stringify(war));
  if(req.method==='GET'&&path.endsWith('/emojis'))return res.end(JSON.stringify({items:[]}));
  if(req.method==='POST'&&path===`/channels/${channel}/messages`)return res.end(JSON.stringify({id:String(message++),channel_id:channel,content:data.content,embeds:data.embeds??[]}));
  res.statusCode=404;res.end(JSON.stringify({reason:'notFound',code:10003}));
});
await new Promise(resolve=>provider.listen(0,'127.0.0.1',resolve));
const providerOrigin=`http://127.0.0.1:${provider.address().port}`;
const config=JSON.parse(readFileSync(join(trackingRoot,'config.json'),'utf8'));
config.dry_run=false;config.mock_db=false;
config.events={...config.events,stream,consumer:'isolated-manual-e2e',retention_seconds:300};
config.trackedclans={...config.trackedclans,snapshot_prefix:stream+':clan:'};
config.capital={...config.capital,snapshot_prefix:stream+':raid:'};
writeFileSync(join(directory,'config.json'),JSON.stringify(config));
const processEnv={PATH:process.env.PATH,TIMESCALE_HOST:'127.0.0.1',TIMESCALE_PORT:databaseURL.port,TIMESCALE_DATABASE:'clashking_dev',TIMESCALE_USERNAME:'clashking_local',TIMESCALE_PASSWORD:'clashking_local',TIMESCALE_SSLMODE:'disable',VALKEY_HOST:'127.0.0.1',VALKEY_PORT:String(valkeyPort),VALKEY_PASSWORD:valkeyPassword,
  DISCORD_BOT_TOKEN:Buffer.from(app).toString('base64')+'.local.token',DISCORD_GUILD_ALLOWLIST:guild,DISCORD_MESSAGE_CREATE_ENABLED:'false',CLASHKING_LOCAL_DISCORD_API_URL:providerOrigin,CLASHKING_PROXY_INTERNAL_ORIGIN:providerOrigin,DATA_ENCRYPTION_KEY:keys.DATA_ENCRYPTION_KEY};
let api,reminders,delivery,logs='';
const capture=child=>{child.stdout.on('data',data=>logs+=data);child.stderr.on('data',data=>logs+=data);return child;};
const stop=async child=>{if(child&&child.exitCode===null){child.kill('SIGTERM');await Promise.race([new Promise(resolve=>child.once('exit',resolve)),new Promise(resolve=>setTimeout(resolve,6000))]);if(child.exitCode===null){child.kill('SIGKILL');await new Promise(resolve=>child.once('exit',resolve));}}};
const assert=(value,message)=>{if(!value)throw Error(message);};
const wait=async(check,label)=>{for(let i=0;i<200;i++){if(await check())return;await new Promise(resolve=>setTimeout(resolve,100));}throw Error('Timed out '+label+' '+logs.slice(-3500));};
const sent=()=>calls.filter(call=>call.method==='POST'&&call.path===`/channels/${channel}/messages`);
const listening=async()=>Number((await db.query("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND query='LISTEN clashking_tracking_wake_v1'")).rows[0].count);
const rowHash=async()=>(await db.query("SELECT md5(string_agg(to_jsonb(r)::text,'' ORDER BY id)) AS hash FROM reminders r")).rows[0].hash;
const userToken=await new SignJWT({}).setProtectedHeader({alg:'HS256'}).setSubject(actor).setAudience('clashking-web').setIssuedAt().setExpirationTime('10m').sign(new TextEncoder().encode(keys.JWT_ACCESS_SECRET));
const request=async(path,body,token,expected)=>{
  const response=await fetch(`http://127.0.0.1:${port}${path}`,{method:'POST',headers:{authorization:`Bearer ${token}`,...(body===undefined?{}:{'content-type':'application/json'})},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const value=await response.json();assert(response.status===expected,`${path} expected${expected} got${response.status} ${JSON.stringify(value)}`);return value;
};
try {
  await db.query("INSERT INTO auth_users(user_id,provider) VALUES($1,'discord')",[actor]);
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Manual E2E'),($2,'Other Manual E2E')",[guild,otherGuild]);
  const generation=randomUUID();
  await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
  for(const id of [guild,otherGuild])await db.query('INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,$2,$3,0,$4,true,true,true)',[id,JSON.stringify({owner_id:actor}),app,generation]);
  await db.query("INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,'{}'),($3,$2,'{}')",[guild,actor,otherGuild]);
  const insert=async(server,halls,disabled=false)=>(await db.query("INSERT INTO reminders(server_id,type,type_name,clan_tag,webhook_token,channel_id,minutes_remaining,townhalls,roles,disabled) VALUES($1,1,'War',$2,'',$3,15,$4,ARRAY['member'],$5) RETURNING id",[server,clanTag,channel,halls,disabled])).rows[0].id;
  const eligible=await insert(guild,[16]),empty=await insert(guild,[14]),disabled=await insert(guild,[16],true),foreign=await insert(otherGuild,[16]);
  assert((await db.query("SELECT to_regclass('public.manual_reminder_requests') IS NULL AS absent")).rows[0].absent,'Obsolete queue table exists');
  const initialHash=await rowHash();
  execFileSync('go',['build','-o',join(directory,'tracking'),'.'],{cwd:trackingRoot,stdio:'pipe'});
  execFileSync('npm',['run','build','--workspace','@clashking/api-contracts'],{cwd:apiRoot,stdio:'pipe'});
  delivery=capture(spawn(join(directory,'tracking'),['--script','discord-delivery'],{cwd:directory,env:processEnv,stdio:['ignore','pipe','pipe']}));
  reminders=capture(spawn(join(directory,'tracking'),['--script','reminders'],{cwd:directory,env:processEnv,stdio:['ignore','pipe','pipe']}));
  await wait(async()=>await listening()>0,'actual PostgreSQL listener');
  api=capture(spawn(process.execPath,['scripts/start-local-rewrite-api.mjs'],{cwd:apiRoot,env:{...process.env,CLASHKING_PERSISTENT_LOCAL_API:'1',CLASHKING_LOCAL_DATABASE_URL:databaseURL.href,CLASHKING_LOCAL_API_PORT:String(port),CLASHKING_LOCAL_DISCORD_CLIENT_ID:app,CLASHKING_LOCAL_DISCORD_CLIENT_SECRET:'local-only',CLASHKING_LOCAL_ARCHIVE_BRIDGE:'0',CLASHKING_LOCAL_PRODUCTION_READS:'0',CLASHKING_LOCAL_CLASH_PROXY_ORIGIN:providerOrigin,CLASHKING_LOCAL_STORAGE_ROOT:join(directory,'api-storage'),...Object.fromEntries(Object.entries(keys).map(([key,value])=>['CLASHKING_LOCAL_'+key,value]))},stdio:['ignore','pipe','pipe']}));
  await wait(async()=>{try{return(await fetch(`http://127.0.0.1:${port}/v2/health`)).ok}catch{return false}},'full API worker');
  const botPath=`/v2/bot/server/${guild}/reminders/manual`;
  const botBody={clanTag,type:'War'};
  await request(botPath,{...botBody,type:'Inactivity'},keys.API_BOT_TOKEN,400);
  await request(`/v2/server/${guild}/reminders`,{type:'Inactivity',clan_tag:clanTag,channel_id:channel,time:'24hr'},userToken,400);
  const listed=await fetch(`http://127.0.0.1:${port}/v2/server/${guild}/reminders`,{headers:{authorization:`Bearer ${userToken}`}});
  const listedBody=await listed.json();
  assert(listed.ok&&!Object.hasOwn(listedBody,'inactivity_reminders'),'Retired reminder response group remains exposed');
  const wakes=[];
  db.on('notification', notification=>wakes.push(JSON.parse(notification.payload)));
  await db.query('LISTEN clashking_tracking_wake_v1');
  const botResult=await request(botPath,botBody,keys.API_BOT_TOKEN,202);assert(botResult.accepted===2,'Bot accepted count must include both enabled configurations');
  await wait(()=>sent().length===1,'actual eligible bot reminder delivery');
  assert(wakes.length===2&&wakes.every(wake=>Object.keys(wake).sort().join(',')==='kind,reminderId,serverId'&&wake.kind==='reminder_send'&&wake.serverId===guild),'Manual NOTIFY must contain only kind, reminderId, and serverId');
  await db.query('UNLISTEN clashking_tracking_wake_v1');
  await new Promise(resolve=>setTimeout(resolve,700));assert(sent().length===1,'Empty configured reminder produced a message');
  const content=sent()[0].data.content;
  assert(content.includes(names[0])&&content.includes('2 attacks left'),'Eligible source member was not rendered');
  for(const name of names.slice(1))assert(!content.includes(name),'Ineligible source member rendered: '+name);
  const userResult=await request(`/v2/server/${guild}/reminders/${eligible}/send`,undefined,userToken,202);assert(userResult.accepted===1,'User accepted count');
  await wait(()=>sent().length===2,'actual user-authenticated reminder delivery');
  await request(`/v2/server/${guild}/reminders/${disabled}/send`,undefined,userToken,404);
  await request(`/v2/server/${guild}/reminders/${foreign}/send`,undefined,userToken,404);
  await request(`/v2/server/${guild}/reminders/${eligible}/send`,undefined,keys.API_BOT_TOKEN,401);
  await request(botPath,botBody,'invalid-token',401);
  await request(`/v2/server/${guild}/reminders/${empty}/send`,undefined,userToken,202);
  await new Promise(resolve=>setTimeout(resolve,700));assert(sent().length===2,'Empty user reminder produced a message');
  await stop(reminders);await wait(async()=>await listening()===0,'listener disconnect');
  const beforeStream=await redis('XLEN',stream);
  assert((await request(`/v2/server/${guild}/reminders/${eligible}/send`,undefined,userToken,202)).accepted===1,'Missing-listener request was not accepted best effort');
  await new Promise(resolve=>setTimeout(resolve,700));
  assert(await redis('XLEN',stream)===beforeStream,'Missing listener unexpectedly published a durable event');
  assert(await rowHash()===initialHash,'Manual request persisted or changed reminder settings');
  reminders=capture(spawn(join(directory,'tracking'),['--script','reminders'],{cwd:directory,env:processEnv,stdio:['ignore','pipe','pipe']}));
  await wait(async()=>await listening()>0,'listener reconnect');await new Promise(resolve=>setTimeout(resolve,1000));
  assert(sent().length===2,'Disconnected request replayed after reconnect');
  await request(`/v2/server/${guild}/reminders/${eligible}/send`,undefined,userToken,202);
  await wait(()=>sent().length===3,'new request after reconnect');
  assert(await rowHash()===initialHash,'Manual flow changed source settings');
  war.state='preparation';war.startTime=stamp(new Date(Date.now()+3600000));
  await request(`/v2/server/${guild}/reminders/${eligible}/send`,undefined,userToken,202);
  await wait(()=>sent().length===4,'dashboard preparation reminder through listener and delivery');
  assert(sent().at(-1).data.content.includes('War starts <t:')&&sent().at(-1).data.content.includes('War preparation'),'Preparation reminder is not labeled with its start time');
  assert(await rowHash()===initialHash,'Preparation send changed reminder settings');
  console.log(JSON.stringify({checks:['retired bot reminder400','retired dashboard create400','retired response group absent','full API bot auth accepted2','full API user auth accepted1','actual pg_notify listener','actual reminders process eligibility','actual Valkey event','actual Discord delivery process','one eligible member and no excluded members','empty filters produce no message','disabled404','wrong-server404','bot rejected by user route401','bad bot token401','missing listener accepted without SQL persistence','no replay after reconnect','new request works after reconnect','dashboard preparation reminder'],discordMessages:sent().length,externalDiscordWrites:0,database:'isolated disposable clone',runtimeDirectory:directory}));
} finally {
  await stop(api);await stop(reminders);await stop(delivery);
  await db.end();await redis('DEL',stream);await new Promise(resolve=>provider.close(resolve));
}
