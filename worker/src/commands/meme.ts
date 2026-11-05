import { sendInteractionError } from "./errors";
import {actionRow,componentsV2} from "../discord/components";
import {InteractionResponseType,InteractionType,MessageFlags,type DiscordInteractionResponse} from "../discord/types";
import {CommandInputError,invokingUserId} from "./command-utils";
import {modalFields,textField} from "./modals";
import {isMemeTemplate,memeTemplates,type MemeTemplate} from "./meme-templates";
import type {Command,CommandContext} from "./types";
function picker(owner:string){return actionRow({type:3,custom_id:`ck:meme:choose:${owner}`,placeholder:"Choose a meme template",options:Object.entries(memeTemplates).map(([value,item])=>({label:item.name,description:item.description,value}))});}
export const memeCommand:Command={
 ephemeral:true,
 definition:{name:"meme",description:"Make a Clash meme or Pepe sign",type:1,integration_types:[0,1],contexts:[0,1,2]},
 async execute(ctx){return componentsV2([{type:17,components:[{type:10,content:"## Make a meme\nChoose a template and add your captions."},picker(invokingUserId(ctx))]}],{ephemeral:true});},
};
function form(owner:string,template:MemeTemplate){return {type:InteractionResponseType.Modal,data:{custom_id:`ck:meme:submit:${owner}:${template}`,title:memeTemplates[template].name,components:memeTemplates[template].labels.map((label,i)=>textField(`text${i}`,label,template==='pepe'?40:120,true))}};}
async function preview(ctx:CommandContext,owner:string,template:MemeTemplate){
 const fields=modalFields(ctx.interaction.data?.components),texts=memeTemplates[template].labels.map((_,i)=>{
  const value=fields.get(`text${i}`)?.value?.trim().replace(/[\p{Control}\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,' ').replace(/\s+/gu,' ');
  if(!value||value.length>(template==='pepe'?40:120))throw new CommandInputError('Keep each caption within the field’s character limit.');return value;
 });
 const {renderMeme}=await import('./meme-image');
 const response=componentsV2([{type:12,items:[{media:{url:'attachment://meme.png'},description:memeTemplates[template].name}]},{type:10,content:'-# Save or copy image & share with your friends'},actionRow(
  {type:2,style:2,label:'Write again',custom_id:`ck:meme:write:${owner}:${template}`}),picker(owner)],{ephemeral:true});
 response.data!.__files=[{name:'meme.png',bytes:await renderMeme(template,texts)}];return response;
}
export function dispatchMeme(ctx:CommandContext,waitUntil?:(p:Promise<unknown>)=>void):DiscordInteractionResponse|Promise<DiscordInteractionResponse>{
 const match=/^ck:meme:(choose|write|submit):([0-9]{15,20})(?::([a-z]+))?$/u.exec(ctx.interaction.data?.custom_id??'');
 if(!match||match[2]!==invokingUserId(ctx))throw new CommandInputError('Use /meme to create your own meme.');
 const action=match[1],owner=match[2]!,template=action==='choose'?ctx.interaction.data?.values?.[0]:match[3];
 if(!template||!isMemeTemplate(template))throw new CommandInputError('Choose a current meme template.');
 const submit=action==='submit';
 if(submit!==(ctx.interaction.type===InteractionType.ModalSubmit))throw new CommandInputError('Invalid meme action.');
 if(action==='choose'||action==='write')return form(owner,template);
 const run=()=>preview(ctx,owner,template);
 if(!waitUntil)return run();
 waitUntil(run().then(r=>ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token,r.data??{})).catch(error=>sendInteractionError(ctx,error,true)));
 return {type:InteractionResponseType.DeferredChannelMessageWithSource,data:{flags:MessageFlags.Ephemeral}};
}
