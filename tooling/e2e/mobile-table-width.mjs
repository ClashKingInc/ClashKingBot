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
   if(u.pathname===`/v2/links/server/${guild}/clans`)return Response.json({clans:[{name:'Mobile Clan',tag,badge:null,verified:false,members}]});
   if(u.pathname===`/v2/server/${guild}/settings`)return Response.json({embed_color:'#123456'});
   if(u.pathname.includes('activity')||u.pathname.includes('command'))return Response.json({ok:true});
   throw Error('Unexpected API request '+request.method+' '+u.pathname);
  }
  if(u.hostname==='discord.com'){
   if(request.method==='GET'&&u.pathname.endsWith('/emojis'))return Response.json({items:[]});
   if(request.method==='PATCH'&&u.pathname.includes('/messages/@original')){
    replies.set(u.pathname.split('/')[5],await request.json());return Response.json({id:'999999999999991004'});
   }
  }
  throw Error('Unexpected external request '+request.method+' '+u.href);
 },
}]}));
async function interact(data){
 const token='mobile-'+(++sequence),timestamp=String(Math.floor(Date.now()/1000));
 const body=JSON.stringify({id:String(999999999999991100n+BigInt(sequence)),application_id:app,guild_id:guild,channel_id:'999999999999991005',member:{user:{id:actor,username:'Local'},roles:[],permissions:'0'},version:1,token,...data});
 const response=await bot.dispatchFetch('https://bot.local/interactions',{method:'POST',headers:{'Content-Type':'application/json','X-Signature-Timestamp':timestamp,'X-Signature-Ed25519':sign(null,Buffer.from(timestamp+body),privateKey).toString('hex')},body});
 assert.equal(response.status,200);const initial=await response.json();
 if(![5,6].includes(initial.type))return initial.data;
 for(let i=0;i<100;i++){if(replies.has(token))return replies.get(token);await new Promise(resolve=>setTimeout(resolve,25));}
 throw Error('No deferred reply');
}
try{
 const result=await interact({type:2,data:{name:'link',options:[{name:'list',type:1,options:[{name:'clan',type:3,value:tag}]}]}});
 const text=result.embeds.map(e=>e.description).join('\n');
 assert.match(text,/Linked & in server: 2/);assert.match(text,/Not in server or hidden: 1/);assert.match(text,/Not linked: 1/);
 const rows=[...text.matchAll(/`([^`]+)`/gu)].map(match=>match[1]);assert.equal(rows.length,4);
 for(const row of rows){assert.equal(row,row.trimEnd(),'No trailing padding');assert.ok(stringWidth(row)<=35,`Oversized row: ${row}`);assert.ok(!row.includes('\ufffd'),'No broken Unicode');}
 assert.ok(text.includes('#PYLQGRJC'),'Outside player tag preserved');
 assert.ok(!text.includes('abcdefghijklmnopqr'),'Long display label must fit remaining width');
 assert.deepEqual(result.allowed_mentions,{parse:[]});
 const refresh=result.components.flatMap(row=>row.components).find(item=>item.type===2);
 const again=await interact({type:3,data:{custom_id:refresh.custom_id,component_type:2}});
 assert.deepEqual(again.embeds,result.embeds,'Refresh retains compact formatting');
 console.log(JSON.stringify({signedWorkerRequests:2,linkRows:rows.length,maxTextColumns:Math.max(...rows.map(row=>stringWidth(row))),trailingPadding:false,unicodeAndTags:'passed',publicRefresh:'passed',externalDiscordWrites:0}));
}finally{await bot.dispose();}
