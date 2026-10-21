// Read-only end-to-end verification of the actual local leaderboard service.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire('/Users/matthewanderson/PycharmProjects/clashking_api/package.json');
const {Client} = require('pg');
const db = new Client({connectionString:'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev'});
await db.connect();
try {
  let entries=0;
  for(let th=1;th<=18;th++) {
    const expected = (await db.query(`SELECT player_tag AS tag,streak FROM war_triple_streaks WHERE townhall_level=$1 AND streak>0 ORDER BY streak DESC,last_attack_time DESC,player_tag LIMIT 5`,[th])).rows;
    const response = await fetch(`http://127.0.0.1:8787/v2/leaderboard/war-triples/${th}?limit=5`);
    assert.equal(response.status,200,`TH${th} HTTP status`);
    const actual=await response.json();
    assert.equal(actual.townhall_level,th);
    assert.deepEqual(actual.items.map(({tag,streak})=>({tag,streak})),expected);
    assert.equal(actual.count,expected.length);
    assert(actual.items.every((row,i)=>row.rank===i+1 && row.streak>0 && row.streak%2===0));
    entries+=actual.count;
  }
  const integrity=(await db.query(`SELECT count(*)::integer AS invalid FROM war_triple_streaks s
    WHERE s.streak<0 OR s.streak%2<>0 OR NOT EXISTS (
      SELECT 1 FROM war_triple_streak_results r WHERE r.player_tag=s.player_tag AND r.townhall_level=s.townhall_level AND r.war_end_time=s.last_attack_time
    )`)).rows[0];
  assert.equal(integrity.invalid,0);
  console.log(JSON.stringify({result:'PASS',path:'local PostgreSQL -> actual API HTTP leaderboard',townHalls:18,entries,invalid:integrity.invalid,mutations:0}));
} finally { await db.end(); }
