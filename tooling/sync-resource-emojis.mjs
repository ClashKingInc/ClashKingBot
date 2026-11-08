// Normalize existing game artwork. Keep source emojis intact for rollback.
import {createRequire} from 'node:module';
const require=createRequire(new URL('../worker/package.json',import.meta.url));
const sharp=require('sharp');
const expected=process.argv.find(arg=>arg.startsWith('--application='))?.slice(14);
const useEnvironment=process.argv.includes('--token-env');
let app,token;
if(useEnvironment){
 if(!expected||!/^\d{15,22}$/.test(expected)||!process.env.DISCORD_BOT_TOKEN)throw Error('--token-env requires --application and DISCORD_BOT_TOKEN');
 app=expected;token=process.env.DISCORD_BOT_TOKEN;
}else{
 const {loadWorkspace}=await import('/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs');
 const workspacePath=process.argv.find(arg=>arg.startsWith('--workspace='))?.slice(12)??'/Users/matthewanderson/ClashKing';
 const workspace=loadWorkspace(workspacePath);
 app=workspace.env.DISCORD_CLIENT_ID;token=workspace.env.DISCORD_BOT_TOKEN;
}
if(process.argv.includes('--apply')&&(!expected||expected!==app))throw Error('--apply requires --application matching the credential application');
const headers={Authorization:`Bot ${token}`,'Content-Type':'application/json'};
// Bind the credential to the explicit target before any application mutation.
const identity=await fetch('https://discord.com/api/v10/oauth2/applications/@me',{headers});
if(!identity.ok||(await identity.json()).id!==app)throw Error('Credential application does not match target');
const base=`https://discord.com/api/v10/applications/${app}/emojis`;
const response=await fetch(base,{headers});if(!response.ok)throw Error(`Inventory HTTP ${response.status}`);
const inventory=(await response.json()).items;
const names=['gold','elixir','dark_elixir','capital_gold','clan_games','buildergold','builderelixir','shinyore','glowyore','starryore','no_star','war_star_filled','war_star_empty'];
const only=process.argv.find(arg=>arg.startsWith('--only='))?.slice(7);
if(only&&!names.includes(only))throw Error('Unknown emoji selection');
for(const name of names.filter(name=>!only||name===only)){
 const star=name.startsWith('war_star_');
 const target=star?name:`full_${name}`,source=inventory.find(item=>item.name===(star?'war_star':name));
 if(inventory.some(item=>item.name===target)){console.log(`${target}: already present`);continue;}
 if(!source)throw Error(`Missing source ${name}`);
 const response=await fetch(`https://cdn.discordapp.com/emojis/${source.id}.png?size=128`);
 if(!response.ok)throw Error(`Source HTTP ${response.status}`);
 const bytes=Buffer.from(await response.arrayBuffer());
 const {data,info}=await sharp(bytes).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 let left=info.width,top=info.height,right=-1,bottom=-1;
 for(let y=0;y<info.height;y++)for(let x=0;x<info.width;x++)if(data[(y*info.width+x)*4+3]>4){left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);}
 if(right<left)throw Error(`Empty source ${name}`);
 let png=await sharp(bytes).extract({left,top,width:right-left+1,height:bottom-top+1}).resize(120,120,{fit:'contain',background:'#00000000'}).extend({top:4,bottom:4,left:4,right:4,background:'#00000000'}).png().toBuffer();
 if(name==='war_star_empty'){
  // Derive the outline from the filled game's own silhouette, at exactly the
  // same bounds. Transparent center makes an unearned star distinct on both
  // light and dark Discord themes without inventing replacement artwork.
  const {data: pixels,info: size}=await sharp(png).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  const original=Buffer.from(pixels),border=7;
  for(let y=border;y<size.height-border;y++)for(let x=border;x<size.width-border;x++){
   let inside=true;
   for(let dy=-border;dy<=border&&inside;dy++)for(let dx=-border;dx<=border;dx++)if(original[((y+dy)*size.width+x+dx)*4+3]<200){inside=false;break;}
   if(inside)pixels[(y*size.width+x)*4+3]=0;
  }
  png=await sharp(pixels,{raw:{width:size.width,height:size.height,channels:4}}).png().toBuffer();
 }
 if(!process.argv.includes('--apply')){console.log(`${target}: ready (${png.length} bytes)`);continue;}
 const result=await fetch(base,{method:'POST',headers,body:JSON.stringify({name:target,image:`data:image/png;base64,${png.toString('base64')}`})});
 if(!result.ok)throw Error(`${target}: HTTP ${result.status}`);
 console.log(`${target}: created ${(await result.json()).id}`);
}
