import { ClashKingApiError } from "../api/client";
import { actionRow, legacyMessage, type LegacyEmbed, type ActionRowComponent } from "../discord/components";
import { editOriginalInteractionResponse } from "../discord/message-actions";
import { InteractionResponseType, type DiscordInteractionResponse } from "../discord/types";
import { CommandInputError, invokingUserId, requireGuildId, OptionType, stringOption } from "./command-utils";
import { sendInteractionError } from "./errors";
import type { Command, CommandContext } from "./types";
const panelButtons=["Link Button","Link Help Button","Refresh Button","To-Do Button","Roster Button"] as const;
const panelColors=["Blue","Green","Grey","Red"] as const;
type PanelOptions={kind:"options";embeds:Array<{name:string;key:string}>};
async function panelRequest<T>(ctx:CommandContext,body:Record<string,unknown>):Promise<T>{
 try{return await ctx.services.api.post<T>(`/v2/bot/servers/${requireGuildId(ctx)}/member-panels`,{...body,actorId:invokingUserId(ctx)});}
 catch(error){if(error instanceof ClashKingApiError&&[400,403,404].includes(error.status)){
  let message="";try{message=JSON.parse(error.body)?.message??"";}catch{}
  if(message)throw new CommandInputError(message);}
  throw error;
 }
}
export const buttonsCommand:Command={
 deferred:true,ephemeral:true,
 definition:{name:"buttons",description:"Create a message with member link, refresh, task and roster buttons",type:1,contexts:[0],integration_types:[0],options:[
  {name:"embed",description:"Saved classic embed (optional)",type:OptionType.String,autocomplete:true,max_length:100},
  {name:"button_color",description:"Color of the member buttons",type:OptionType.String,choices:panelColors.map(color=>({name:color,value:color}))},
  {name:"on_welcome_channel",description:"Post this panel when someone joins this server",type:OptionType.Channel},
 ]},
 async autocomplete(ctx){
  const focused=ctx.options.get("embed");if(!focused?.focused)return [];
  const value=String(focused.value??"").toLocaleLowerCase();
  const options=await panelRequest<PanelOptions>(ctx,{action:"options"});
  return options.embeds.filter(item=>item.name.toLocaleLowerCase().includes(value)).slice(0,25).map(item=>({name:item.name.slice(0,100),value:item.key}));
 },
 async execute(ctx){
  const options=await panelRequest<PanelOptions>(ctx,{action:"options"}),requested=stringOption(ctx,"embed");
  const embed=requested?options.embeds.find(item=>item.key===requested||item.name===requested):undefined;
  if(requested&&!embed)throw new CommandInputError("No saved embed with that name. Choose an autocomplete result.");
  const color=panelColors.indexOf((stringOption(ctx,"button_color")??"Grey") as typeof panelColors[number]);
  if(color<0)throw new CommandInputError("Choose Blue, Green, Grey or Red.");
  const welcome=stringOption(ctx,"on_welcome_channel")??"0";
  if(welcome!=="0"&&!/^\d{15,20}$/u.test(welcome))throw new CommandInputError("Choose a welcome channel in this server.");
  // A stable short embed key fits Discord's 100-character ID without a volatile
  // isolate cache. The API resolves it against this server's current saved embeds.
  const id=`ck:panel:${invokingUserId(ctx)}:${requireGuildId(ctx)}:${color}:${welcome}:${embed?.key??"0"}:${Math.floor(Date.now()/1000+600).toString(36)}`;
  return legacyMessage({content:"Choose the buttons you would like on this embed",allowed_mentions:{parse:[]},components:[actionRow({type:3,custom_id:id,placeholder:"Button Types",min_values:1,max_values:4,options:panelButtons.map(name=>({label:name,value:name}))})]},{ephemeral:true});
 },
};
export async function dispatchButtons(ctx:CommandContext,waitUntil?: (promise:Promise<unknown>)=>void):Promise<DiscordInteractionResponse>{
 const parts=ctx.interaction.data?.custom_id?.split(":")??[],[,kind,actor,guild,color,welcome,embedKey,expiry]=parts;
 if(parts.length!==8||kind!=="panel"||actor!==invokingUserId(ctx)||guild!==requireGuildId(ctx))throw new CommandInputError("Only the panel creator can finish this selection in its original server.");
 if(!expiry||!Number.isFinite(parseInt(expiry,36))||parseInt(expiry,36)<Date.now()/1000)throw new CommandInputError("This selection expired. Run /buttons again.");
 if(!/^[0-3]$/u.test(color??"")||!/^0$|^\d{15,20}$/u.test(welcome??"")||!/^0$|^[a-f0-9]{12}$/u.test(embedKey??""))throw new CommandInputError("This selection is invalid. Run /buttons again.");
 const buttons=ctx.interaction.data?.values??[];
 if(buttons.length<1||buttons.length>4||new Set(buttons).size!==buttons.length||buttons.some(value=>!panelButtons.includes(value as typeof panelButtons[number])))throw new CommandInputError("Choose one to four different buttons.");
 const run=async()=>{
  const result=await panelRequest<{kind:"posted"|"welcome";channelId:string;messageId?:string;preview:{content?:string;embeds:LegacyEmbed[];components:ActionRowComponent[]}}>(ctx,{
   action:"publish",channelId:welcome!=="0"?welcome:ctx.interaction.channel_id,welcome:welcome!=="0",buttonColor:panelColors[Number(color)],...(embedKey!=="0"?{embedKey}:{}),buttons,
  });
  return legacyMessage(result.kind==="welcome"?{...result.preview,content:`This panel will post in <#${result.channelId}> when someone joins.${result.preview.content?`\n${result.preview.content}`:""}`,allowed_mentions:{parse:[]}}:{content:`Done · [View message](https://discord.com/channels/${guild}/${result.channelId}/${result.messageId})`,allowed_mentions:{parse:[]}});
 };
 // Replace the private builder after success; public member actions remain
 // independent and always resolve their current clicker.
 if(waitUntil){waitUntil(run().then(response=>editOriginalInteractionResponse(ctx.services.discordRest,ctx.interaction.token,response.data??{})).catch(error=>sendInteractionError(ctx,error,true)));return {type:InteractionResponseType.DeferredUpdateMessage};}
 const response=await run();return {...response,type:InteractionResponseType.UpdateMessage};
}
