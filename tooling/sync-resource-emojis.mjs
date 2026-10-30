// Approved Beta-only padding correction. Keep source emojis intact for rollback.
import {createRequire} from 'node:module';
import {loadWorkspace} from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
const require=createRequire(new URL('../worker/package.json',import.meta.url));
const sharp=require('sharp');
const workspace=loadWorkspace('/Users/matthewanderson/ClashKing');
const app=workspace.env.DISCORD_CLIENT_ID;
if(app!=='808566437199216691')throw Error('Only Beta is allowed');
const headers={Authorization:`Bot ${workspace.env.DISCORD_BOT_TOKEN}`,'Content-Type':'application/json'};
const base=`https://discord.com/api/v10/applications/${app}/emojis`;
const response=await fetch(base,{headers});if(!response.ok)throw Error(`Inventory HTTP ${response.status}`);
const inventory=(await response.json()).items;
for(const name of ['gold','elixir','dark_elixir','capital_gold','clan_games','buildergold','builderelixir','shinyore','glowyore','starryore']){
 const target=`full_${name}`,source=inventory.find(item=>item.name===name);
 if(inventory.some(item=>item.name===target)){console.log(`${target}: already present`);continue;}
 if(!source)throw Error(`Missing source ${name}`);
 const response=await fetch(`https://cdn.discordapp.com/emojis/${source.id}.png?size=128`);
 if(!response.ok)throw Error(`Source HTTP ${response.status}`);
 const bytes=Buffer.from(await response.arrayBuffer());
 const {data,info}=await sharp(bytes).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 let left=info.width,top=info.height,right=-1,bottom=-1;
 for(let y=0;y<info.height;y++)for(let x=0;x<info.width;x++)if(data[(y*info.width+x)*4+3]>4){left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);}
 if(right<left)throw Error(`Empty source ${name}`);
 const png=await sharp(bytes).extract({left,top,width:right-left+1,height:bottom-top+1}).resize(120,120,{fit:'contain',background:'#00000000'}).extend({top:4,bottom:4,left:4,right:4,background:'#00000000'}).png().toBuffer();
 if(!process.argv.includes('--apply')){console.log(`${target}: ready (${png.length} bytes)`);continue;}
 const result=await fetch(base,{method:'POST',headers,body:JSON.stringify({name:target,image:`data:image/png;base64,${png.toString('base64')}`})});
 if(!result.ok)throw Error(`${target}: HTTP ${result.status}`);
 console.log(`${target}: created ${(await result.json()).id}`);
}
