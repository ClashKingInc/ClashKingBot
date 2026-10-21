// Match the App's Lucide ShieldCheck/TriangleAlert artwork. Only the explicitly
// selected Beta application is supported; no guild or production emoji writes.
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {loadWorkspace} from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
const require=createRequire(new URL('../worker/package.json',import.meta.url));
const {Resvg,initWasm}=require('@resvg/resvg-wasm');
await initWasm(readFileSync(require.resolve('@resvg/resvg-wasm/index_bg.wasm')));
// Dry runs render the actual checked-in art without credentials or network.
const apply=process.argv.includes('--apply');
const workspace=apply?loadWorkspace('/Users/matthewanderson/ClashKing'):undefined;
let existing=[];
let headers,base;
if(apply){
const app=workspace.env.DISCORD_CLIENT_ID;
if(app!=='808566437199216691')throw Error('Only the local Beta application is allowed');
headers={Authorization:`Bot ${workspace.env.DISCORD_BOT_TOKEN}`,'Content-Type':'application/json'};
base=`https://discord.com/api/v10/applications/${app}/emojis`;
const response=await fetch(base,{headers});if(!response.ok)throw Error(`Emoji inventory HTTP ${response.status}`);
existing=(await response.json()).items;
}
const icons={
 account_verified_green:{svg:readFileSync(new URL('../worker/src/assets/account-verified.svg',import.meta.url),'utf8')},
 account_unverified:{color:'#E56B2F',paths:'<path d="m10.3 3.8-8.5 14.3A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.8a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>'},
};
for(const [name,icon] of Object.entries(icons)){
 if(existing.some(item=>item.name===name)){console.log(`${name}: already present`);continue;}
 const svg=icon.svg??`<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 26 26"><g transform="translate(1 1)" fill="none" stroke="${icon.color}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">${icon.paths}</g></svg>`;
 const png=new Resvg(svg).render().asPng();
 if(!apply){console.log(`${name}: ready (${png.length} bytes); pass --apply to add to Beta`);continue;}
 const result=await fetch(base,{method:'POST',headers,body:JSON.stringify({name,image:`data:image/png;base64,${Buffer.from(png).toString('base64')}`})});
 if(!result.ok)throw Error(`${name}: HTTP ${result.status}`);
 console.log(`${name}: created ${(await result.json()).id}`);
}
