// Execute the App's real ClanService against the running local API.
// No React mocks, browser automation, production writes or synthesized player data.
import {createRequire} from 'node:module';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {loadWorkspace} from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
const app='/Users/matthewanderson/IdeaProjects/ClashKingApp/expo';
const require=createRequire('/Users/matthewanderson/PycharmProjects/clashking_api/package.json');
const {build}=require('esbuild');
const workspace=loadWorkspace('/Users/matthewanderson/ClashKing');
if(workspace.env.TIMESCALE_HOST!=='127.0.0.1')throw Error('Only local API data is allowed');
const response=await fetch('http://127.0.0.1:8787/v2/bot/clash/clans/%238YL9CRJP',{headers:{Authorization:`Bearer ${workspace.env.API_BOT_TOKEN}`}});
if(!response.ok)throw Error(`Local clan lookup HTTP ${response.status}`);
const clan=await response.json();
const directory=mkdtempSync(join(tmpdir(),'ck-clan-competitive-'));
const outfile=join(directory,'app-service.mjs');
await build({stdin:{contents:`
import {loadClanCompetitiveDay} from './src/features/clan/data/clan-competitive-service';
import {hasCompetitiveMembers} from './src/features/clan/models/clan-competitive';
import {createApiClient,httpTransport} from '@clashking/api-client';
export async function run(value){
 const members=value.memberList.map(member=>({...member,league:member.leagueTier??member.league}));
 const api=createApiClient({baseUrl:'http://127.0.0.1:8787',transport:httpTransport()});
 const data=await loadClanCompetitiveDay(api,members);
 const day=new Date(Date.now()-(5*60+10)*60_000-86400000).toISOString().slice(0,10);
 const previous=await loadClanCompetitiveDay(api,members,day);
 return {visible:hasCompetitiveMembers(members),data,previous};
}`,resolveDir:app,sourcefile:'clan-competitive-e2e.ts',loader:'ts'},outfile,bundle:true,platform:'node',format:'esm',target:'node24'});
const {run}=await import(pathToFileURL(outfile).href);
const result=await run(clan);
if(!result.visible||!result.data.legends.length)throw Error('Current Legend clan members missing');
const expectedTags=clan.memberList.filter(member=>(member.leagueTier??member.league)?.id===105000036).map(member=>member.tag).sort();
for(const data of [result.data,result.previous]){
 if(JSON.stringify(data.legends.map(item=>item.member.tag).sort())!==JSON.stringify(expectedTags))throw Error('Clan page must include exactly the current Legend I members');
}
if(result.data.legends.some(item=>!clan.memberList.some(member=>member.tag===item.member.tag)||!item.stats||item.stats.attacks<0||item.stats.attacks>8||item.stats.defenses<0||item.stats.defenses>8))throw Error('Invalid current roster/day statistics');
const day=new Date(Date.now()-(5*60+10)*60_000).toISOString().slice(0,10);
if(result.data.day!==day)throw Error('Wrong Legend day boundary');
if(result.previous.day===day||result.previous.legends.some(item=>item.trophies!==undefined&&!item.globalRank))throw Error('Historical day/snapshot selection failed');
if('ranked' in result.data)throw Error('Ranked section was not removed');
console.log(JSON.stringify({appClanService:'passed',localApi:'passed',day,previousDay:result.previous.day,legendPlayers:result.data.legends.length,pageAvailable:result.visible}));
