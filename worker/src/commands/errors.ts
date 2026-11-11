import { ClashContractError } from '../api/clash-wire';
import { editOriginalInteractionResponse, createInteractionFollowup } from "../discord/message-actions";
import { ClashKingApiError } from '../api/client';
import { DiscordRestError } from '../discord/rest';
import { actionRow, linkButton } from '../discord/components';
import { InteractionResponseType, MessageFlags, type DiscordInteraction, type DiscordInteractionResponse } from '../discord/types';
import { CommandInputError } from './command-utils';
import { translate, resolveLocale } from '../localization/catalog';
import type { CommandContext } from './types';

type ErrorContext = Pick<CommandContext,'interaction'|'services'>;
interface Explanation { title:string; description:string; unexpected?:boolean }
function apiReason(error:ClashKingApiError):string|undefined{
  try { const body=JSON.parse(error.body);return typeof body.reason==='string'?body.reason:typeof body.detail?.reason==='string'?body.detail.reason:undefined; }catch{return undefined;}
}
function explain(error:unknown,interaction:DiscordInteraction):Explanation{
  if(error instanceof CommandInputError){
    const message=error.message;
    if(message===translate('error.guild',resolveLocale(interaction.locale,interaction.guild_locale)))return {title:'Use this in a server',description:message};
    if(/^Invalid .*?(?:control|page|interaction|button|selection|action)\.?$/iu.test(message))return {title:'Open a fresh command',description:'This control is no longer available. Run the command again and use its new buttons.'};
    if(message===translate('error.tag',resolveLocale(interaction.locale,interaction.guild_locale)))return {title:'Invalid player or clan tag',description:'Copy the tag from Clash of Clans and try again. A tag starts with # and is different from the player or clan name.'};
    return {title:/permission|manage server|manage roles|access|another (?:user|person|server)/iu.test(message)?'Permission needed':/no .*linked|not found|unavailable|not available|no active|not in|already|not ongoing/iu.test(message)?'Not available':'Check your selection',description:message};
  }
  if(error instanceof ClashContractError)return {title:'Service temporarily unavailable',description:'ClashKing or the game API could not respond. Please try again shortly.',unexpected:true};
  if(error instanceof ClashKingApiError){
    const reason=apiReason(error);
    if(error.outcome.kind==='maintenance')return {title:'Clash of Clans maintenance',description:'Game data is temporarily unavailable. Please try again after maintenance ends.'};
    if(error.outcome.kind==='privateWarLog'||reason==='privateWarLog')return {title:'Private war log',description:'This clan’s war log is private. Ask a clan leader to make it public in Clash of Clans.'};
    if(reason==='linked_account')return {title:'Link an account first',description:'Use /link add to link and verify your account, then try again.'};
    if(reason==='wrong_message')return {title:'This control is no longer available',description:'Run the command again or open the current panel.'};
    if(reason==='roles')return {title:'Permission needed',description:'Your server roles do not allow this action. Ask a server administrator to check your access.'};
    // Only known domain failures become user-facing instructions. Never echo
    // arbitrary provider messages, SQL errors, request bodies, or credentials.
    let message:string|undefined;try{message=JSON.parse(error.body).message;}catch{}
    const rosterMessages:Record<string,Explanation>={
      'Roster maximum signups would be exceeded':{title:'Roster is full',description:'There is not enough space for these accounts. Choose fewer accounts or another roster.'},
      'Roster account limit per Discord user would be exceeded':{title:'Account limit reached',description:'You have reached this roster’s per-person account limit. Remove an account before adding another.'},
      'None of your linked accounts are on this roster':{title:'No accounts to remove',description:'None of your linked accounts are on this roster.'},
      'No linked accounts are available to add to this roster':{title:'No eligible accounts',description:'Your linked accounts are already signed up or do not meet this roster’s requirements.'},
      'Roster form expired, completed, or its board was archived':{title:'Roster form expired',description:'Open the current roster board and start again.'},
    };
    if(error.path?.includes('/tickets/')&&message==='Ticket not found in this channel')return {title:'Not a ticket channel',description:'Use this command inside the ticket channel you want to update.'};
    if(error.path?.includes('/tickets/')&&message==='This member already has access to this ticket')return {title:'Already in this ticket',description:'This member already has access. No changes were made.'};
    if(error.path?.includes('roster')&&message&&Object.hasOwn(rosterMessages,message))return rosterMessages[message]!;
    if(error.status===413)return {title:'File too large',description:'Choose a smaller image and try again.'};
    if(error.status===401)return {title:'Service temporarily unavailable',description:'ClashKing could not authenticate this request. Please contact the support server if it continues.'};
    if(error.status===429)return {title:'Please wait a moment',description:'Too many requests were made. Try again shortly.'};
    if(error.status>=500)return {title:'Service temporarily unavailable',description:'ClashKing or the game API could not respond. Please try again shortly.'};
    if(error.status===404){
      const entity=error.path?.includes('/clash/players/')?'Player':error.path?.includes('/clash/clans/')?'Clan':'Record';
      return {title:`${entity} not found`,description:entity==='Record'?'This item may have been removed. Run the command again to choose a current item.':`No ${entity.toLowerCase()} was found with that tag. Copy the tag from Clash of Clans and try again.`};
    }
    if(error.status===403)return {title:'Access unavailable',description:error.path?.includes('/bot/clash/')?'The game API refused this request. Please try again later.':'You do not have access to this action. Ask a server administrator to check your permissions.'};
    if(error.status===409)return {title:'This item changed',description:'The item already exists or changed since you opened it. Refresh the list before trying again.'};
    if(error.status===400||error.status===422)return {title:'Check your selection',description:'One or more values could not be accepted. Check the selected player, clan, date, and other options.'};
  }
  if(error instanceof DiscordRestError){
    let code:number|undefined;try{code=JSON.parse(error.body).code;}catch{/* Never display a raw Discord error body. */}
    if(code===50013||code===50001||error.status===403)return {title:'Bot permission needed',description:'ClashKing cannot access this channel or complete this action. Ask an administrator to check the bot’s channel permissions and role position.'};
    if(code===30008)return {title:'No emoji slots available',description:'This server has reached its emoji limit. Remove an unused emoji and try again.'};
    if(code===10062||code===10008||code===10015)return {title:'This interaction expired',description:'Run the command again to open a fresh message.'};
    if(error.status===429)return {title:'Please wait a moment',description:'Discord is limiting requests. Try again shortly.'};
    if(error.status>=500)return {title:'Discord is temporarily unavailable',description:'Discord could not complete this request. Please try again shortly.',unexpected:true};
  }
  if(error instanceof Error&&['AbortError','TimeoutError'].includes(error.name))return {title:'Request timed out',description:'The service took too long to respond. If you were making a change, check whether it completed before trying again.'};
  if(error instanceof TypeError&&/fetch|network|connect/iu.test(error.message))return {title:'Service temporarily unavailable',description:'ClashKing could not reach the service. Please try again shortly.'};
  return {title:'Something went wrong',description:'I couldn’t complete this request. If you were making a change, check whether it went through before trying again.',unexpected:true};
}

/** No network or custom emoji dependency: errors must still render during outages.
 * Keep tokens, raw upstream bodies, and command options out of messages and logs. */
export function interactionErrorData(error:unknown,interaction:DiscordInteraction):NonNullable<DiscordInteractionResponse['data']>{
  const info=explain(error,interaction),reference=interaction.id;
  if(info.unexpected||error instanceof ClashKingApiError&&error.status>=500)console.warn('interaction_error',{reference,command:interaction.data?.name,type:error instanceof Error?error.name:'UnknownError',status:error instanceof ClashKingApiError||error instanceof DiscordRestError?error.status:undefined,...(error instanceof ClashContractError?{operation:error.operation,classification:error.kind}:{}),...(error instanceof DiscordRestError?{providerKind:error.providerKind}:{})});
  return {content:'',embeds:[{color:0xed4245,title:info.title,description:info.description,...(info.unexpected?{footer:{text:`Reference: ${reference}`}}:{})}],components:info.unexpected?[actionRow(linkButton('Support server','https://discord.gg/clashking'))]:[],allowed_mentions:{parse:[]},flags:MessageFlags.Ephemeral};
}
export function interactionErrorReply(error:unknown,interaction:DiscordInteraction):DiscordInteractionResponse{
  return {type:InteractionResponseType.ChannelMessageWithSource,data:interactionErrorData(error,interaction)};
}
/** Component failures are private follow-ups; never replace a shared report.
 * Slash-command failures finish their deferred original message in place. */
export async function sendInteractionError(ctx:ErrorContext,error:unknown,original=false):Promise<void>{
  const data=interactionErrorData(error,ctx.interaction);
  try{
    if(original)await editOriginalInteractionResponse(ctx.services.discordRest,ctx.interaction.token,data);
    else await createInteractionFollowup(ctx.services.discordRest,ctx.interaction.token,data);
  }catch{console.warn('interaction_error_delivery_failed',{reference:ctx.interaction.id});}
}
