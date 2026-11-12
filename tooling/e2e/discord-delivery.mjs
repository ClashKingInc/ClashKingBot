import {createServer} from 'node:http';
import {randomUUID,randomBytes} from 'node:crypto';
import {mkdtempSync,readFileSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {connect} from 'node:net';
import {spawn,execFileSync} from 'node:child_process';
const botRoot=resolve(fileURLToPath(new URL('../../',import.meta.url)));
const apiRoot=resolve(process.env.CLASHKING_E2E_API_REPO??join(botRoot,'../clashking_api'));
const trackingRoot=resolve(process.env.CLASHKING_E2E_TRACKING_REPO??join(botRoot,'../clashking_tracking'));
const pg=createRequire(join(apiRoot,'package.json'))('pg');
const directory=mkdtempSync(join(tmpdir(),'ck-delivery-e2e-'));
const database=process.env.TEST_DATABASE_URL??process.env.CLASHKING_E2E_DATABASE_URL??'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev';
const databaseURL=new URL(database);if(databaseURL.protocol!=='postgres:'||databaseURL.hostname!=='127.0.0.1'||(databaseURL.pathname!=='/clashking_dev'&&process.env.CLASHKING_DISPOSABLE_TIMESCALE!=='1'))throw Error('Only owned loopback clashking_dev is allowed');
const workspace={env:{VALKEY_PORT:process.env.VALKEY_PORT??process.env.CLASHKING_E2E_VALKEY_PORT??'6379',VALKEY_PASSWORD:process.env.CLASHKING_E2E_VALKEY_PASSWORD??'',DATA_ENCRYPTION_KEY:randomBytes(32).toString('base64url')}};
if(!/^\d{1,5}$/.test(workspace.env.VALKEY_PORT))throw Error('Invalid loopback Valkey port');
const db=new pg.Client({connectionString:database});await db.connect();
const app='999999999999997501',guild='999999999999997502',channel='999999999999997503',hook='999999999999997504';
const donationHook='999999999999997505';
const stream='ck:e2e:delivery:'+randomUUID(),snapshot='ck:e2e:snapshot:clan:#P0Y';
const config=JSON.parse(readFileSync(join(trackingRoot,'config.json'),'utf8'));
config.dry_run=false;config.mock_db=false;config.events={...config.events,stream,consumer:'isolated-e2e',retention_seconds:300};
config.trackedclans={...config.trackedclans,snapshot_prefix:'ck:e2e:snapshot:'};
writeFileSync(join(directory,'config.json'),JSON.stringify(config));
const recipients=['999999999999997801','999999999999997802'];
async function redis(...args){return new Promise((resolve,reject)=>{
 const socket=connect({host:'127.0.0.1',port:Number(workspace.env.VALKEY_PORT||6379)});let result='';socket.on('error',reject);
 socket.on('connect',()=>{const commands=workspace.env.VALKEY_PASSWORD?[['AUTH',workspace.env.VALKEY_PASSWORD],args]:[args];socket.write(Buffer.concat(commands.flatMap(a=>[Buffer.from('*'+a.length+'\r\n'),...a.flatMap(x=>{const data=Buffer.isBuffer(x)?x:Buffer.from(String(x));return [Buffer.from('$'+data.length+'\r\n'),data,Buffer.from('\r\n')];})])));});
 socket.on('data',data=>{result+=data;const parts=result.split('\r\n').filter(Boolean);if(parts.some(x=>x.startsWith('-'))){socket.destroy();reject(Error('Local Valkey request failed'));return;}if(parts.filter(x=>/^[+:$]/.test(x)).length>=(workspace.env.VALKEY_PASSWORD?2:1)){socket.end();resolve(result);}});
});}
const calls=[];let message=999999999999997600n,lockedWelcome=false;
const provider=createServer(async(req,res)=>{let body='';for await(const chunk of req)body+=chunk;const path=new URL(req.url,'http://local');const data=body?JSON.parse(body):undefined;calls.push({method:req.method,path:path.pathname,data});res.setHeader('Content-Type','application/json');
 if(req.method==='GET'&&decodeURIComponent(path.pathname)==='/v1/clans/#P0Y')return res.end(JSON.stringify({tag:'#P0Y',name:'Farming E2E',memberList:[{tag:'#P0YQ',name:'First',townHallLevel:16},{tag:'#P0YG',name:'Second',townHallLevel:16}]}));
 if(req.method==='GET'&&path.pathname.startsWith('/channels/'))return res.end(JSON.stringify({id:path.pathname.split('/').at(-1),guild_id:guild,name:'Welcome',type:path.pathname.endsWith('506')?11:0,parent_id:channel,...(path.pathname.endsWith('506')?{thread_metadata:{locked:lockedWelcome,archived:false,auto_archive_duration:1440,archive_timestamp:new Date().toISOString()}}:{})}));
 if(req.method==='GET'&&path.pathname.endsWith('/emojis'))return res.end(JSON.stringify({items:['th16','up_green_arrow','down_red_arrow','refresh','green_check','calendar'].map((name,i)=>({id:String(999999999999997700n+BigInt(i)),name,animated:false}))}));
 if(req.method==='GET'&&path.pathname.includes('/webhooks/'))return res.end(JSON.stringify({id:path.pathname.split('/').at(-1),type:1,guild_id:guild,channel_id:channel,user:{id:app},token:'local-webhook'}));
 if(req.method==='POST'||req.method==='PATCH')return res.end(JSON.stringify({id:String(message++),channel_id:channel,content:data?.content??'',embeds:data?.embeds??[]}));
 res.statusCode=404;res.end(JSON.stringify({code:10003,message:'Local route not found'}));
});await new Promise(r=>provider.listen(0,'127.0.0.1',r));const port=provider.address().port;
let worker,logs='',ownsRecords=false,ownsSnapshot=false,ownsFarming=false,ownsClan=false;const boardIDs=[];let reminderID;
const wait=async(check,label)=>{for(let i=0;i<100;i++){if(await check())return;await new Promise(r=>setTimeout(r,200));}throw Error('Timed out: '+label+' '+logs.slice(-2500));};
const publish=async(value)=>redis('XADD',stream,'*','topic',value.type==='all_member_donations'?'clan':value.type==='member_join'?'discord_member_join':'reminder','clan_tag','#P0Y','timestamp',new Date().toISOString(),'value',JSON.stringify(value));
try{
 if((await db.query('SELECT id FROM servers WHERE id=$1',[guild])).rowCount)throw Error('Synthetic server already exists');
 if((await db.query('SELECT user_id FROM auth_users WHERE user_id=ANY($1::text[])',[recipients])).rowCount)throw Error('Synthetic users already exist');
 if((await db.query('SELECT application_id FROM discord_cache.gateway_shards WHERE application_id=$1',[app])).rowCount)throw Error('Synthetic gateway already exists');
 if(!(await redis('EXISTS',snapshot)).endsWith(':0\r\n'))throw Error('Synthetic snapshot already exists');
 await db.query('INSERT INTO servers(id,name,family_label) VALUES($1,$2,$2)',[guild,'E2E Donors']);ownsRecords=true;
 for(const mode of ['refresh','send']){const row=(await db.query(`WITH board AS (INSERT INTO autoboards(server_id,board_type,target_scope,delivery_mode,webhook_id,enabled,interval_minutes,schedule_kind,schedule_time,row_limit,next_run_at) VALUES($1,'donations','custom',$2,$3,true,$4,$5,$6,2,now()-interval '1 second') RETURNING id), target AS (INSERT INTO autoboard_targets(autoboard_id,position,target) SELECT id,0,'#P0Y' FROM board) SELECT id FROM board`,[guild,mode,hook,mode==='refresh'?1:null,mode==='send'?'daily':null,mode==='send'?'09:00':null])).rows[0];boardIDs.push(row.id);}
 reminderID=(await db.query(`INSERT INTO reminders(server_id,type,clan_tag,webhook_token,minutes_remaining,type_name,channel_id,webhook_id) VALUES($1,1,'#P0Y','',15,'Clan Capital',$2,$3) RETURNING id`,[guild,channel,donationHook])).rows[0].id;
 const snapshotJSON=Buffer.from(JSON.stringify({tag:'#P0Y',name:'Snapshot Clan',memberList:[{tag:'#P0Y1',name:'First',townHallLevel:16,donations:123456,donationsReceived:2345},{tag:'#P0Y2',name:'Second',townHallLevel:16,donations:70000,donationsReceived:99},{tag:'#P0Y3',name:'Third',townHallLevel:16,donations:1,donationsReceived:1}]}));
 let size=snapshotJSON.length;const header=[];do{const next=size&127;size>>>=7;header.push(next|(size?128:0));}while(size);
 const length=snapshotJSON.length-1,bytes=length<256?1:2;header.push((59+bytes)<<2,length&255);if(bytes===2)header.push(length>>8);
 await redis('SET',snapshot,Buffer.concat([Buffer.from(header),snapshotJSON]));
 ownsSnapshot=true;
 execFileSync('go',['build','-o',directory+'/tracking','.'],{cwd:trackingRoot,stdio:'pipe'});
 const env={PATH:process.env.PATH,TIMESCALE_HOST:'127.0.0.1',TIMESCALE_PORT:databaseURL.port||'5432',TIMESCALE_DATABASE:databaseURL.pathname.slice(1),TIMESCALE_USERNAME:decodeURIComponent(databaseURL.username),TIMESCALE_PASSWORD:decodeURIComponent(databaseURL.password),TIMESCALE_SSLMODE:'disable',VALKEY_HOST:'127.0.0.1',VALKEY_PORT:workspace.env.VALKEY_PORT,VALKEY_PASSWORD:workspace.env.VALKEY_PASSWORD,DISCORD_BOT_TOKEN:Buffer.from(app).toString('base64')+'.local.token',DISCORD_GUILD_ALLOWLIST:guild,DISCORD_MESSAGE_CREATE_ENABLED:'false',CLASHKING_LOCAL_DISCORD_API_URL:`http://127.0.0.1:${port}`,CLASHKING_PROXY_INTERNAL_ORIGIN:`http://127.0.0.1:${port}`,CLASHKING_API_ORIGIN:`http://127.0.0.1:${port}`,CLASHKING_API_TOKEN:'isolated-local-token',DATA_ENCRYPTION_KEY:workspace.env.DATA_ENCRYPTION_KEY};
 worker=spawn(directory+'/tracking',['--script','discord-delivery'],{cwd:directory,env,stdio:['ignore','pipe','pipe']});worker.stdout.on('data',b=>logs+=b);worker.stderr.on('data',b=>logs+=b);
 const posts=()=>calls.filter(c=>c.method==='POST'&&c.path.includes('/webhooks/')&&!c.path.includes(donationHook));
 const edits=()=>calls.filter(c=>c.method==='PATCH'&&c.path.includes('/webhooks/')&&!c.path.includes(donationHook));
 await wait(()=>posts().length===2,'initial refresh and daily sends');
 const first=posts()[0].data;const text=JSON.stringify(first);if(!text.includes('123.5K')||!text.includes('Snapshot Clan')||text.includes('Third')||!text.includes('up_green_arrow'))throw Error('Snapshot baseline, identity, row limit or emoji rendering failed');
 await db.query("UPDATE autoboards SET last_run_at=now()-interval '2 minutes' WHERE id=$1",[boardIDs[0]]);
 await publish({type:'all_member_donations'});await publish({type:'all_member_donations'});
 await wait(()=>edits().length===1,'coalesced edit');if(posts().length!==2)throw Error('Refresh created duplicate message');
 await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES('#P0Y','Donation Clan',true,0,3,'',0,0)");ownsClan=true;
 await db.query("INSERT INTO server_clans(server_id,tag) VALUES($1,'#P0Y')",[guild]);
 // The same event must still dirty donation boards and independently deliver
 // the legacy clan log. The isolated Discord provider only captures HTTP.
 await db.query("INSERT INTO server_logs(server_id,clan_tag,type,webhook_id) VALUES($1,'#P0Y','donation_log',$2)",[guild,donationHook]);
 const donationPosts=()=>calls.filter(c=>c.method==='POST'&&c.path.includes('/webhooks/'+donationHook+'/'));
 const donationEvent={type:'all_member_donations',clan:{tag:'#P0Y',name:'Donation Clan',badgeUrls:{large:'https://example.invalid/badge.png'}},donations:[{member:{tag:'#P0Y1',name:'Donor'},donated:25,received:0},{member:{tag:'#P0Y2',name:'Receiver'},donated:0,received:8},{member:{tag:'#P0Y3',name:'Reset'},donated:-5,received:0}]};
 await publish(donationEvent);await wait(()=>donationPosts().length===1,'donation log webhook');
 const donationEmbed=donationPosts()[0].data.embeds[0];
 if(!donationEmbed.description.includes('[**Donation Clan**]')||!donationEmbed.description.includes('OpenClanProfile')||donationEmbed.thumbnail?.url!=='https://example.invalid/badge.png'||donationEmbed.fields.length!==2||donationEmbed.fields[0].name!=='Donated'||donationEmbed.fields[1].name!=='Received'||donationEmbed.fields.some(f=>f.inline)||!donationEmbed.fields[0].value.includes('up_green_arrow')||!donationEmbed.fields[1].value.includes('down_red_arrow')||!donationEmbed.fields[0].value.includes('25 ')||JSON.stringify(donationEmbed).includes('Reset'))throw Error('Legacy donation log layout/deltas failed: '+JSON.stringify(donationEmbed));
 await publish({...donationEvent,donations:[]});await new Promise(r=>setTimeout(r,1200));if(donationPosts().length!==1)throw Error('Empty donation log sent');
 await db.query("UPDATE server_logs SET disabled=true WHERE server_id=$1 AND type='donation_log'",[guild]);
 await publish(donationEvent);await new Promise(r=>setTimeout(r,1200));if(donationPosts().length!==1)throw Error('Paused donation log sent');
 await db.query("DELETE FROM server_logs WHERE server_id=$1 AND type='donation_log'",[guild]);
 // Exercise the actual farming worker against persisted attacks and loopback
 // Discord. These isolated rows are rolled back/removed in the cleanup below.
 if((await db.query("SELECT 1 FROM battles_farming WHERE player_tag IN ('#P0YQ','#P0YG') LIMIT 1")).rowCount)throw Error('Synthetic farming tags already have data');
 ownsFarming=true;
 await db.query(`INSERT INTO battles_farming(player_tag,battle_time,stars,destruction_percentage,duration_seconds,looted_resources)
 VALUES('#P0YQ',now()-interval '10 minutes',3,100,60,'{"gold":1000000,"elixir":2000000,"darkElixir":1000}'),
 ('#P0YQ',now()-interval '8 minutes',3,100,60,'{"gold":1000000,"elixir":2000000,"darkElixir":1000}'),
 ('#P0YG',now()-interval '9 minutes',2,80,0,'{"gold":100000,"elixir":100000,"darkElixir":100}')`);
 const farmingID=(await db.query(`WITH board AS (INSERT INTO autoboards(server_id,board_type,target_scope,delivery_mode,webhook_id,enabled,interval_seconds,row_limit,next_run_at)
 VALUES($1,'farming','custom','refresh',$2,true,30,5,now()-interval '1 second') RETURNING id), target AS (
 INSERT INTO autoboard_targets(autoboard_id,position,target) SELECT id,0,'#P0Y' FROM board) SELECT id FROM board`,[guild,hook])).rows[0].id;
 boardIDs.push(farmingID);
 await db.query("INSERT INTO autoboard_farming_settings(autoboard_id,counting_from) VALUES($1,now()-interval '1 hour')",[farmingID]);
 await wait(()=>posts().length===3,'farming initial publication');
 const farm=posts()[2].data.embeds[0];
 if(farm.title!=='Farming E2E · Top Looters'||farm.fields.length!==2||farm.fields.some(f=>f.inline)||!farm.fields[0].value.includes('6M')||!farm.fields[0].value.includes('2M')||!farm.fields[0].value.includes('4M')||!farm.fields[0].value.includes('3m 0s')||!farm.fields[1].value.includes('Unavailable')||farm.image)throw Error('Farming calculation/layout/coverage failed: '+JSON.stringify(farm));
 await db.query("UPDATE autoboards SET next_run_at=now()-interval '1 second' WHERE id=$1",[farmingID]);
 await wait(()=>edits().length===2,'farming edit-in-place');
 if(posts().length!==3)throw Error('Farming refresh created another message');
 const stored=(await db.query('SELECT extract(epoch FROM next_run_at-last_run_at)::int AS delay FROM autoboards WHERE id=$1',[farmingID])).rows[0];
 if(stored.delay!==30)throw Error('Farming periodic cadence was not retained');
 const reminder={id:reminderID,server_id:guild,channel_id:channel,minutes_remaining:15,custom_text:''};
 const raid={state:'ongoing',startTime:new Date(Date.now()-86400000).toISOString().replaceAll('-','').replaceAll(':',''),endTime:new Date(Date.now()+86400000).toISOString().replaceAll('-','').replaceAll(':','')};
 const reminderPosts=()=>calls.filter(c=>c.method==='POST'&&c.path.includes('/webhooks/'+donationHook+'/')&&c.data?.content);
 await publish({type:'raid',raid,reminder,clan:{name:'Snapshot Clan'},members:[{tag:'#P0Y1',name:'Unlinked Raider',townhall:16,remaining_attacks:3}]});
 await wait(()=>reminderPosts().length===1,'unlinked reminder send');
 const reminderMessage=reminderPosts()[0].data;
 if(!reminderMessage.content.includes('Unlinked Raider')||reminderMessage.content.includes('<@')||!reminderMessage.content.includes('(3 left)'))throw Error('Unlinked reminder rendering failed');
 if((await db.query('SELECT tag FROM player_links WHERE tag=ANY($1::text[])',[['#P0Y1','#P0Y2']])).rowCount)throw Error('Synthetic player tags are already linked');
 await db.query("INSERT INTO auth_users(user_id,provider) VALUES($1,'discord'),($2,'discord')",recipients);
 await db.query("INSERT INTO player_links(tag,user_id,source,is_verified) VALUES('#P0Y1',$1,'discord',true),('#P0Y2',$2,'discord',true)",recipients);
 const generation=randomUUID();
 await db.query('INSERT INTO discord_cache.gateway_shards(application_id,shard_id,shard_count,generation,healthy,heartbeat_at) VALUES($1,0,1,$2,true,now())',[app,generation]);
 await db.query("INSERT INTO discord_cache.guilds(id,data,application_id,shard_id,generation,available,metadata_complete,members_complete) VALUES($1,'{}',$2,0,$3,true,true,true)",[guild,app,generation]);
 for(const user of recipients)await db.query("INSERT INTO discord_cache.members(guild_id,user_id,data) VALUES($1,$2,'{}')",[guild,user]);
 await publish({type:'raid',raid,reminder,clan:{name:'Snapshot Clan'},members:[{tag:'#P0Y1',name:'Linked One',townhall:16,remaining_attacks:3},{tag:'#P0Y2',name:'Linked Two',townhall:15,remaining_attacks:2},{tag:'#P0Y3',name:'Unlinked Three',townhall:14,remaining_attacks:1}]});
 await wait(()=>reminderPosts().length===2,'two recipient reminder');
 const multi=reminderPosts().at(-1).data;
 if(!recipients.every(id=>multi.content.includes(`<@${id}>`)&&multi.allowed_mentions.users.includes(id))||multi.allowed_mentions.users.length!==2||!multi.content.includes('Unlinked Three'))throw Error('Two confirmed recipient mentions and unlinked row failed');
 const before=reminderPosts().length;await publish({type:'raid',raid,reminder,clan:{name:'Snapshot Clan'},members:[]});await new Promise(r=>setTimeout(r,1500));if(reminderPosts().length!==before)throw Error('Empty reminder sent');
 await db.query(`INSERT INTO reminders(server_id,type,clan_tag,webhook_token,minutes_remaining,type_name,channel_id,webhook_id) VALUES($1,1,'#P0Y','',1800,'War',$2,$3)`,[guild,channel,donationHook]);
 const prepWar={state:'preparation',startTime:new Date(Date.now()+3600000).toISOString().replaceAll('-','').replaceAll(':',''),endTime:new Date(Date.now()+90000000).toISOString().replaceAll('-','').replaceAll(':',''),attacksPerMember:2,
   clan:{tag:'#P0Y',name:'Preparation Clan',members:[{tag:'#P0Y3',name:'Prep Player',townhallLevel:16,attacks:[{},{}]}]},opponent:{tag:'#P0QQ',name:'Opponent',members:[]}};
 await publish({type:'war',minutes_remaining:1800,data:prepWar});
 await wait(()=>reminderPosts().length===3,'scheduled preparation delivery');
 const prepMessage=reminderPosts().at(-1).data.content;
 if(!prepMessage.includes('Prepare for battle day.')||!prepMessage.includes('War starts <t:')||!prepMessage.includes('Prep Player')||!prepMessage.includes('(2/2)'))throw Error('Scheduled preparation content or roster incorrect');
 await db.query('UPDATE autoboards SET next_run_at=now() WHERE id=$1',[boardIDs[1]]);await wait(()=>posts().length===4,'daily new message');
 // Actual member-join delivery uses the same stored configuration as /buttons.
 await db.query("UPDATE servers SET embed_color='#123456' WHERE id=$1",[guild]);
 await db.query("INSERT INTO server_welcome_panels(server_id,button_color,welcome_channel_id) VALUES($1,'Blue',$2)",[guild,channel]);
 for(const [position,name]of ['Link Button','Refresh Button','To-Do Button','Roster Button'].entries())await db.query('INSERT INTO server_welcome_panel_buttons(server_id,button_name,position) VALUES($1,$2,$3)',[guild,name,position]);
 const joinEvent={type:'member_join',guild_id:guild,user_id:recipients[0],application_id:app};
 const welcomes=()=>calls.filter(c=>c.method==='POST'&&c.path.startsWith('/channels/')&&c.data?.embeds?.length);
 await publish(joinEvent);await wait(()=>welcomes().length===1,'default welcome panel');
 const welcome=welcomes()[0].data;
 if(welcome.embeds[0].description!=='**Welcome to E2E Donors!**\nUse the buttons below to get started.'||welcome.embeds[0].color!==0x123456||welcome.components[0].components.length!==4||welcome.components[0].components[1].label!=='Refresh Roles'||welcome.components[0].components[1].emoji.name!=='refresh'||welcome.components[0].components.some(button=>button.style!==1)||welcome.allowed_mentions.parse.length||welcome.allowed_mentions.users.length!==1)throw Error('Default welcome panel differs from configured legacy design: '+JSON.stringify(welcome));
 await db.query("INSERT INTO server_custom_embeds(server_id,name,data) VALUES($1,'Saved welcome',$2)",[guild,{content:'@everyone saved text',embeds:[{title:'Saved welcome'}]}]);
 await db.query("UPDATE server_welcome_panels SET embed_name='Saved welcome',button_color='Red',welcome_channel_id='999999999999997506' WHERE server_id=$1",[guild]);
 await publish(joinEvent);await wait(()=>welcomes().length===2,'saved welcome in thread');
 const savedWelcome=welcomes()[1].data;if(savedWelcome.embeds[0].title!=='Saved welcome'||!savedWelcome.content.includes('@everyone saved text')||savedWelcome.components[0].components[0].style!==4||savedWelcome.allowed_mentions.parse.length||savedWelcome.allowed_mentions.users.length!==1||!welcomes()[1].path.includes('506'))throw Error('Saved welcome/thread/mention scope failed');
 lockedWelcome=true;await publish(joinEvent);await new Promise(r=>setTimeout(r,1200));if(welcomes().length!==2)throw Error('Locked welcome thread received a panel');
 console.log(JSON.stringify({checks:['default and saved welcome panels through actual event consumer','legacy welcome buttons and hex color','thread destination and locked-thread suppression','only new member can be mentioned','legacy donation log webhook and badge','separate donated and received fields','negative resets and empty changes suppressed','paused donation log suppressed','full snapshot donation baseline','configured arrows and clan identity','rowLimit2 hides third player','refresh edits same message','coalesced donation events','daily creates new message','farming all three resources','farming session time','farming missing duration','farming edits same message','farming 30 second periodic schedule','unlinked reminder visible without ping','two confirmed users both explicitly mentioned','unlinked row retained alongside mentions','empty reminder suppressed','scheduled preparation roster and start time'],webhookCreates:posts().length,webhookEdits:edits().length,reminderSends:3,confirmedMentionCount:multi.allowed_mentions.users.length}));
}finally{
 if(worker&&worker.exitCode===null){worker.kill('SIGTERM');await Promise.race([new Promise(r=>worker.once('exit',r)),new Promise(r=>setTimeout(r,6000))]);}
 if(ownsFarming)await db.query("DELETE FROM battles_farming WHERE player_tag IN ('#P0YQ','#P0YG') AND battle_time > now()-interval '2 hours'");
 if(ownsRecords){await db.query('DELETE FROM discord_cache.members WHERE guild_id=$1',[guild]);await db.query('DELETE FROM discord_cache.guilds WHERE id=$1',[guild]);await db.query('DELETE FROM discord_cache.gateway_shards WHERE application_id=$1',[app]);
 await db.query('DELETE FROM player_links WHERE user_id=ANY($1::text[])',[recipients]);await db.query('DELETE FROM auth_users WHERE user_id=ANY($1::text[])',[recipients]);
 await db.query('DELETE FROM servers WHERE id=$1',[guild]);}if(ownsClan)await db.query("DELETE FROM basic_clan WHERE tag='#P0Y'");await db.end();await redis('DEL',stream);if(ownsSnapshot)await redis('DEL',snapshot);await new Promise(r=>provider.close(r));
}
