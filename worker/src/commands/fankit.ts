import { editOriginalInteractionResponse, createInteractionFollowup } from "../discord/message-actions";
import { DiscordRestError } from "../discord/rest";
import { sendInteractionError } from "./errors";
import { actionRow, componentsV2, legacyMessage, type ContainerChild } from "../discord/components";
import { InteractionResponseType, type DiscordInteractionResponse } from "../discord/types";
import { CommandInputError, OptionType, requireGuildId, stringOption } from "./command-utils";
import { escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { Command, CommandContext } from "./types";

interface Asset {id:string;title:string;path:string;animated:boolean}
let catalog: {expires:number;pending:Promise<Asset[]>}|undefined;
const root="https://assets.clashk.ing/";
const encode=(value:string)=>{let binary="";for(const b of new TextEncoder().encode(value))binary+=String.fromCharCode(b);return btoa(binary).replaceAll("+","-").replaceAll("/","_").replace(/=+$/u,"");};
function queryValue(raw:string){
 const query=raw.trim().replace(/\s+/gu," ");
 if(!query||query.length>40||new TextEncoder().encode(query).length>48||/[\p{Control}]/u.test(query))throw new CommandInputError("Use a search phrase up to 40 characters.");return query;
}
async function bytes(response:Response,limit:number){
 if(!response.ok||Number(response.headers.get("content-length"))>limit){await response.body?.cancel();throw new CommandInputError("The fan-kit service is unavailable or returned an oversized image. Try another result.");}
 const reader=response.body?.getReader();if(!reader)throw new CommandInputError("The fan-kit service returned no data.");
 const chunks:Uint8Array[]=[];let size=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();throw new CommandInputError("This fan-kit response is too large. Try another result.");}chunks.push(value);}}finally{reader.releaseLock();}
 const result=new Uint8Array(size);let offset=0;for(const chunk of chunks){result.set(chunk,offset);offset+=chunk.length;}return result;
}
async function search(query:string):Promise<Asset[]>{
 if(!catalog||catalog.expires<Date.now()){
  const pending=(async()=>{
   const response=await fetch(`${root}manifest.json`,{redirect:"manual",signal:AbortSignal.timeout(10000)});
   const body=JSON.parse(new TextDecoder().decode(await bytes(response,2*1024*1024))) as {version:number;assets:Record<string,unknown[]>};
   if(body.version!==2||!body.assets||typeof body.assets!=="object")throw new CommandInputError("The asset catalog is unavailable.");
   return Object.values(body.assets).flat().flatMap(row=>{
    if(!row||typeof row!=="object")return [];
    const value=row as Record<string,unknown>;
    if(typeof value.path!=="string"||typeof value.display_name!=="string"||typeof value.sha!=="string"||!/^[a-f0-9]{64}$/u.test(value.sha)||!value.path.split('/').every(part=>part&&part!=='.'&&part!=='..')||/[\\?#\p{Control}]/u.test(value.path)||!/[.](png|webp|jpe?g|gif|avif)$/iu.test(value.path))return [];
    return [{id:value.sha.slice(0,12),title:value.display_name,path:value.path,animated:value.animated===true}];
   });
  })();
  catalog={expires:Date.now()+300000,pending};
  pending.catch(()=>{if(catalog?.pending===pending)catalog=undefined;});
 }
 const normalize=(value:string)=>value.toLocaleLowerCase("en").normalize("NFKC").replace(/[^\p{L}\p{N}]+/gu," ").trim();
 const phrase=normalize(query),words=phrase.split(/\s+/u);
 // Word boundaries matter: "ore" is a resource before it is part of "explorer".
 // Paths broaden discovery, but a matching displayed name always ranks first.
 const rank=(asset:Asset)=>{
  const title=normalize(asset.title),titleWords=title.split(" "),path=normalize(asset.path);
  if(title===phrase)return 0;
  if(words.every(word=>titleWords.includes(word)))return 1;
  if(words.every(word=>titleWords.some(token=>token.startsWith(word))))return 2;
  if(words.every(word=>title.includes(word)))return 3;
  if(words.every(word=>path.split(" ").includes(word)))return 4;
  return 5;
 };
 return [...new Map((await catalog.pending).map(asset=>[asset.id,asset])).values()].filter(asset=>words.every(word=>normalize(`${asset.title} ${asset.path}`).includes(word))).sort((a,b)=>rank(a)-rank(b)||a.title.localeCompare(b.title)||a.path.localeCompare(b.path));
}
const urlFor=(asset:Asset,emoji=false)=>new URL(asset.path.split('/').map(encodeURIComponent).join('/').replace(emoji&&!asset.animated?/\.(png|webp|jpe?g|avif)$/iu:/$^/u,'.avif')+(emoji&&!asset.animated?'?size=128':''),root).href;
async function page(ctx:CommandContext,query:string,index:number){
 const assets=await search(query),pageCount=Math.ceil(assets.length/5);
 if(!assets.length)return legacyMessage({content:"No ClashKing assets found for that search.",allowed_mentions:{parse:[]}});
 if(!Number.isInteger(index)||index<0||index>=pageCount)throw new CommandInputError("These results changed. Run /fankit again.");
 const token=encode(query),children:ContainerChild[]=[{type:10,content:`## ${escapeMarkdown(query)}`}];
 for(const asset of assets.slice(index*5,index*5+5)){
  children.push({type:9,components:[{type:10,content:`**${escapeMarkdown(asset.title)}**`}],accessory:{type:2,style:2,label:"Add Emoji",custom_id:`ck:fk:e:${token}:${asset.id}`,disabled:!ctx.interaction.guild_id||asset.path.endsWith('.svg')}},{type:12,items:[{media:{url:urlFor(asset)},description:asset.title}]});
 }
 children.push({type:10,content:`-# Page ${index+1}/${pageCount} (${assets.length} images)`});
 return componentsV2([{type:17,accent_color:await serverEmbedColor(ctx),components:children},...(pageCount>1?[actionRow({type:2,style:2,label:"Previous",disabled:index===0,custom_id:`ck:fk:p:${token}:${Math.max(0,index-1)}`},{type:2,style:2,label:"Next",disabled:index===pageCount-1,custom_id:`ck:fk:p:${token}:${Math.min(pageCount-1,index+1)}`})]:[])]);
}
async function addEmoji(ctx:CommandContext,query:string,id:string){
 const guild=requireGuildId(ctx),permissions=ctx.interaction.member?.permissions??"0";
 // CREATE_GUILD_EXPRESSIONS authorizes uploads. Managing existing expressions
 // alone does not. Each click supplies fresh signed member permissions.
 if(!/^\d+$/u.test(permissions)||(BigInt(permissions)&((1n<<43n)|8n))===0n)throw new CommandInputError("Create Expressions permission is required to add server emojis.");
 const asset=(await search(query)).find(item=>item.id===id);
 if(!asset||asset.path.endsWith('.svg'))throw new CommandInputError("This image cannot be added. Run /fankit again.");
 // Never trust a URL from a component: resolve the hash through our catalog.
 const response=await fetch(urlFor(asset,true),{redirect:"manual",signal:AbortSignal.timeout(10000)}),type=response.headers.get("content-type")?.split(";")[0]??"";
 if(!["image/png","image/jpeg","image/gif","image/webp","image/avif"].includes(type)){await response.body?.cancel();throw new CommandInputError("This image format cannot be used as a Discord emoji.");}
 const image=await bytes(response,256*1024);let binary="";for(let offset=0;offset<image.length;offset+=8192)binary+=String.fromCharCode(...image.subarray(offset,offset+8192));
 const name=asset.title.toLowerCase().replace(/[^a-z0-9_]/gu,"_").replace(/_+/gu,"_").replace(/^_|_$/gu,"").slice(0,32)||"asset";
 try{
  // Do not retry an uncertain creation; Discord may already have accepted it.
  const emoji=await ctx.services.discordRest.createGuildEmoji(guild,{name:name,image:`data:${type};base64,${btoa(binary)}`});
  return legacyMessage({content:`Emoji added: <${asset.animated?'a':''}:${emoji.name}:${emoji.id}>`,allowed_mentions:{parse:[]}},{ephemeral:true});
 }catch(error){if(error instanceof DiscordRestError)throw error;throw new CommandInputError("Could not add the emoji. Check available emoji slots and the bot's Create Expressions permission.");}
}
export const fankitCommand:Command={deferred:true,definition:{name:"fankit",description:"Browse ClashKing game assets",type:1,integration_types:[0,1],contexts:[0,1,2],options:[{name:"query",description:"Search troops, heroes, buildings and other game artwork",type:OptionType.String,required:true,min_length:1,max_length:40}]},execute:ctx=>page(ctx,queryValue(stringOption(ctx,"query")??""),0)};
export function dispatchFankit(ctx:CommandContext,waitUntil?:(promise:Promise<unknown>)=>void):Promise<DiscordInteractionResponse>|DiscordInteractionResponse{
 const match=/^ck:fk:([pe]):([A-Za-z0-9_-]{1,64}):([a-f0-9]{1,12})$/u.exec(ctx.interaction.data?.custom_id??"");
 if(!match)throw new CommandInputError("Invalid asset control.");
 let query:string;try{query=queryValue(new TextDecoder("utf-8",{fatal:true}).decode(Uint8Array.from(atob(match[2]!.replaceAll("-","+").replaceAll("_","/")),c=>c.charCodeAt(0))));}catch{throw new CommandInputError("Invalid asset search.");}
 const browsing=match[1]==="p";
 if(browsing&&!/^\d{1,5}$/u.test(match[3]!))throw new CommandInputError("Invalid asset page.");
 const run=()=>browsing?page(ctx,query,Number(match[3])):addEmoji(ctx,query,match[3]!);
 if(!waitUntil)return run().then(result=>browsing?{...result,type:InteractionResponseType.UpdateMessage}:result);
 waitUntil(run().then(result=>browsing?editOriginalInteractionResponse(ctx.services.discordRest,ctx.interaction.token,result.data??{}):createInteractionFollowup(ctx.services.discordRest,ctx.interaction.token,result.data??{})).catch(error=>sendInteractionError(ctx,error)));
 return {type:InteractionResponseType.DeferredUpdateMessage};
}
