// Actual signed Bot Worker modal requests with a slow external emoji provider.
import assert from 'node:assert/strict';
import {generateKeyPairSync,sign} from 'node:crypto';
import {createRequire} from 'node:module';
import {bundleWorker} from './bundle-worker.mjs';
const require=createRequire(new URL('../../worker/package.json',import.meta.url));
const {Miniflare,convertV4MiniflareOptions}=require('miniflare');
const {publicKey,privateKey}=generateKeyPairSync('ed25519');
const app='999999999999992001',guild='999999999999992002',actor='999999999999992003',id='12345678-1234-4234-8234-123456789012';
const runtime=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{name:'modal-deadlines',...await bundleWorker(),compatibilityDate:'2026-09-02',compatibilityFlags:['nodejs_compat'],bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:'https://local-api.test',CLASHKING_API_TOKEN:'local-only',DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:'local-only',DISCORD_PUBLIC_KEY:publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex')},outboundService:async request=>{
 const url=new URL(request.url);
 if(url.hostname==='discord.com'&&url.pathname.endsWith('/emojis')){await new Promise(r=>setTimeout(r,4000));return Response.json({items:[]});}
 if(url.hostname==='local-api.test'){
  if(url.pathname.endsWith('/tickets/open/prepare'))return Response.json({outcome:'ready',form:{kind:'modal',customId:'sdk-modal',title:'Apply',fields:[{customId:'name',label:'Name',required:true,style:'short',maxLength:50}]}});
  if(url.pathname.endsWith('/accounts'))return Response.json({items:[{tag:'#2PP',name:'Account',townhall:18,isVerified:true,signedUp:false}],remainingSlots:1});
  if(url.pathname.endsWith('/rosters/'+id))return Response.json({roster:{id,serverId:guild,alias:'Fixture',description:null,memberCount:0,members:[],questionnaire:{questions:[]}}});
  if(url.pathname.includes('activity'))return Response.json({ok:true});
 }
 throw Error('Unexpected local provider path');
}}]}));
try{
 let seq=0;
 for(const customId of ['ck:ticket:open:'+id+':'+id,'ck:roster:join:'+id]){
  const body=JSON.stringify({id:String(999999999999992100n+BigInt(seq++)),application_id:app,guild_id:guild,channel_id:guild,member:{user:{id:actor,username:'Local'},roles:[],permissions:'0'},version:1,token:'local-only-'+seq,type:3,data:{component_type:2,custom_id:customId}});
  const timestamp=String(Math.floor(Date.now()/1000)),start=Date.now();
  const response=await runtime.dispatchFetch('http://local/interactions',{method:'POST',headers:{'content-type':'application/json','x-signature-timestamp':timestamp,'x-signature-ed25519':sign(null,Buffer.from(timestamp+body),privateKey).toString('hex')},body});
  const result=await response.json();assert.equal(result.type,9,JSON.stringify(result));assert(Date.now()-start<2500,'Modal missed its bounded acknowledgement');
 }
 console.log('PASS real signed ticket/roster modals: slow emoji provider falls back before acknowledgement deadline');
}finally{await runtime.dispose();}
