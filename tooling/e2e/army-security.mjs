import { spawn } from 'node:child_process';
import { generateKeyPairSync, sign, createHash, randomBytes } from 'node:crypto';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const botRoot=resolve(fileURLToPath(new URL('../../',import.meta.url)));
const root=resolve(process.env.CLASHKING_E2E_API_REPO??join(botRoot,'../clashking_api'));
const assets=resolve(process.env.CLASHKING_E2E_ASSETS_REPO??join(botRoot,'../clashking_assets'));
const pg=createRequire(join(root,'package.json'))('pg');
const secrets=Object.fromEntries(['DATA_ENCRYPTION_KEY','JWT_ACCESS_SECRET','JWT_REFRESH_SECRET','API_BOT_TOKEN','AI_USAGE_SECRET','STRIPE_WEBHOOK_SECRET'].map(key=>[key,randomBytes(32).toString('base64url')]));
const port=Number(process.env.CLASHKING_E2E_API_PORT??8802);
if(!Number.isInteger(port)||port<1024||port>65535)throw Error('Invalid loopback port');
const {publicKey,privateKey}=generateKeyPairSync('ed25519');
const publicHex=publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex');
const app='999999999999998501', actor='999999999999998502', other='999999999999998503';
const database=process.env.CLASHKING_E2E_DATABASE_URL??'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev';
const databaseURL=new URL(database);if(databaseURL.protocol!=='postgres:'||databaseURL.hostname!=='127.0.0.1'||databaseURL.pathname!=='/clashking_dev')throw Error('Only owned loopback clashking_dev is allowed');
const client=new pg.Client({connectionString:database});
await client.connect();
const composition=(await client.query('SELECT share_code FROM army_compositions ORDER BY length(share_code),share_code LIMIT 1')).rows[0]?.share_code;
if(!composition)throw new Error('A known local army composition is required');
const rows=await client.query('SELECT user_id FROM auth_users WHERE user_id = ANY($1::text[])',[[actor,other]]);
if(rows.rowCount)throw new Error('Synthetic identity already exists; do not overwrite');
await client.query("INSERT INTO auth_users(user_id,provider) VALUES($1,'discord'),($2,'discord')",[actor,other]);
const env={PATH:process.env.PATH,HOME:process.env.HOME,TMPDIR:process.env.TMPDIR,CLASHKING_PERSISTENT_LOCAL_API:'1',CLASHKING_LOCAL_DATABASE_URL:database,
  CLASHKING_LOCAL_API_PORT:String(port),CLASHKING_LOCAL_DISCORD_CLIENT_ID:app,
  CLASHKING_LOCAL_DISCORD_CLIENT_SECRET:'local-e2e-only',CLASHKING_LOCAL_DISCORD_PUBLIC_KEY:publicHex,
  CLASHKING_LOCAL_ARCHIVE_BRIDGE:'0',CLASHKING_LOCAL_CLASH_PROXY_ORIGIN:'http://127.0.0.1:65534',
  CLASHKING_LOCAL_STATIC_ASSETS_ROOT:join(assets,'assets/static_data'),
  CLASHKING_LOCAL_STORAGE_ROOT:mkdtempSync(join(tmpdir(),'ck-army-e2e-')),
  ...Object.fromEntries(Object.entries(secrets).map(([k,v])=>[`CLASHKING_LOCAL_${k}`,v]))};
const worker=spawn(process.execPath,['scripts/start-local-rewrite-api.mjs'],{cwd:root,env,stdio:['ignore','pipe','pipe']});
let startup='';worker.stdout.on('data',chunk=>startup+=chunk);worker.stderr.on('data',chunk=>startup+=chunk);
const base=`http://127.0.0.1:${port}`;
const payload=(id=actor)=>({id:'999999999999998504',application_id:app,guild_id:'999999999999998505',channel_id:'999999999999998506',
  member:{user:{id,username:'Local E2E'},roles:[]},type:2,data:{name:'army',options:[{name:'link',type:1,options:[{name:'army',type:3,value:composition},{name:'nickname',type:3,value:'Security check'}]}]}});
const proof=(value,timestamp=String(Math.floor(Date.now()/1000)))=>{const rawBody=JSON.stringify(value);return {interaction:{rawBody,timestamp,signature:sign(null,Buffer.from(timestamp+rawBody),privateKey).toString('hex')}};};
async function request(body,expected=200,token=secrets.API_BOT_TOKEN){
  const response=await fetch(base+'/v2/bot/armies/interaction',{method:'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},body:JSON.stringify(body)});
  const data=await response.json();
  if(response.status!==expected)throw new Error(`Expected ${expected}, received ${response.status}: ${JSON.stringify(data)}`);
  return data;
}
try{
  let ready=false;
  for(let i=0;i<60;i++){try{const response=await fetch(base+'/v2/health');if(response.ok&&startup.includes('local_static_assets_seeded')){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,500));}
  if(!ready)throw new Error('Local API failed to start: '+startup.slice(-4000));
  await request(proof(payload()),401,'');
  const tampered=proof(payload());tampered.interaction.rawBody=JSON.stringify(payload(other));await request(tampered,401);
  await request(proof({...payload(),application_id:'999999999999998599'}),403);
  await request(proof(payload(),String(Math.floor(Date.now()/1000)-600)),401);
  const preview=await request(proof(payload()));
  const hash=createHash('sha256').update(preview.shareCode).digest('hex');
  const savePayload={...payload(),type:3,data:{custom_id:`ck:army:save:${hash}`,component_type:2},message:{id:'999999999999998507',author:{id:app},embeds:[{title:'Security check'}],components:[{type:1,components:[{type:2,style:5,url:preview.armyLink},{type:2,style:3,custom_id:`ck:army:save:${hash}`}]}]}};
  const saved=await request({...proof(savePayload),actorId:other});
  if(!saved.saved||saved.shareCode!==composition)throw new Error('Canonical save response mismatch');
  const stored=(await client.query('SELECT user_id,share_code FROM user_saved_armies WHERE user_id=ANY($1::text[])',[[actor,other]])).rows;
  if(stored.length!==1||stored[0].user_id!==actor)throw new Error('Signed actor ownership failed');
  const selection={...payload(other),type:3,data:{custom_id:`ck:army:pick:${actor}`,component_type:3,values:[createHash('sha256').update(composition).digest('hex')]}};
  await request(proof(selection),400);
  const chosen=await request(proof({...selection,member:payload().member}));
  if(chosen.shareCode!==composition)throw new Error('Saved army selection mismatch');
  for(const [path,token,status] of [
    ['/v2/bot/clash/players/%23P09LP8CY','',401],
    ['/v2/bot/clash/players/https%3A%2F%2Fevil.example',secrets.API_BOT_TOKEN,400],
    ['/v2/bot/clash/players/%23P09LP8CY?url=https://evil.example',secrets.API_BOT_TOKEN,400],
    ['/proxy/v1/players/%23P09LP8CY',secrets.API_BOT_TOKEN,401],
  ]){const response=await fetch(base+path,{headers:token?{Authorization:`Bearer ${token}`}:{}});if(response.status!==status)throw new Error(`Scope check ${path}: ${response.status}, expected ${status}`);}
  console.log(JSON.stringify({port,checks:['missing bot token rejected','tampered actor signature rejected','wrong application rejected','expired proof rejected','unsigned actor override ignored','saved row owned only by signed actor','cross-user selection rejected','owner saved-army selection succeeded'],savedArmies:stored.length}));
}finally{
  worker.kill('SIGTERM');
  await client.query('DELETE FROM auth_users WHERE user_id=ANY($1::text[])',[[actor,other]]);
  await client.end();
}
