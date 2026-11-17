// Signed requests through the actual Bot Worker; only external providers are fixtures.
import assert from 'node:assert/strict';
import {generateKeyPairSync,sign} from 'node:crypto';
import {createRequire} from 'node:module';
import {bundleWorker} from './bundle-worker.mjs';
const require=createRequire(new URL('../../worker/package.json',import.meta.url));
const {Miniflare,convertV4MiniflareOptions}=require('miniflare');
const {publicKey,privateKey}=generateKeyPairSync('ed25519');
const app='999999999999992101',guild='999999999999992102',actor='999999999999992103',id='12345678-1234-4234-8234-123456789012';
const th19={id:'999999999999992119',name:'th19'};
let removing=false,sequence=0;
const replies=new Map();
const members=[{playerTag:'#2PP',playerName:'[GC] Valentine',townhall:19,clanName:'[GC] Clan'},
];
const runtime=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{
 name:'roster-display',...await bundleWorker(),compatibilityDate:'2026-09-02',compatibilityFlags:['nodejs_compat'],
 bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:'https://local-api.test',CLASHKING_API_TOKEN:'local-only',DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:'local-only',DISCORD_PUBLIC_KEY:publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex')},
 outboundService:async request=>{
  const u=new URL(request.url);
  if(u.hostname==='local-api.test'){
   if(u.pathname.endsWith('/accounts'))return Response.json({items:members.map(m=>({tag:m.playerTag,name:m.playerName,townhall:m.townhall,isVerified:true,signedUp:removing})),remainingSlots:3});
   if(u.pathname.endsWith('/rosters/'+id))return Response.json({roster:{id,serverId:guild,alias:'[GC] Roster',description:null,memberCount:members.length,members,questionnaire:{questions:[]}}});
   if(u.pathname.includes('activity'))return Response.json({ok:true});
  }
  if(u.hostname==='discord.com'){
   if(request.method==='GET'&&u.pathname.endsWith('/emojis'))return Response.json({items:[th19]});
   if(request.method==='PATCH'&&u.pathname.includes('/messages/@original')){replies.set(u.pathname.split('/')[5],await request.json());return Response.json({id:'999999999999992104'});}
  }
  throw Error('Unexpected provider request '+request.method+' '+u.pathname);
 }
}]}));
async function interact(action){
 const token='roster-display-'+(++sequence),timestamp=String(Math.floor(Date.now()/1000));
 const body=JSON.stringify({id:String(999999999999992200n+BigInt(sequence)),application_id:app,guild_id:guild,channel_id:guild,member:{user:{id:actor,username:'Fixture'},roles:[],permissions:'0'},version:1,token,type:3,data:{component_type:2,custom_id:'ck:roster:'+action+':'+id}});
 const response=await runtime.dispatchFetch('https://bot.local/interactions',{method:'POST',headers:{'content-type':'application/json','x-signature-timestamp':timestamp,'x-signature-ed25519':sign(null,Buffer.from(timestamp+body),privateKey).toString('hex')},body});
 assert.equal(response.status,200);
 const result=await response.json();
 if(![5,6].includes(result.type))return result;
 for(let i=0;i<100;i++){if(replies.has(token))return {type:4,data:replies.get(token)};await new Promise(r=>setTimeout(r,25));}
 throw Error('Deferred response missing');
}
function options(modal){assert.equal(modal.type,9,JSON.stringify(modal));return modal.data.components[0].component.options;}
try{
 let rows=options(await interact('join'));
 assert.equal(rows[0].emoji.id,th19.id);assert.equal(rows[0].label,'[GC] Valentine (#2PP)');
 removing=true;rows=options(await interact('leave'));
 assert.equal(rows[0].label,'[GC] Valentine (#2PP)');
 const view=await interact('view');assert.equal(view.type,4);
 assert.ok(view.data.content.includes('\\[GC\\] Valentine'));
 assert.ok(view.data.content.includes('\\[GC\\] Clan'));
 assert.deepEqual(view.data.allowed_mentions,{parse:[]});
 assert.ok(view.data.content.length<=2000);
 console.log('PASS signed roster join/leave and view: literal brackets and disabled mentions');
}finally{await runtime.dispose();}
