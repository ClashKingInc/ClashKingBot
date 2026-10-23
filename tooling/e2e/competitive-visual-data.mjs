import {createRequire} from 'node:module';
import {readFileSync,writeFileSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import {loadLocalApiSecrets} from '/Users/matthewanderson/PycharmProjects/clashking_api/scripts/local-api-keychain.mjs';
const require=createRequire('/Users/matthewanderson/PycharmProjects/clashking_api/workers/api/package.json'),pg=require('pg');
const file=process.argv[2],fixture=JSON.parse(readFileSync(file,'utf8'));
if(!fixture.email.endsWith('@competitive-qa.clashking.invalid')||fixture.serverId)throw Error('Expected a fresh owned visual fixture');
const origin='http://127.0.0.1:8787',db=new pg.Client({connectionString:'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev'});
await db.connect();
const serverId='999999999999994903',clans=['#QYLL0P2L','#QYLL0P2Q'];
try{
  await db.query('BEGIN');
  if((await db.query('SELECT 1 FROM servers WHERE id=$1',[serverId])).rowCount)throw Error('Visual server already exists');
  await db.query("INSERT INTO servers(id,name) VALUES($1,'Local competitive visual QA')",[serverId]);
  for(const [i,tag] of clans.entries()){
    if((await db.query('SELECT 1 FROM basic_clan WHERE tag=$1',[tag])).rowCount)throw Error('Visual clan already exists');
    await db.query('INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,$2,true,0,2,\'local\',0,0)',[tag,['Night Owls · QA','Northstar · QA'][i]]);
    await db.query('INSERT INTO server_clans(tag,server_id) VALUES($1,$2)',[tag,serverId]);
    await db.query("INSERT INTO server_clan_verifications(server_id,clan_tag,challenge_id,marker,marker_index,requested_by,state,check_after,next_check_at,expires_at,verified_at) VALUES($1,$2,$3,'appleck',0,$4,'verified',now()+interval '2 minutes',now(),now()+interval '1 day',now())",[serverId,tag,randomUUID(),fixture.userId]);
  }
  await db.query('COMMIT');
  fixture.serverId=serverId;fixture.clans=clans;writeFileSync(file,JSON.stringify(fixture),{mode:0o600});
  const keys=loadLocalApiSecrets();
  async function request(path,data,token=keys.API_BOT_TOKEN,method='POST'){
    const response=await fetch(origin+path,{method,headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result=await response.json();if(!response.ok)throw Error(`${path}: ${response.status} ${JSON.stringify(result)}`);return result;
  }
  const session=await request('/v2/auth/email',{email:fixture.email,password:fixture.password,device_id:'competitive-visual-local',device_name:'Local QA'});
  const base=`/v2/competitive/servers/${serverId}`,teams=[];
  for(let i=0;i<2;i++){
    const {id}=await request(base+'/teams',{clanTag:clans[i],internalName:i?'Evening duo':'Weekend duo',size:2});teams.push(id);
    for(const playerTag of fixture.tags.slice(i*2,i*2+2)){
      await request(base+`/teams/${id}/members`,{playerTag});
      await request(`/v2/competitive/teams/${id}/join`,{playerTag},session.access_token);
    }
  }
  await request(base+'/teams',{clanTag:clans[0],internalName:'Large-war roster',size:10});
  const tournament=await request(base+'/tournaments',{name:'Ember Weekly · Local QA',format:'single_elimination',teamSize:2,startsAt:new Date(Date.now()+86400000).toISOString(),endsAt:new Date(Date.now()+2*86400000).toISOString(),rules:{description:'Synthetic local browser test. Free entry. Two verified accounts per roster.',minTownHall:18,maxTownHall:18,maxRosterSize:2}});
  fixture.tournamentId=tournament.id;writeFileSync(file,JSON.stringify(fixture),{mode:0o600});
  await request(base+`/tournaments/${tournament.id}`,{status:'registration'},undefined,'PUT');
  for(const teamId of teams){await request(`/v2/competitive/tournaments/${tournament.id}/register`,{teamId},session.access_token);await request(`/v2/competitive/tournaments/${tournament.id}/check-in`,{teamId},session.access_token);}
  await request(base+`/tournaments/${tournament.id}/generate`,{});
  await request('/v2/competitive/profile',{displayName:'Nova · Local QA',avatarUrl:null,bannerUrl:null,bio:'Synthetic local review account. Weekend competitor.',socials:{},private:false,hideDiscord:true},session.access_token,'PUT');
  console.log(JSON.stringify({serverId,tournamentId:tournament.id,teams:teams.length,scope:'synthetic local only'}));
}finally{await db.end();}
