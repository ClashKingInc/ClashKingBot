import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType, MessageFlags, type DiscordInteractionResponse } from "../discord/types";
import { CommandInputError, OptionType, requireGuildId, stringOption } from "./command-utils";
import { serverEmbedColor } from "./embed-color";
import type { Command, CommandContext } from "./types";
interface Asset {id:number;title:string;preview:string;image:string}
const media=(raw:unknown,width?:number)=>{
 if(typeof raw!=="string")return undefined;
 try{const url=new URL(raw.replaceAll("{width}",String(width??800)));if(url.protocol!=="https:"||url.hostname!=="media.ffycdn.net"||!url.pathname.startsWith("/eu/supercell/")||url.username||url.password||url.port)return undefined;return url.href;}catch{return undefined;}
};
async function bytes(response:Response,limit:number){
 if(!response.ok||Number(response.headers.get("content-length"))>limit){await response.body?.cancel();throw new CommandInputError("The fan-kit service is unavailable or returned an oversized image. Try another result.");}
 const reader=response.body?.getReader();if(!reader)throw new CommandInputError("The fan-kit service returned no data.");
 const chunks:Uint8Array[]=[];let size=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();throw new CommandInputError("This fan-kit response is too large. Try another result.");}chunks.push(value);}}finally{reader.releaseLock();}
 const result=new Uint8Array(size);let offset=0;for(const chunk of chunks){result.set(chunk,offset);offset+=chunk.length;}return result;
}
const encode=(value:string)=>{let binary="";for(const b of new TextEncoder().encode(value))binary+=String.fromCharCode(b);return btoa(binary).replaceAll("+","-").replaceAll("/","_").replace(/=+$/u,"");};
function queryValue(raw:string){
 const query=raw.trim().replace(/\s+/gu," ");
 if(!query||query.length>40||new TextEncoder().encode(query).length>48||/[\p{Control}]/u.test(query))throw new CommandInputError("Use a shorter fan-kit search phrase (up to 40 characters).");return query;
}
async function search(query:string):Promise<Asset[]>{
 const url=new URL("https://fankit.supercell.com/api/assets/search/338");url.search=new URLSearchParams({q:query,limit:"25",page:"1",requestnewflag:"true",order:"RELEVANCE"}).toString();
 const response=await fetch(url,{redirect:"manual",signal:AbortSignal.timeout(10000)});
 let data:unknown;try{data=JSON.parse(new TextDecoder().decode(await bytes(response,2*1024*1024)));}catch(error){if(error instanceof CommandInputError)throw error;throw new CommandInputError("Could not read the fan-kit results. Try again.");}
 const body=data as {success?:unknown;data?:unknown};
 if(!body||body.success!==true||!Array.isArray(body.data))throw new CommandInputError("Could not load fan-kit results. Try again.");
 const assets:Asset[]=[];
 for(const row of body.data.slice(0,25)){
  if(!row||typeof row!=="object")continue;
  const value=row as Record<string,unknown>,preview=media(value.preview_url),image=media(value.generic_url,128);
  if(value.is_image!==true||!Number.isSafeInteger(value.id)||Number(value.id)<=0||typeof value.title!=="string"||!preview||!image)continue;
  assets.push({id:Number(value.id),title:value.title.slice(0,256),preview,image});
 }
 return assets;
}
async function page(ctx:CommandContext,query:string,index:number,assetId?:number){
 const assets=await search(query);if(assetId!==undefined)index=assets.findIndex(asset=>asset.id===assetId);if(!assets.length)return legacyMessage({content:"No fan-kit images found for that search.",allowed_mentions:{parse:[]}});
 if(index<0||index>=assets.length)throw new CommandInputError("These results changed. Run /fankit again.");
 const asset=assets[index]!,token=encode(query);
 return legacyMessage({allowed_mentions:{parse:[]},embeds:[{title:asset.title,image:{url:asset.preview},color:await serverEmbedColor(ctx),footer:{text:`${index+1}/${assets.length} · Supercell fan kit`}}],components:[
  actionRow({type:3,custom_id:`ck:fk:s:${token}:0`,placeholder:"Choose an image",options:assets.map(item=>({label:item.title.slice(0,100),value:String(item.id),default:item.id===asset.id}))}),
  actionRow({type:2,style:5,label:"Download",url:asset.preview},...(ctx.interaction.guild_id?[{type:2 as const,style:2 as const,label:"Add as Emoji",custom_id:`ck:fk:e:${token}:${asset.id}`}]:[])),
 ]});
}
async function addEmoji(ctx:CommandContext,query:string,id:number){
 const guild=requireGuildId(ctx),permissions=ctx.interaction.member?.permissions??"0";
 // Check the clicker's current signed permissions, never the search author's.
 if(!/^\d+$/u.test(permissions)||(BigInt(permissions)&((1n<<43n)|(1n<<30n)|8n))===0n)throw new CommandInputError("Create Expressions permission is required to add server emojis.");
 const asset=(await search(query)).find(item=>item.id===id);
 // A component carries an asset ID, not a downloadable URL. Re-resolve it
 // against current provider results before letting a click trigger an upload.
 if(!asset)throw new CommandInputError("This result is no longer available. Run /fankit again.");
 const response=await fetch(asset.image,{redirect:"manual",signal:AbortSignal.timeout(10000)}),type=response.headers.get("content-type")?.split(";")[0]??"";
 if(!["image/png","image/jpeg","image/gif","image/webp","image/avif"].includes(type)){await response.body?.cancel();throw new CommandInputError("This image format cannot be used as a Discord emoji.");}
 const image=await bytes(response,256*1024);let binary="";for(let offset=0;offset<image.length;offset+=8192)binary+=String.fromCharCode(...image.subarray(offset,offset+8192));
 const name=(asset.title.replace(/[^a-zA-Z0-9_]/gu,"_").replace(/_+/gu,"_").slice(0,24)+`_${id}`).slice(0,32);
 try{
  // Never retry an uncertain emoji creation: Discord might already have accepted it.
  const emoji=await ctx.services.discordRest.createGuildEmoji(guild,name,`data:${type};base64,${btoa(binary)}`);
  return legacyMessage({content:`Emoji added: <:${emoji.name}:${emoji.id}>`,allowed_mentions:{parse:[]}},{ephemeral:true});
 }catch{throw new CommandInputError("Could not add the emoji. Check the server's emoji slots and the bot's Create Expressions permission before trying again.");}
}
export const fankitCommand:Command={deferred:true,definition:{name:"fankit",description:"Browse official Supercell fan-kit images",type:1,integration_types:[0,1],contexts:[0,1,2],options:[{name:"query",description:"Image search phrase",type:OptionType.String,required:true,min_length:1,max_length:40}]},execute:ctx=>page(ctx,queryValue(stringOption(ctx,"query")??""),0)};
export function dispatchFankit(ctx:CommandContext,waitUntil?:(promise:Promise<unknown>)=>void):Promise<DiscordInteractionResponse>|DiscordInteractionResponse{
 const match=/^ck:fk:([pse]):([A-Za-z0-9_-]{1,64}):(\d{1,12})$/u.exec(ctx.interaction.data?.custom_id??"");
 if(!match)throw new CommandInputError("Invalid fan-kit control.");
 let query:string;try{query=queryValue(new TextDecoder("utf-8",{fatal:true}).decode(Uint8Array.from(atob(match[2]!.replaceAll("-","+").replaceAll("_","/")),c=>c.charCodeAt(0))));}catch{throw new CommandInputError("Invalid fan-kit search.");}
 const value=Number(match[3]);if(!Number.isSafeInteger(value)||match[1]==="p"&&value>24)throw new CommandInputError("Invalid fan-kit result.");
 let selected:number|undefined;
 if(match[1]==="s"){
  const values=ctx.interaction.data?.values;
  if(ctx.interaction.data?.component_type!==3||values?.length!==1||!/^\d{1,12}$/u.test(values[0]!))throw new CommandInputError("Choose an image from these results.");
  selected=Number(values[0]);
 }
 const browsing=match[1]!=="e";
 const run=()=>browsing?page(ctx,query,value,selected):addEmoji(ctx,query,value);
 if(!waitUntil)return run().then(result=>browsing?{...result,type:InteractionResponseType.UpdateMessage}:result);
 waitUntil(run().then(result=>browsing?ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token,result.data??{}):ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token,result.data??{})).catch(error=>ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token,{content:error instanceof CommandInputError?error.message:"Could not load the fan kit. Try again.",flags:MessageFlags.Ephemeral})));
 return {type:InteractionResponseType.DeferredUpdateMessage};
}
