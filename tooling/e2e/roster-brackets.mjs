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
let removing=false,sequence=0,rosterLoads=0,formLoads=0,submissions=0;
const replies=new Map();
const members=[{playerTag:'#2PP',playerName:'[GC] Valentine',townhall:19,clanName:'[GC] Clan'},
  {playerTag:'#8Q8',playerName:'#8Q8',townhall:0,clanName:null},
];
const runtime=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{
 name:'roster-display',...await bundleWorker(),compatibilityDate:'2026-09-02',compatibilityFlags:['nodejs_compat'],
 bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:'https://local-api.test',CLASHKING_API_TOKEN:'local-only',DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:'local-only',DISCORD_PUBLIC_KEY:publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex')},
 outboundService:async request=>{
  const u=new URL(request.url);
  if(u.hostname==='local-api.test'){
   if(u.pathname.endsWith('/accounts'))return Response.json({items:members.map(m=>({tag:m.playerTag,name:m.playerName,townhall:m.townhall,isVerified:true,signedUp:removing})),remainingSlots:3,requireVerified:false,questionnaire:{accountSelector:{id:'account',type:'account',required:true},questions:[]}});
   if(u.pathname.endsWith('/signup-form')){formLoads++;return Response.json({accountSelector:{id:'account',type:'account',required:true},questions:[],requireVerified:false});}
   if(u.pathname.endsWith('/links/'+actor))return Response.json({items:[{player_tag:'#2PP',is_verified:true}]});
   if(u.pathname.endsWith('/submissions')){submissions++;return Response.json({submission:{id:'s1',rosterId:id,playerTag:'#2PP',answers:{},createdAt:'2026-11-22T00:00:00Z',updatedAt:'2026-11-22T00:00:00Z'}},{status:201});}
   if(u.pathname.endsWith('/rosters/'+id)){rosterLoads++;return Response.json({roster:{id,serverId:guild,alias:'[GC] Roster',description:null,memberCount:members.length,members,questionnaire:{questions:[]}}});}
   if(u.pathname.includes('activity'))return Response.json({ok:true});
  }
  if(u.hostname==='discord.com'){
   if(request.method==='GET'&&u.pathname.endsWith('/emojis'))return Response.json({items:[th19]});
   if(request.method==='PATCH'&&u.pathname.includes('/messages/@original')){replies.set(u.pathname.split('/')[5],await request.json());return Response.json({id:'999999999999992104'});}
  }
  throw Error('Unexpected provider request '+request.method+' '+u.pathname);
 }
}]}));
async function send(payload){
 const token='roster-display-'+(++sequence),timestamp=String(Math.floor(Date.now()/1000));
 const body=JSON.stringify({id:String(999999999999992200n+BigInt(sequence)),application_id:app,guild_id:guild,channel_id:guild,member:{user:{id:actor,username:'Fixture'},roles:[],permissions:'0'},version:1,token,...payload});
 const response=await runtime.dispatchFetch('https://bot.local/interactions',{method:'POST',headers:{'content-type':'application/json','x-signature-timestamp':timestamp,'x-signature-ed25519':sign(null,Buffer.from(timestamp+body),privateKey).toString('hex')},body});
 assert.equal(response.status,200);
 const result=await response.json();
 if(![5,6].includes(result.type))return result;
 for(let i=0;i<100;i++){if(replies.has(token))return {type:4,data:replies.get(token)};await new Promise(r=>setTimeout(r,25));}
 throw Error('Deferred response missing');
}
const interact=action=>send({type:3,data:{component_type:2,custom_id:'ck:roster:'+action+':'+id}});
function options(modal){assert.equal(modal.type,9,JSON.stringify(modal));return modal.data.components[0].component.options;}
try{
 const joinModal=await interact('join');
 let rows=options(joinModal);
 assert.equal(rosterLoads,0);
 assert.equal(rows[0].emoji.id,th19.id);assert.equal(rows[0].label,'[GC] Valentine (#2PP)');
 assert.equal(rows[1].label,'#8Q8');
 const submitted=await send({type:5,data:{custom_id:joinModal.data.custom_id,components:[{type:18,component:{type:3,custom_id:'player',values:['#2PP']}}]}});
 assert.equal(submitted.type,4);assert.equal(formLoads,1);assert.equal(submissions,1);assert.equal(rosterLoads,0);
 removing=true;rows=options(await interact('leave'));
 assert.equal(rosterLoads,0);
 assert.equal(rows[0].label,'[GC] Valentine (#2PP)');
 const view=await interact('view');assert.equal(view.type,4);
 assert.equal(rosterLoads,1);
 assert.ok(view.data.content.includes('\\[GC\\] Valentine'));
 assert.ok(view.data.content.includes('\\[GC\\] Clan'));
 assert.deepEqual(view.data.allowed_mentions,{parse:[]});
 assert.ok(view.data.content.length<=2000);
 console.log('PASS signed roster join/leave and view: literal brackets and disabled mentions');
}finally{await runtime.dispose();}
