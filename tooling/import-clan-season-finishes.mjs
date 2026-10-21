// Production is read-only. Merge only current members of the requested clan into the
// named local database; preserve local-only history and back up changed rows.
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {mkdtempSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const args=process.argv.slice(2);
let apply=false,clanTag='#P09LP8CY',hasClan=false;
for(let index=0;index<args.length;index++){
 if(args[index]==='--apply'&&!apply){apply=true;continue;}
 if(args[index]==='--clan'&&!hasClan&&args[index+1]){clanTag=args[++index].trim().toUpperCase();hasClan=true;continue;}
 throw Error('Usage: node tooling/import-clan-season-finishes.mjs [--clan #TAG] [--apply]');
}
if(!/^#[0289PYLQGRJCUV]+$/.test(clanTag))throw Error('Invalid clan tag');
const response=await fetch('http://127.0.0.1:8011/v1/clans/'+encodeURIComponent(clanTag),{signal:AbortSignal.timeout(15000)});
if(!response.ok)throw Error('Current clan roster unavailable: '+response.status);
const roster=await response.json();
if(roster.tag!==clanTag||!Array.isArray(roster.memberList)||roster.memberList.length<1||roster.memberList.length>50)throw Error('Invalid roster');
const tags=[...new Set(roster.memberList.map(member=>member.tag))].sort();
if(tags.some(tag=>!/^#[0289PYLQGRJCUV]+$/.test(tag)))throw Error('Invalid player tag');
const columns=['season','player_tag','rank','trophies','player_name','exp_level','attack_wins','defense_wins','clan_tag','clan_name','clan_badge_token','league_tier_id'];
const sourceCommand='docker exec -i timescale-qsj8dfwekv4uw7ri76r9bhcx-023002241562 sh -c \'exec psql -X -q -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d clashking\'';
const sourceSql=`BEGIN READ ONLY; SET LOCAL statement_timeout='20s';
SELECT COALESCE(json_agg(history),'[]'::json) FROM
(SELECT ${columns.join(',')} FROM public.legend_history
WHERE player_tag IN (${tags.map(tag=>"'"+tag+"'").join(',')}) ORDER BY player_tag,season) history;
COMMIT;`;
const rows=JSON.parse(execFileSync('ssh',['-o','BatchMode=yes','-o','ConnectTimeout=10','root@152.53.82.182',sourceCommand],{input:sourceSql,encoding:'utf8',maxBuffer:16*1024*1024,timeout:40000}).trim());
if(!Array.isArray(rows)||rows.some(row=>!tags.includes(row.player_tag)))throw Error('Source rows outside requested roster');
const require=createRequire('/Users/matthewanderson/PycharmProjects/clashking_api/package.json');
const {Client}=require('pg');
const db=new Client({connectionString:'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev'});
await db.connect();
try{
 await db.query('BEGIN');
 await db.query("SET LOCAL statement_timeout='20s'");
 const identity=(await db.query('SELECT current_database() database,inet_server_addr()::text address')).rows[0];
 if(identity.database!=='clashking_dev')throw Error('Local database identity mismatch');
 await db.query("SELECT pg_advisory_xact_lock(hashtext('local-clan-season-finish-import'))");
 const before=(await db.query(`SELECT ${columns.join(',')} FROM legend_history WHERE player_tag=ANY($1::text[]) ORDER BY player_tag,season`,[tags])).rows;
 const beforeTotal=Number((await db.query('SELECT count(*) AS n FROM legend_history')).rows[0].n);
 await db.query('CREATE TEMP TABLE incoming_clan_finishes (LIKE legend_history INCLUDING DEFAULTS) ON COMMIT DROP');
 await db.query(`INSERT INTO incoming_clan_finishes (${columns.join(',')}) SELECT ${columns.join(',')} FROM json_populate_recordset(NULL::legend_history,$1::json)`,[JSON.stringify(rows)]);
 const changed=Number((await db.query(`SELECT count(*) n FROM incoming_clan_finishes source LEFT JOIN legend_history target USING(player_tag,season)
WHERE target.player_tag IS NULL OR ROW(${columns.map(column=>'source.'+column).join(',')}) IS DISTINCT FROM ROW(${columns.map(column=>'target.'+column).join(',')})`)).rows[0].n);
 const directory=mkdtempSync(join(tmpdir(),'ck-clan-season-finishes-'));
 writeFileSync(join(directory,'before.json'),JSON.stringify({clanTag,tags,rows:before},null,2),{mode:0o600});
 writeFileSync(join(directory,'source.json'),JSON.stringify({clanTag,rosterObservedAt:new Date().toISOString(),tags,rows},null,2),{mode:0o600});
 if(apply){
  await db.query(`INSERT INTO legend_history (${columns.join(',')}) SELECT ${columns.join(',')} FROM incoming_clan_finishes
ON CONFLICT(player_tag,season) DO UPDATE SET ${columns.filter(column=>!['season','player_tag'].includes(column)).map(column=>column+'=EXCLUDED.'+column).join(',')}`);
  const missing=Number((await db.query(`SELECT count(*) n FROM incoming_clan_finishes source LEFT JOIN legend_history target USING(player_tag,season)
WHERE target.player_tag IS NULL OR ROW(${columns.map(column=>'source.'+column).join(',')}) IS DISTINCT FROM ROW(${columns.map(column=>'target.'+column).join(',')})`)).rows[0].n);
  const afterTotal=Number((await db.query('SELECT count(*) AS n FROM legend_history')).rows[0].n);
  const newKeys=rows.filter(row=>!before.some(old=>old.player_tag===row.player_tag&&old.season===row.season)).length;
  if(missing||afterTotal!==beforeTotal+newKeys)throw Error('Import reconciliation failed');
 }
 const perPlayer=roster.memberList.map(member=>({tag:member.tag,name:member.name,sourceFinishes:rows.filter(row=>row.player_tag===member.tag).length}));
 const report={applied:apply,clanTag,clanName:roster.name,members:tags.length,sourceRows:rows.length,playersWithFinishes:perPlayer.filter(player=>player.sourceFinishes>0).length,changedRows:changed,backupDirectory:directory,perPlayer};
 await db.query(apply?'COMMIT':'ROLLBACK');
 writeFileSync(join(directory,'report.json'),JSON.stringify(report,null,2),{mode:0o600});
 console.log(JSON.stringify(report,null,2));
}catch(error){await db.query('ROLLBACK');throw error;}finally{await db.end();}
