// A unique synthetic email login in the existing loopback development DB.
// No external identity, production account or auth bypass is involved.
import {createRequire} from 'node:module';
import {createHash,randomBytes,randomUUID} from 'node:crypto';
import {mkdtempSync,writeFileSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {loadLocalApiSecrets} from '/Users/matthewanderson/PycharmProjects/clashking_api/scripts/local-api-keychain.mjs';
const require=createRequire('/Users/matthewanderson/PycharmProjects/clashking_api/workers/api/package.json');
const {default:pg}=await import(require.resolve('pg'));
const {hash}=require('bcryptjs');
const db=new pg.Client({connectionString:'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev'});
await db.connect();
try {
  if(process.argv[2]==='populate'){
    const file=process.argv[3],fixture=JSON.parse(readFileSync(file,'utf8'));
    if(!fixture.email.endsWith('@competitive-qa.clashking.invalid'))throw Error('Not an owned visual fixture');
    const tags=['#QYLL0P2G','#QYLL0P2J','#QYLL0P2C','#QYLL0P2U'];
    for(const tag of tags) if((await db.query('SELECT 1 FROM basic_player WHERE tag=$1',[tag])).rowCount)throw Error('Visual fixture player already exists');
    await db.query('BEGIN');
    for(const [i,tag] of tags.entries()){
      await db.query('INSERT INTO basic_player(tag,name,townhall_level) VALUES($1,$2,18)',[tag,['Nova QA','Atlas QA','Echo QA','Luna QA'][i]]);
      await db.query("INSERT INTO player_links(tag,user_id,is_verified,verified_at,source) VALUES($1,$2,true,now(),'clashking')",[tag,fixture.userId]);
    }
    await db.query('COMMIT');
    fixture.tags=tags;writeFileSync(file,JSON.stringify(fixture),{mode:0o600});console.log('Added four synthetic verified player fixtures for UI testing');
  }else if(process.argv[2]==='cleanup'){
    const fixture=JSON.parse(readFileSync(process.argv[3],'utf8'));
    if(!fixture.email.endsWith('@competitive-qa.clashking.invalid'))throw Error('Not an owned visual fixture');
    await db.query('BEGIN');
    // This fixed server was created only by the paired visual fixture helper.
    // Delete children first; never broaden cleanup to existing local servers.
    if(fixture.serverId){
      if(fixture.serverId!=='999999999999994903')throw Error('Unknown visual fixture server');
      const server=await db.query('SELECT name FROM servers WHERE id=$1',[fixture.serverId]);
      if(server.rows[0]?.name!=='Local competitive visual QA')throw Error('Visual fixture server ownership mismatch');
      await db.query('DELETE FROM competitive_matches WHERE tournament_id IN (SELECT id FROM competitive_tournaments WHERE server_id=$1)',[fixture.serverId]);
      await db.query('DELETE FROM competitive_participants WHERE tournament_id IN (SELECT id FROM competitive_tournaments WHERE server_id=$1)',[fixture.serverId]);
      await db.query('DELETE FROM competitive_team_members WHERE team_id IN (SELECT id FROM competitive_teams WHERE server_id=$1)',[fixture.serverId]);
      await db.query('DELETE FROM competitive_tournaments WHERE server_id=$1',[fixture.serverId]);
      await db.query('DELETE FROM competitive_teams WHERE server_id=$1',[fixture.serverId]);
      await db.query('DELETE FROM competitive_role_grants WHERE server_id=$1',[fixture.serverId]);
      await db.query('DELETE FROM competitive_audit WHERE server_id=$1',[fixture.serverId]);
      await db.query('DELETE FROM server_clan_verifications WHERE server_id=$1',[fixture.serverId]);
      await db.query('DELETE FROM server_clans WHERE server_id=$1',[fixture.serverId]);
      await db.query('DELETE FROM servers WHERE id=$1',[fixture.serverId]);
      await db.query('DELETE FROM basic_clan WHERE tag=ANY($1::text[])',[fixture.clans]);
    }
    await db.query('DELETE FROM competitive_profiles WHERE user_id=$1',[fixture.userId]);
    await db.query('DELETE FROM player_links WHERE user_id=$1',[fixture.userId]);
    if(fixture.tags)await db.query('DELETE FROM basic_player WHERE tag=ANY($1::text[])',[fixture.tags]);
    await db.query('DELETE FROM auth_users WHERE user_id=$1 AND provider=$2',[fixture.userId,'email']);
    await db.query('COMMIT');
    console.log('Removed only the owned synthetic visual server, competitive records, clans, players and email identity');
  }else{
    const userId=randomUUID(),email=`review-${randomBytes(6).toString('hex')}@competitive-qa.clashking.invalid`,password=randomBytes(24).toString('base64url')+'7';
    const secrets=loadLocalApiSecrets(), emailHash=createHash('sha256').update(email+secrets.JWT_ACCESS_SECRET).digest('hex');
    await db.query("INSERT INTO auth_users(user_id,provider,email_hash,username,password_hash) VALUES($1,'email',$2,'Competitive QA',$3)",[userId,emailHash,await hash(password,10)]);
    const directory=mkdtempSync(join(tmpdir(),'ck-competitive-visual-')),file=join(directory,'identity.json');
    writeFileSync(file,JSON.stringify({userId,email,password}),{mode:0o600});console.log(JSON.stringify({file,userId}));
  }
}finally{await db.end();}
