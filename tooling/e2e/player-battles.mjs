// Signed interactions exercise the actual Bot Worker and running local API.
// Discord delivery is captured; this check never posts a message to Discord.
import assert from 'node:assert/strict';
import {generateKeyPairSync,sign} from 'node:crypto';
import {createRequire} from 'node:module';
import {bundleWorker} from './bundle-worker.mjs';
import {loadWorkspace} from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';

const workspace=loadWorkspace('/Users/matthewanderson/ClashKing');
const api=process.env.PLAYER_BATTLES_API_ORIGIN??`http://127.0.0.1:${workspace.config.ports.api}`;
assert.equal(new URL(api).hostname,'127.0.0.1');
const app=workspace.env.DISCORD_CLIENT_ID;
assert.equal(app,'808566437199216691');
const headers={Authorization:`Bearer ${workspace.env.API_BOT_TOKEN}`};
const get=async path=>{
 const response=await fetch(api+path,{headers});
 assert.equal(response.status,200,`Local API failed: ${path}`);
 return response.json();
};
const rankedTag=process.env.PLAYER_BATTLES_RANKED_TAG??'#2J8V28GV0';
const legendTag=process.env.PLAYER_BATTLES_LEGEND_TAG??'#LG8Q9QYR';
const player=await get(`/v2/bot/clash/players/${encodeURIComponent(rankedTag)}`);
assert.ok(player.currentLeagueGroupTag&&player.currentLeagueSeasonId,'Choose a player in a current Ranked group');
const group=await get(`/v2/bot/clash/leaguegroup/${encodeURIComponent(player.currentLeagueGroupTag)}/${player.currentLeagueSeasonId}?playerTag=${encodeURIComponent(rankedTag)}`);
const member=group.members.find(row=>row.playerTag===rankedTag);
assert.ok(member);
const inventoryResponse=await fetch(`https://discord.com/api/v10/applications/${app}/emojis`,{headers:{Authorization:`Bot ${workspace.env.DISCORD_BOT_TOKEN}`}});
assert.equal(inventoryResponse.status,200);
const inventory=await inventoryResponse.json();
const require=createRequire(`${workspace.config.repositories.api}/package.json`);
const {Miniflare,convertV4MiniflareOptions}=require('miniflare');
const {privateKey,publicKey}=generateKeyPairSync('ed25519');
const replies=new Map();let counter=999999999999997100n;
const bot=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{
 name:'player-battles-e2e',...await bundleWorker(),compatibilityDate:'2026-08-22',compatibilityFlags:['nodejs_compat'],
 bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://local-dash.clashk.ing',CLASHKING_API_BASE_URL:api,CLASHKING_API_TOKEN:workspace.env.API_BOT_TOKEN,DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:`${Buffer.from(app).toString('base64')}.local.token`,DISCORD_PUBLIC_KEY:publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex')},
 outboundService:async request=>{
  const url=new URL(request.url);
  if(url.hostname==='discord.com'){
   if(request.method==='GET'&&url.pathname.endsWith('/emojis'))return Response.json(inventory);
   assert.ok(url.pathname.includes('/webhooks/'),'Unexpected Discord operation');
   if(request.method==='DELETE')return new Response(null,{status:204});
   const payload=request.headers.get('content-type')?.startsWith('multipart/form-data')?JSON.parse((await request.formData()).get('payload_json')):await request.json();
   replies.set(url.pathname.split('/')[5],payload);
   return Response.json({id:'999999999999997999'});
  }
  if(url.origin===api)return fetch(request.url,{method:request.method,headers:request.headers,body:['GET','HEAD'].includes(request.method)?undefined:await request.arrayBuffer()});
  if(request.method==='GET'&&['assets.clashk.ing','api-assets.clashofclans.com','cdn.discordapp.com'].includes(url.hostname))return fetch(request.url,{redirect:'manual'});
  throw Error('Unexpected external request');
 },
}]}));
try{
 const origin=new URL('/interactions',String(await bot.ready));
 async function interact(data){
  const token=String(counter++),body=JSON.stringify({id:token,application_id:app,channel_id:'999999999999997002',user:{id:'999999999999997003',username:'Local'},version:1,token,...data});
  const timestamp=String(Math.floor(Date.now()/1000));
  const response=await fetch(origin,{method:'POST',headers:{'Content-Type':'application/json','X-Signature-Timestamp':timestamp,'X-Signature-Ed25519':sign(null,Buffer.from(timestamp+body),privateKey).toString('hex')},body});
  assert.equal(response.status,200);const initial=await response.json();
  if(![5,6].includes(initial.type))return initial.data;
  for(let i=0;i<300;i++){if(replies.has(token))return replies.get(token);await new Promise(resolve=>setTimeout(resolve,100));}
  throw Error('Deferred reply timed out');
 }
 const command=(name,sub,tag)=>interact({type:2,data:{name,options:[{name:sub,type:1,options:[{name:'player',type:3,value:tag}]}]}});
 const fields=reply=>(reply.embeds?.[0]?.fields??[]);
 const lookup=await command('player','lookup',rankedTag);
 const summary=fields(lookup)[0].value;
 assert.ok(summary.includes(`**${member.leagueTrophies.toLocaleString('en')}**`),'Lookup did not use group trophies');
 const tierResponse=await fetch('https://assets.clashk.ing/static_data/league_tiers.json');assert.equal(tierResponse.status,200);
 const rules=(await tierResponse.json()).items.find(item=>item._id===player.leagueTier.id);
 assert.ok(rules);
 const total=group.members.length,rank=1+group.members.filter(row=>row.leagueTrophies>member.leagueTrophies).length;
 const zone=rank<=Math.round(total*rules.promote_percentage/100)?'Promotion':rank>total-Math.round(total*rules.demote_percentage/100)?'Demotion':'Staying';
 const iconName=zone==='Promotion'?'up_green_arrow':zone==='Demotion'?'down_red_arrow':'grey_dash';
 assert.ok(summary.split("\n")[0].includes(`**#${rank}**)`));
 assert.ok(!summary.includes(zone));
 assert.ok(summary.includes(`:${iconName}:`));
 assert.ok(summary.includes(`**${member.attackWinCount+member.attackLoseCount}/${rules.battle_count}**`));
 assert.ok(summary.includes(`**${member.defenseWinCount+member.defenseLoseCount}/${rules.battle_count}**`));
 assert.equal(summary.replace(/\n\u200b$/u,'').split('\n').length,2,'Ranked summary must remain compact');
 assert.ok(!summary.includes('<t:'));
 assert.ok(!summary.includes(`#${rank} /`),'Do not show group size beside rank');
 assert.ok(!fields(lookup).some(field=>/^Attacks|^Defenses/.test(field.name)),'Lookup must not render battle-list fields');
 const ranked=await command('ranked','player',rankedTag);
 assert.equal(fields(ranked).filter(field=>/^Attacks|^Defenses/.test(field.name)).length,2,'Dedicated Ranked command lost battle details');
 const select=lookup.components[0].components[0];
 const refreshed=await interact({type:3,data:{custom_id:select.custom_id,component_type:3,values:['overview']}});
 assert.equal(fields(refreshed)[0].value,summary,'Overview selection changed summary');
 const legend=await command('player','lookup',legendTag);
 const today=new Date(Date.now()-5*3600000).toISOString().slice(0,10);
 const day=await get(`/v2/player/${encodeURIComponent(legendTag)}/legend/${today}/battlelog`);
 const legendSummary=fields(legend)[0].value;
 assert.ok(legendSummary.includes(`**${day.attacks.length}/8**`));
 assert.ok(legendSummary.includes(`**${day.defenses.length}/8**`));
 assert.ok(!legendSummary.includes('<t:'));
 assert.ok(!fields(legend).some(field=>/^Attacks|^Defenses/.test(field.name)));

 for(const reply of [lookup,ranked,refreshed,legend]){
  assert.deepEqual(reply.allowed_mentions,{parse:[]});
  assert.ok(fields(reply).every(f=>f.value.length<=1024));
 }
 console.log('PASS: compact Ranked trophies/rank/standing/usage, unchanged dedicated details, overview control and compact Legend usage against the running local API; no Discord messages sent.');
}finally{await bot.dispose();}
