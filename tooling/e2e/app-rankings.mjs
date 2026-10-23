// Exercise the real local public API through the App's installed SDK/contracts.
// App bundling/type checks cover its UI/service integration separately.
import {createRequire} from 'node:module';
const require=createRequire('/Users/matthewanderson/IdeaProjects/ClashKingApp/expo/package.json');
const {createApiClient,httpTransport}=await import('/Users/matthewanderson/IdeaProjects/ClashKingApp/expo/node_modules/@clashking/api-client/dist/index.js');
const {LeaderboardClanDonationsEndpoint,LeaderboardClanWarWinsEndpoint,WarTripleStreakEndpoint}=await import('/Users/matthewanderson/IdeaProjects/ClashKingApp/expo/node_modules/@clashking/api-contracts/dist/expo.js');
const {Effect}=await import(require.resolve('effect'));
const api=createApiClient({baseUrl:'http://127.0.0.1:8787',transport:httpTransport()});
const results=[];
for(const endpoint of [LeaderboardClanDonationsEndpoint,LeaderboardClanWarWinsEndpoint]){
 for(const locationId of ['global','32000006']){
  const value=await Effect.runPromise(api.execute(endpoint,{path:{locationId},query:{limit:5},body:{}}));
  if(value.items.length!==5||value.items.some(item=>item.rank<1||!item.tag||!item.name))throw Error('Expected valid existing clan rankings');
  results.push({operation:endpoint.operationId,locationId,count:value.items.length});
 }
}
const streak=await Effect.runPromise(api.execute(WarTripleStreakEndpoint,{path:{townhallLevel:18},query:{limit:5},body:{}}));
if(streak.townhall_level!==18||streak.items.some(item=>item.streak<=0||item.streak%2!==0))throw Error('Invalid streak ranking');
console.log(JSON.stringify({localApi:'passed',appSdkContracts:'passed',routes:results,streakCount:streak.items.length}));
