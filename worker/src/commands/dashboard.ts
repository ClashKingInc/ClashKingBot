import { ClashKingApiError } from '../api/client';
import { actionRow, legacyMessage, linkButton } from '../discord/components';
import { CommandInputError, invokingUserId, requireGuildId } from './command-utils';
import type { Command, CommandContext } from './types';

export async function dashboardAccessLink(ctx: CommandContext, rosterId?: string) {
 const grant=await ctx.services.api.post<{code:string;expiresAt:string}>(`/v2/server/${requireGuildId(ctx)}/dashboard-access-grants`,{source:'bot',userId:invokingUserId(ctx)});
 // Neither the private grant code nor the destination is sent in a web request URL.
 // The dashboard derives the server from the authenticated grant response.
 const url=new URL('/access',ctx.env.DASHBOARD_BASE_URL);
 url.hash=new URLSearchParams({code:grant.code,...(rosterId?{roster:rosterId}:{})}).toString();
 return url.toString();
}

export const dashboardCommand:Command={
 deferred:true,ephemeral:true,
 definition:{name:'setup',description:'Open this server’s ClashKing dashboard',type:1,contexts:[0],integration_types:[0]},
 async execute(ctx){
  let url: string;
  try { url=await dashboardAccessLink(ctx); }
  catch (error) {
   if(error instanceof ClashKingApiError && error.status===403) {
    throw new CommandInputError('You need Manage Server, Administrator, or a role with Dashboard access to use /setup.');
   }
   if(error instanceof ClashKingApiError && error.status===503) {
    let message='';try{message=JSON.parse(error.body)?.message??'';}catch{}
    if(message.startsWith('Discord authorization')) {
     return legacyMessage({content:'ClashKing could not verify your server permissions right now. You can try again or sign in to the Dashboard. Access still requires Manage Server, Administrator, or a Dashboard-access role.',components:[actionRow(linkButton('Open dashboard',new URL('/login',ctx.env.DASHBOARD_BASE_URL).toString()))]},{ephemeral:true});
    }
   }
   // A first-time Discord user has no app account yet. Give them the normal
   // OAuth entry, never a fabricated account or a bypassed server grant.
   let firstUse=false;
   if(error instanceof ClashKingApiError && error.status===401) {
    try { firstUse=JSON.parse(error.body)?.message==='User session is no longer valid'; } catch { /* Preserve unrelated authentication errors. */ }
   }
   if(!firstUse)throw error;
   return legacyMessage({content:'Sign in with Discord, then choose this server to open its dashboard.',components:[actionRow(linkButton('Sign in to dashboard',new URL('/login',ctx.env.DASHBOARD_BASE_URL).toString()))]},{ephemeral:true});
  }
  return legacyMessage({content:'Open this server’s dashboard. Do not share this link. You can reopen it in another browser for 60 minutes.',components:[actionRow(linkButton('Open dashboard',url))]},{ephemeral:true});
 }
};
