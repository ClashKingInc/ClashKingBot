import { ClashKingApiError } from '../api/client';
import { actionRow, legacyMessage, linkButton } from '../discord/components';
import { invokingUserId, requireGuildId } from './command-utils';
import type { Command, CommandContext } from './types';

export async function dashboardAccessLink(ctx: CommandContext, rosterId?: string) {
 const grant=await ctx.services.api.post<{code:string;expiresAt:string}>(`/v2/server/${requireGuildId(ctx)}/dashboard-access-grants`,{source:'bot',userId:invokingUserId(ctx)});
 // Neither the one-use code nor the destination is sent in a web request URL.
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
   // A first-time Discord user has no app account yet. Give them the normal
   // OAuth entry, never a fabricated account or a bypassed server grant.
   let firstUse=false;
   if(error instanceof ClashKingApiError && error.status===401) {
    try { firstUse=JSON.parse(error.body)?.message==='User session is no longer valid'; } catch { /* Preserve unrelated authentication errors. */ }
   }
   if(!firstUse)throw error;
   return legacyMessage({content:'Sign in with Discord, then choose this server to open its dashboard.',components:[actionRow(linkButton('Sign in to dashboard',new URL('/login',ctx.env.DASHBOARD_BASE_URL).toString()))]},{ephemeral:true});
  }
  return legacyMessage({content:'Open this server’s dashboard. Do not share this link. It expires in 2 minutes and can be used once.',components:[actionRow(linkButton('Open dashboard',url))]},{ephemeral:true});
 }
};
