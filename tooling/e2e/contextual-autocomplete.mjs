// Actual signed HTTP interactions through the bundled Bot Worker. Only external
// API/Discord responses are local fixtures; no production messages are sent.
import assert from 'node:assert/strict';
import {generateKeyPairSync,sign} from 'node:crypto';
import {createRequire} from 'node:module';
import {bundleWorker} from './bundle-worker.mjs';
const require=createRequire(new URL('../../worker/package.json',import.meta.url));
const {Miniflare,convertV4MiniflareOptions}=require('miniflare');
const {default:stringWidth}=await import(new URL('../../worker/node_modules/string-width/index.js',import.meta.url));
const {publicKey,privateKey}=generateKeyPairSync('ed25519');
const app='999999999999991001',guild='999999999999991002',actor='999999999999991003';
const tag='#PYLQGRJC',replies=new Map();let sequence=0;
const recentWrites=[];
const directoryClans=Array.from({length:46},(_,i)=>({name:`Family Clan ${String(i+1).padStart(2,'0')}`,tag:i===0?'#PYLQGRJ':'#PYLQ'+i.toString(8).replaceAll('1','P').replaceAll('3','Y').replaceAll('4','L').replaceAll('5','Q').replaceAll('6','G').replaceAll('7','R'),category:'Family',categoryOrder:0}));
const members=[
 {name:'SIR TROLLSON',tag:'#PYLQGRJCUV',townHall:18,hidden:false,link:{userId:actor,inServer:true,username:'emma.polishpower',verified:false}},
 {name:'👩🏽‍🚀 漢字 Café Long Player',tag:'#PYLQGRJCU',townHall:18,hidden:false,link:{userId:actor,inServer:true,username:'abcdefghijklmnopqr',verified:true}},
 {name:'A very long outside player name',tag:'#PYLQGRJC',townHall:18,hidden:false,link:{userId:actor,inServer:false,username:null,verified:true}},
 {name:'Short',tag:'#PYLQGRJ',townHall:6,hidden:false,link:null},
];
const bot=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{
 name:'mobile-width-e2e',...await bundleWorker(),compatibilityDate:'2026-08-22',compatibilityFlags:['nodejs_compat'],
 bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:'https://local-api.test',CLASHKING_API_TOKEN:'local-only',DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:`${Buffer.from(app).toString('base64')}.local.token`,DISCORD_PUBLIC_KEY:publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex')},
 outboundService:async request=>{
  const u=new URL(request.url);
  if(u.hostname==='local-api.test'){
   if(u.pathname===`/v2/bot/servers/${guild}/player-autocomplete`)return Response.json({items:[{name:'Server Player',tag:'#PYLQGRJC',townHallLevel:18,clanName:'Must not show'}]});
   if(u.pathname===`/v2/server/${guild}/clans-basic`)return Response.json(directoryClans);
   if(u.pathname.startsWith('/v2/bot/clash/clans/'))return Response.json({members:50,warLeague:{name:'Champion League I'}});
   if(u.pathname.endsWith('/settings'))return Response.json({embed_color:'#000000'});
   if(u.pathname.includes('/search-suggestions')){
    if(request.method==='POST'){recentWrites.push(await request.json());return Response.json({ok:true});}
    return Response.json({items:u.searchParams.get('type')==='clan'?[{name:'Bookmarked Clan',tag:'#PYLQGRL'}]:[{name:'Recent Player',tag:'#PYLQGRQ',townHallLevel:17}]});
   }
   if(u.pathname==='/v2/bot/legends/player-autocomplete')return Response.json({items:[{name:'Global Legend',tag:'#PYLQGRU',townHallLevel:18}]});
   if(u.pathname==='/v2/player/search'){
    assert.equal(u.searchParams.get('leagueIds'),'105000036');
    return Response.json({items:[{name:'Global Legend',tag:'#PYLQGRU',townHallLevel:18}]});
   }
   if(u.pathname.includes('/league/history'))return Response.json({items:[{id:'999999999999991010',name:'people'},{id:'999999999999991011',name:'championleaguei'},{id:'999999999999991012',name:'refresh'}]});
   if(u.pathname.startsWith('/v2/bot/clash/players/'))return Response.json({name:'Recent Player',tag:'#PYLQGRQ',townHallLevel:17});
   if(u.pathname.includes('activity'))return Response.json({ok:true});
   throw Error('Unexpected API request '+request.method+' '+u.pathname);
  }
  if(u.hostname==='discord.com'){
   if(request.method==='GET'&&u.pathname.endsWith('/emojis'))return Response.json({items:[{id:'999999999999991010',name:'people'},{id:'999999999999991011',name:'championleaguei'},{id:'999999999999991012',name:'refresh'}]});
   if(request.method==='GET'&&u.pathname===`/api/v10/guilds/${guild}`)return Response.json({id:guild,name:'Family directory'});
   if(request.method==='PATCH'&&u.pathname.includes('/messages/@original')){
    replies.set(u.pathname.split('/')[5],await request.json());return Response.json({id:'999999999999991004'});
   }
  }
  throw Error('Unexpected external request '+request.method+' '+u.href);
 },
}]}));
async function interact(data,dm=false){
 const token='mobile-'+(++sequence),timestamp=String(Math.floor(Date.now()/1000));
 const body=JSON.stringify({id:String(999999999999991100n+BigInt(sequence)),application_id:app,...(dm?{user:{id:actor}}:{guild_id:guild}),channel_id:'999999999999991005',member:{user:{id:actor,username:'Local'},roles:[],permissions:'0'},version:1,token,...data});
 const response=await bot.dispatchFetch('https://bot.local/interactions',{method:'POST',headers:{'Content-Type':'application/json','X-Signature-Timestamp':timestamp,'X-Signature-Ed25519':sign(null,Buffer.from(timestamp+body),privateKey).toString('hex')},body});
 assert.equal(response.status,200);const initial=await response.json();
 if(![5,6].includes(initial.type))return initial.data;
 for(let i=0;i<100;i++){if(replies.has(token))return replies.get(token);await new Promise(resolve=>setTimeout(resolve,25));}
 throw Error('No deferred reply');
}
try{
 const auto=(name,sub,option,value='',dm=false)=>interact({type:4,data:{name,options:sub?[{name:sub,type:1,options:[{name:option,type:3,value,focused:true}]}]:[{name:option,type:3,value,focused:true}]}},dm);
 for(const [name,sub] of [['player','lookup'],['ranked','player']]){
  const result=await auto(name,sub,'player');assert.equal(result.choices[0].name,'¹⁸ Server Player | #PYLQGRJC');
 }
 const legends=await auto('legends','player','player');assert.equal(legends.choices.length,2);assert.match(legends.choices[1].name,/Global Legend/);
 const searched=await auto('legends','player','player','Global');assert.ok(searched.choices.some(item=>item.value==='#PYLQGRU'));
 const reminders=await auto('reminders',null,'clan');assert.equal(reminders.choices[0].value,'#PYLQGRJ');
 for(const [name,sub] of [['player','lookup'],['ranked','player'],['legends','player']]){
  const result=await auto(name,sub,'player','',true);assert.equal(result.choices[0].name,'¹⁷ Recent Player | #PYLQGRQ');
 }
 const clans=await auto('clan','search','clan','',true);assert.equal(clans.choices[0].value,'#PYLQGRL');
 assert.equal(recentWrites.length,0,'Autocomplete must not record searches');
 await interact({type:2,data:{name:'ranked',options:[{name:'history',type:1,options:[{name:'player',type:3,value:'#PYLQGRQ'}]}]}},true);
 assert.equal(recentWrites.length,1);assert.equal(recentWrites[0].tag,'#PYLQGRQ');
 const directory=await interact({type:2,data:{name:'family',options:[{name:'clans',type:1}]}});
 const verifyDirectory=(message)=>{
  assert.ok(message.embeds?.[0]?.description,'Expected clan directory, not an error reply');
  assert.ok(message.embeds[0].description.length<=4096);
  const controls=message.components.flatMap(row=>row.components);
  const ids=controls.map(control=>control.custom_id).filter(Boolean);
  assert.equal(new Set(ids).size,ids.length,'Disabled navigation and refresh IDs must remain unique');
  assert.ok(ids.every(id=>id.length<=100));
  return controls;
 };
 const controls=verifyDirectory(directory);
 assert.ok(controls.find(c=>c.label==='Previous')?.disabled);
 const next=controls.find(c=>c.label==='Next'&&!c.disabled);
 assert.ok(next,'46 linked clans must paginate beyond the compact 45-clan cap');
 const second=await interact({type:3,data:{custom_id:next.custom_id,component_type:2}});
 const previous=verifyDirectory(second).find(c=>c.label==='Previous'&&!c.disabled);
 assert.ok(previous);
 const back=await interact({type:3,data:{custom_id:previous.custom_id,component_type:2}});
 verifyDirectory(back);
 assert.equal(back.embeds[0].description,directory.embeds[0].description);
 console.log('PASS signed Bot autocomplete: server players, global Legends, reminder clans, superscript labels, DM personal sources, successful-search recording and unique family pagination controls.');
}finally{await bot.dispose();}
