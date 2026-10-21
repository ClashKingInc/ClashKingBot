import { actionRow, legacyMessage, linkButton } from '../discord/components';
import { invokingUserId, requireGuildId } from './command-utils';
import type { Command } from './types';

export const dashboardCommand:Command={
 deferred:true,ephemeral:true,
 definition:{name:'dashboard',description:'Open this server’s ClashKing dashboard',type:1,contexts:[0],integration_types:[0]},
 async execute(ctx){
  const grant=await ctx.services.api.post<{code:string;expiresAt:string}>(`/v2/server/${requireGuildId(ctx)}/dashboard-access-grants`,{source:'bot',userId:invokingUserId(ctx)});
  // Fragments never reach the web server or its request logs. The API still
  // checks the browser's Discord identity before consuming this one-use grant.
  const url=new URL('/access',ctx.env.DASHBOARD_BASE_URL);url.hash=new URLSearchParams({code:grant.code}).toString();
  return legacyMessage({content:'Open this server’s dashboard. This link expires in 2 minutes and can be used once.',components:[actionRow(linkButton('Open dashboard',url.toString()))]},{ephemeral:true});
 }
};
