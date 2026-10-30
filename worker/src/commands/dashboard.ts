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
 definition:{name:'dashboard',description:'Open this server’s ClashKing dashboard',type:1,contexts:[0],integration_types:[0]},
 async execute(ctx){
  const url=await dashboardAccessLink(ctx);
  return legacyMessage({content:'Open this server’s dashboard. This link expires in 2 minutes and can be used once.',components:[actionRow(linkButton('Open dashboard',url))]},{ephemeral:true});
 }
};
