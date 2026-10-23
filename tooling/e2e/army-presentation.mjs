// Actual signed bot Worker -> API Worker -> PostgreSQL. Discord is a loopback provider boundary.
import { createHmac, generateKeyPairSync, randomBytes, sign } from 'node:crypto';
import { bundleWorker } from './bundle-worker.mjs';
import { mkdtempSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawn } from 'node:child_process';

const botRoot=resolve(fileURLToPath(new URL('../../',import.meta.url)));
const apiRoot=resolve(process.env.CLASHKING_E2E_API_REPO??join(botRoot,'../clashking_api'));
const assets=resolve(process.env.CLASHKING_E2E_ASSETS_REPO??join(botRoot,'../clashking_assets'));
const appRoot=resolve(process.env.CLASHKING_E2E_APP_REPO??join(botRoot,'../../IdeaProjects/ClashKingApp'));
const require=createRequire(join(apiRoot,'package.json'));
const {Client}=require('pg'),{build}=require('esbuild'),{Miniflare,convertV4MiniflareOptions}=require('miniflare');
const database=process.env.CLASHKING_E2E_DATABASE_URL??'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev';
const dbURL=new URL(database);if(dbURL.protocol!=='postgres:'||dbURL.hostname!=='127.0.0.1'||dbURL.pathname!=='/clashking_dev')throw Error('Only owned loopback clashking_dev is allowed');
const port=Number(process.env.CLASHKING_E2E_API_PORT??8803);if(!Number.isInteger(port)||port<1024||port>65535)throw Error('Invalid loopback port');
const app='999999999999995501',author='999999999999995502',clicker='999999999999995503',unregistered='999999999999995504';
const limitUser='999999999999995505';
const limitCodes=Array.from({length:26},(_,i)=>`u${201+i}x999990`);
const canonical='h0p0e0i2x0d1x0u7x4-2x9-1x26-1x51s2x0';
const noIdentityCode=canonical.replace('u7x4','u8x4');
const futureCode='h999p999e998_999i1x999d1x999u1x999s1x999';
const portalCode='h2m1p16e5_22-4p4e6_13-6p17e35_61-7p11e52_56i1x63-1x75-1x181-1x188d4x5u3x1-53x5-2x10-2x76-1x91-1x92-1x188s1x92-2x10-2x11-3x35-1x70-1x120';
const input='https://link.clashofclans.com/en?action=CopyArmy&army='+encodeURIComponent('u1x9-7x4-1x9-1x26-1x51s2x0h0p0e0i2x0d1x0');
const db=new Client({connectionString:database});await db.connect();
const keys=Object.fromEntries(['DATA_ENCRYPTION_KEY','JWT_ACCESS_SECRET','JWT_REFRESH_SECRET','API_BOT_TOKEN','AI_USAGE_SECRET','STRIPE_WEBHOOK_SECRET'].map(key=>[key,randomBytes(32).toString('base64url')]));
const {privateKey,publicKey}=generateKeyPairSync('ed25519');const publicHex=publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex');
const directory=mkdtempSync(join(tmpdir(),'ck-army-presentation-'));
let api,bot,owns=false,baseId,logs='',counter=999999999999995600n;const responses=new Map();
const wait=async(check,label)=>{for(let i=0;i<100;i++){const value=await check();if(value)return value;await new Promise(r=>setTimeout(r,100));}throw Error(`Timeout ${label}: ${logs.slice(-2000)}`);};
try{
 if((await db.query('SELECT user_id FROM auth_users WHERE user_id=ANY($1::text[])',[[author,clicker,unregistered,limitUser]])).rowCount)throw Error('Synthetic users already exist');
 if((await db.query('SELECT share_code FROM army_compositions WHERE share_code=ANY($1::text[])',[[canonical,noIdentityCode,futureCode,...limitCodes]])).rowCount)throw Error('Synthetic army already exists');
 await db.query("INSERT INTO auth_users(user_id,provider) VALUES($1,'discord'),($2,'discord'),($3,'discord')",[author,clicker,limitUser]);owns=true;
 const env={PATH:process.env.PATH,HOME:process.env.HOME,TMPDIR:process.env.TMPDIR,CLASHKING_PERSISTENT_LOCAL_API:'1',CLASHKING_LOCAL_DATABASE_URL:database,CLASHKING_LOCAL_API_PORT:String(port),CLASHKING_LOCAL_DISCORD_CLIENT_ID:app,CLASHKING_LOCAL_DISCORD_CLIENT_SECRET:'local-only',CLASHKING_LOCAL_DISCORD_PUBLIC_KEY:publicHex,CLASHKING_LOCAL_ARCHIVE_BRIDGE:'0',CLASHKING_LOCAL_CLASH_PROXY_ORIGIN:'http://127.0.0.1:65534',CLASHKING_LOCAL_STATIC_ASSETS_ROOT:join(assets,'assets/static_data'),CLASHKING_LOCAL_STORAGE_ROOT:join(directory,'storage'),...Object.fromEntries(Object.entries(keys).map(([key,value])=>[`CLASHKING_LOCAL_${key}`,value]))};
 api=spawn(process.execPath,['scripts/start-local-rewrite-api.mjs'],{cwd:apiRoot,env,stdio:['ignore','pipe','pipe']});api.stdout.on('data',v=>logs+=v);api.stderr.on('data',v=>logs+=v);
 await wait(async()=>{try{return logs.includes('local_static_assets_seeded')&&(await fetch(`http://127.0.0.1:${port}/v2/health`)).ok;}catch{return false;}},'API and static assets startup');
 const bundle=await bundleWorker();
 bot=new Miniflare(convertV4MiniflareOptions({host:'127.0.0.1',port:0,workers:[{name:'army-presentation-e2e',...bundle,compatibilityDate:'2026-08-22',compatibilityFlags:['nodejs_compat'],
 bindings:{APP_ENV:'dev',LOCAL_TEST_USER_ID:'',DASHBOARD_BASE_URL:'https://dash.clashk.ing',CLASHKING_API_BASE_URL:`http://127.0.0.1:${port}`,CLASHKING_API_TOKEN:keys.API_BOT_TOKEN,DISCORD_APPLICATION_ID:app,DISCORD_BOT_TOKEN:`${Buffer.from(app).toString('base64')}.local.token`,DISCORD_PUBLIC_KEY:publicHex},
 outboundService:async request=>{const url=new URL(request.url);
  if(url.hostname==='discord.com'){
   if(request.method==='GET'&&url.pathname.endsWith('/emojis'))return Response.json({items:['pekka','wallbreaker','wallwrecker','lightningspell','barbarian','barbarianking','barbarianpuppet','lassi','th14'].map((name,i)=>({name,id:String(999999999999995700n+BigInt(i)),animated:false}))});
   if(!url.pathname.includes('/webhooks/'))throw Error('Unexpected Discord route');
   responses.set(url.pathname.split('/')[5],await request.json());return Response.json({id:'999999999999995999'});
  }
  if(url.hostname==='127.0.0.1'&&url.port===String(port)){const response=await fetch(request.url,{method:request.method,headers:Object.fromEntries(request.headers),body:['GET','HEAD'].includes(request.method)?undefined:await request.arrayBuffer()});if(!response.ok)logs+=await response.clone().text();return response;}
  throw Error('External network blocked');
 }}]}));
 const origin=new URL('/interactions',String(await bot.ready));
 async function interact(data,actor=author){const token=String(counter++),rawBody=JSON.stringify({id:token,application_id:app,guild_id:'999999999999995510',channel_id:'999999999999995511',member:{user:{id:actor,username:'Local'},roles:[]},version:1,token,...data});const timestamp=String(Math.floor(Date.now()/1000));const r=await fetch(origin,{method:'POST',headers:{'Content-Type':'application/json','X-Signature-Timestamp':timestamp,'X-Signature-Ed25519':sign(null,Buffer.from(timestamp+rawBody),privateKey).toString('hex')},body:rawBody});const initial=await r.json();if(r.status!==200)throw Error(`Bot HTTP${r.status}`);return {initial,result:[5,6].includes(initial.type)?await wait(()=>responses.get(token),'deferred reply'):initial.data};}
 const command=(army,extra=[])=>({type:2,data:{name:'army',options:[{name:'link',type:1,options:[{name:'army',type:3,value:army},...(!extra.some(option=>option.name==='nickname')?[{name:'nickname',type:3,value:'Army Link Results'}]:[]),...extra]}]}});
 const preview=(await interact(command(input))).result;
 const text=JSON.stringify(preview),embed=preview.embeds?.[0],buttons=preview.components?.[0]?.components;
 if(embed?.title!=='Army Link Results'||text.includes('Saved armies')||embed.description.includes(canonical))throw Error('Old-style title/raw-code/library-link regression: '+text+' '+logs.slice(-3000));
 for(const name of ['Troops','Super Troops','Spells','Siege Machines','Heroes Loadout','Clan Castle'])if(!embed.fields.some(f=>f.name===name))throw Error(`Missing old-style ${name}`);
 if(!text.includes('P.E.K.K.A')||!text.includes('pekka:')||!text.includes('x 2')||!text.includes('Barbarian Puppet')||!text.includes('L.A.S.S.I'))throw Error('Named emoji/quantity/loadout missing: '+text);
 if(embed.fields.some(f=>f.value.length>1024)||buttons.length!==2||buttons[0].label!=='Copy Army'||buttons[1].label!=='Save Army'||buttons[1].style!==3)throw Error('Invalid fields/actions');
 if((await db.query('SELECT share_code FROM army_compositions WHERE share_code=$1',[canonical])).rowCount)throw Error('Viewing auto-registered composition');
 if((await db.query('SELECT * FROM user_saved_armies WHERE user_id=ANY($1::text[])',[[author,clicker]])).rowCount)throw Error('Viewing auto-saved');
 if(!embed.description.includes('Minimum Townhall ')||embed.description.includes('unit unlock'))throw Error('Townhall copy did not match request');
 const named=(await interact(command(input,[{name:'nickname',type:3,value:'My Smash'},{name:'notes',type:3,value:'Use the Warden late.'}]))).result;
 if(named.embeds[0].title!=='My Smash'||!named.embeds[0].fields.some(f=>f.name==='Notes'&&f.value==='Use the Warden late.'))throw Error('Nickname/notes missing');
 const message={id:'999999999999995999',author:{id:app},components:named.components,embeds:named.embeds};
 const component={type:3,data:{component_type:2,custom_id:buttons[1].custom_id},message};
 const save=await interact(component,clicker);if(save.initial.data.flags!==64||!save.result.content.includes('Saved to your'))throw Error('Save must privately confirm: '+JSON.stringify(save)+' '+logs.slice(-3000));
 const saved=(await db.query('SELECT user_id,share_code FROM user_saved_armies WHERE user_id=ANY($1::text[])',[[author,clicker]])).rows;
 if(saved.length!==1||saved[0].user_id!==clicker||saved[0].share_code!==canonical)throw Error('Save did not target clicking actor');
 const labels=(await db.query('SELECT name,notes,saved_at FROM user_saved_armies WHERE user_id=$1',[clicker])).rows[0];
 if(labels.name!=='My Smash'||labels.notes!=='Use the Warden late.')throw Error('Personal name and notes not retained');
 const share={type:2,data:{name:'army',options:[{name:'share',type:1}]}};
 const modal=await interact(share,clicker),select=modal.initial.data?.components?.[0]?.component;
 if(modal.initial.type!==9||select?.type!==3||select.options[0].label!=='My Smash'||!/^Saved \d{4}-\d{2}-\d{2}$/.test(select.options[0].description)||!select.options[0].emoji?.name.startsWith('th'))throw Error('Share must open clean named/Townhall modal: '+JSON.stringify(modal));
 const submit={type:5,data:{custom_id:modal.initial.data.custom_id,components:[{type:18,component:{type:3,custom_id:'army',values:[select.options[0].value]}}]}};
 const shared=await interact(submit,clicker);
 if(shared.initial.type!==5||shared.initial.data?.flags===64||shared.result.embeds?.[0]?.title!=='My Smash')throw Error('Modal submit must post named public army');
 if((await interact(submit,author)).result.embeds)throw Error('Cross-user modal accepted');
 const missing=await interact({type:2,data:{name:'army',options:[{name:'link',type:1}]}},clicker);
 if(!missing.result.content.includes('required'))throw Error('Missing required army accepted');
 for(const options of [[{name:'army',type:3,value:canonical}], [{name:'army',type:3,value:canonical},{name:'nickname',type:3,value:'   '}]]){
   const reply=await interact({type:2,data:{name:'army',options:[{name:'link',type:1,options}]}},clicker);
   if(!reply.result.content.includes('nickname is required'))throw Error('Missing/blank nickname accepted');
 }
 const obsolete=await interact({type:2,data:{name:'army',options:[{name:'share',type:1,options:[{name:'army',type:3,value:canonical}]}]}},clicker);
 if(!JSON.stringify(obsolete).includes('does not accept options'))throw Error('Share still accepts a link');
 // Run the real App service/client over HTTP, not a fake ContractApiService.
 const appBundle=join(directory,'app-army-service.mjs');
 await build({stdin:{contents:`import {PersonalArmiesService} from ${JSON.stringify(join(appRoot,'expo/src/features/bases-armies/personal-armies-service.ts'))}; import {PersonalBasesService} from ${JSON.stringify(join(appRoot,'expo/src/features/bases-armies/personal-bases-service.ts'))}; import {createAppContractClient} from ${JSON.stringify(join(appRoot,'expo/src/core/api/app-contract-client.ts'))}; import {AppConfigEndpoint,PersonalArmiesEndpoint} from '@clashking/api-contracts/expo'; import {Effect} from 'effect'; import {createApiClient,httpTransport} from '@clashking/api-client'; const client=(baseUrl,bearerToken)=>createApiClient({baseUrl,auth:{bearerToken},transport:httpTransport()}); export const library=(baseUrl,bearerToken)=>new PersonalArmiesService(client(baseUrl,bearerToken)); export const bases=(baseUrl,bearerToken)=>new PersonalBasesService(client(baseUrl,bearerToken),baseUrl+'/v2'); export async function credentials(baseUrl,bearerToken){const seen=[];const api=createAppContractClient({baseUrl,web:true,transport:httpTransport(request=>{seen.push(request.credentials);return fetch(request)})});await Effect.runPromise(api.execute(AppConfigEndpoint,{path:{},query:{},body:{}}));await Effect.runPromise(api.execute(PersonalArmiesEndpoint,{path:{},query:{},body:{}},{auth:{bearerToken}}));return seen;}`,resolveDir:join(appRoot,'expo')},bundle:true,platform:'node',format:'esm',target:'node24',outfile:appBundle});
 const {library,bases,credentials}=await import(pathToFileURL(appBundle).href);
 const tokenFor=sub=>{const now=Math.floor(Date.now()/1000),parts=[{alg:'HS256',typ:'JWT'},{sub,aud:'clashking-native',iat:now,exp:now+600}].map(value=>Buffer.from(JSON.stringify(value)).toString('base64url'));return parts.join('.')+'.'+createHmac('sha256',keys.JWT_ACCESS_SECRET).update(parts.join('.')).digest('base64url');};
 const personal=library(`http://127.0.0.1:${port}`,tokenFor(clicker));
 const modes=await credentials(`http://127.0.0.1:${port}`,tokenFor(clicker));
 if(modes.join(',')!=='omit,include')throw Error('Public and authenticated request credential modes are incorrect');
 baseId=(await db.query("INSERT INTO bases(base_link,message_id,server_id,channel_id) VALUES('https://link.clashofclans.com/en?action=OpenLayout&id=TH18:HV:LOCAL', '999999999999995901','999999999999995902','999999999999995903') RETURNING id::text")).rows[0].id;
 const baseLibrary=bases(`http://127.0.0.1:${port}`,tokenFor(clicker));
 const downloadBase=async(user=clicker)=>{const response=await fetch(`http://127.0.0.1:${port}/v2/bases/${baseId}/downloaders/${user}`,{method:'POST',headers:{Authorization:`Bearer ${keys.API_BOT_TOKEN}`}});if(!response.ok)throw Error('Bot base download failed: '+await response.text());};
 await downloadBase();
 await downloadBase(author);
 if(!(await baseLibrary.load()).items.some(item=>item.id===baseId&&item.saved))throw Error('Discord download did not enter personal library');
 if((await baseLibrary.unsave(baseId).catch(cause=>{throw new Error('Single base removal failed',{cause})})).items.some(item=>item.id===baseId)||(await baseLibrary.load()).items.some(item=>item.id===baseId))throw Error('Unbookmarked downloaded base reappeared');
 const afterRemoval=(await db.query('SELECT downloads ? $2::text AS removed_user,downloads ? $3::text AS other_user FROM bases WHERE id=$1',[baseId,clicker,author])).rows[0];
 if(afterRemoval.removed_user||!afterRemoval.other_user)throw Error('Unbookmark must remove only the current user download entry');
 const otherBases=bases(`http://127.0.0.1:${port}`,tokenFor(author));
 if(!(await otherBases.load()).items.some(item=>item.id===baseId&&item.downloadCount===1))throw Error('Unbookmark changed another user library or retained the removed download count');
 await downloadBase();if(!(await baseLibrary.load()).items.some(item=>item.id===baseId))throw Error('Explicit re-download did not restore bookmark');
 await db.query("UPDATE user_saved_bases SET saved_at=now()-interval '91 days' WHERE user_id=$1 AND base_id=$2",[clicker,baseId]);
 if((await baseLibrary.deleteOld().catch(cause=>{throw new Error('Bulk base removal failed',{cause})})).items.some(item=>item.id===baseId))throw Error('Bulk removal retained an old base');
 const afterBulkRemoval=(await db.query('SELECT downloads ? $2::text AS removed_user,downloads ? $3::text AS other_user FROM bases WHERE id=$1',[baseId,clicker,author])).rows[0];
 if(afterBulkRemoval.removed_user||!afterBulkRemoval.other_user)throw Error('Bulk removal must clear only the current user download history');
 const appBefore=await personal.load();
 if(appBefore.items[0].name!=='My Smash'||appBefore.items[0].minimumTownHall!==14)throw Error('App service lost name or Town Hall');
 const edited=await personal.update(canonical,{name:'Edited in App',notes:'New app notes'});
 if(edited.items[0].name!=='Edited in App'||edited.items[0].notes!=='New app notes'||edited.items[0].savedAt!==appBefore.items[0].savedAt)throw Error('App edit did not preserve saved timestamp');
 const otherLibrary=library(`http://127.0.0.1:${port}`,tokenFor(author));
 let forbiddenEdit=false;try{await otherLibrary.update(canonical,{name:'Not mine',notes:null});}catch{forbiddenEdit=true;}if(!forbiddenEdit)throw Error('App edited another user library');
 const stored=(await db.query('SELECT main_troops,spells,heroes,equipment,pet_assignments,siege_machine_id FROM army_compositions WHERE share_code=$1',[canonical])).rows[0];
 if(!stored.main_troops.some(u=>u.id===4000009&&u.quantity===2)||stored.siege_machine_id!==4000051||stored.spells.length!==2||stored.heroes[0]!==28000000||stored.pet_assignments[0].petId!==73000000)throw Error('Canonical composition did not preserve loadout');
 await interact(component,clicker);if((await db.query('SELECT * FROM user_saved_armies WHERE user_id=$1',[clicker])).rowCount!==1)throw Error('Repeated save duplicated row');
 for(const denied of [{...component,message:{...message,author:{id:author}}},{...component,data:{...component.data,custom_id:'ck:army:save:'+'0'.repeat(64)}}]){const r=(await interact(denied,author)).result;if(r.content.includes('Saved to your'))throw Error('Invalid signed message was accepted');}
 if((await db.query('SELECT * FROM user_saved_armies WHERE user_id=$1',[author])).rowCount)throw Error('Rejected click saved to original author');
 const unlinked=(await interact(component,unregistered)).result;if(!unlinked.content.includes('Sign in'))throw Error('Missing app identity should require sign-in');
 const noIdentityPreview=(await interact(command(noIdentityCode),unregistered)).result;if(noIdentityPreview.embeds?.[0]?.title!=='Army Link Results')throw Error('Viewing must not require app identity');
 const noIdentitySave={type:3,data:{component_type:2,custom_id:noIdentityPreview.components[0].components[1].custom_id},message:{...message,components:noIdentityPreview.components}};
 if(!(await interact(noIdentitySave,unregistered)).result.content.includes('Sign in'))throw Error('Unregistered Save needs clear sign-in error');
 if((await db.query('SELECT share_code FROM army_compositions WHERE share_code=$1',[noIdentityCode])).rowCount)throw Error('Failed identity left orphan composition');
 const long=(await interact(command('u'+Array.from({length:150},(_,i)=>`1x${i}`).join('-')))).result;
 if(!long.content.includes('512'))throw Error('Long Copy Army URL needs clear length rejection');
 const portal=(await interact(command(portalCode))).result;
 if(!JSON.stringify(portal).includes('Portal Pendant')||!portal.embeds)throw Error('Portal Pendant must resolve from local assets: '+JSON.stringify(portal));
 // Future metadata must not destroy copy/save data or bypass known validation.
 const future=(await interact(command(futureCode))).result, futureText=JSON.stringify(future);
 for(const label of ['Unknown hero (28000999)','Unknown pet (73000999)','Unknown equipment (90000998)','Unknown troop (4000999)','Unknown spell (26000999)','Known items only'])if(!futureText.includes(label))throw Error('Missing future-ID placeholder or incomplete metrics: '+label+' '+futureText);
 if(!future.components[0].components[0].url.includes(encodeURIComponent(futureCode)))throw Error('Copy link lost unknown IDs');
 const futureSave={type:3,data:{component_type:2,custom_id:future.components[0].components[1].custom_id},message:{...message,components:future.components}};
 if(!(await interact(futureSave,clicker)).result.content.includes('Saved to your'))throw Error('Unknown IDs must remain saveable');
 const futureStored=(await db.query('SELECT main_troops,equipment,heroes,pet_assignments FROM army_compositions WHERE share_code=$1',[futureCode])).rows[0];
 if(futureStored?.main_troops[0]?.id!==4000999||futureStored.equipment[0]?.equipmentId!==90000998||futureStored.heroes[0]!==28000999||futureStored.pet_assignments[0]?.petId!==73000999)throw Error('Save lost unknown IDs');
 for(const invalid of ['u1x2147483647','s1001x0','h0-0u1x0','h0e4u1x0','h0e999_999u1x0']){if((await interact(command(invalid))).result.embeds)throw Error('Invalid composition preview was accepted');}
 for(const [i,code]of limitCodes.entries())await db.query('INSERT INTO army_compositions(share_code,main_troops) VALUES($1,$2::jsonb)',[code,JSON.stringify([{id:4999990,quantity:201+i}])]);
 for(const code of limitCodes.slice(0,24))await db.query('INSERT INTO user_saved_armies(user_id,share_code) VALUES($1,$2)',[limitUser,code]);
 const capped=library(`http://127.0.0.1:${port}`,tokenFor(limitUser));
 const contenders=await Promise.allSettled(limitCodes.slice(24).map(code=>capped.save(code)));
 if(contenders.filter(result=>result.status==='fulfilled').length!==1||(await capped.load()).items.length!==25)throw Error('Concurrent saves exceeded 25');
 if((await capped.save(limitCodes[0])).items.length!==25)throw Error('Resaving at cap must work');
 console.log(JSON.stringify({checks:['required army and nonblank nickname; share has no options','nickname and notes saved per clicking user','real App service loads Town Hall and edits owned metadata without changing saved date','App cannot edit another user save','concurrent new saves capped at 25; existing save allowed at cap','clean Townhall label','share opens modal with name/date/Townhall icon','modal submit posts public named army; cross-user denied','old grouped fields and named emojis','copy and green Save only','link preview has no database side effects','Save belongs to clicking user not author','repeat Save idempotent','wrong message author and mismatched hash denied','unregistered viewer allowed; failed Save leaves no orphan composition','512-character Copy URL limit','Portal Pendant from local metadata','unknown IDs display placeholders and survive Copy and Save','oversized IDs/quantities, duplicate heroes/equipment and wrong known equipment denied'],presentation:{title:embed.title,fields:embed.fields.map(f=>f.name),footer:embed.footer.text},discordNetworkWrites:0}));
}finally{
 if(bot)await bot.dispose().catch(()=>{});if(api&&api.exitCode===null){api.kill('SIGTERM');await Promise.race([new Promise(r=>api.once('exit',r)),new Promise(r=>setTimeout(r,5000))]);}
 if(baseId)await db.query('DELETE FROM bases WHERE id=$1',[baseId]);
 if(owns){await db.query('DELETE FROM auth_users WHERE user_id=ANY($1::text[])',[[author,clicker,limitUser]]);await db.query('DELETE FROM army_compositions WHERE share_code=ANY($1::text[])',[[canonical,noIdentityCode,futureCode,...limitCodes]]);}await db.end();
}
