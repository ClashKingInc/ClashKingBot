import { contributionOptions, contributionReport, type ContributionClan } from "./contribution-report";
import { CommandInputError, OptionType, requireGuildId } from "./command-utils";
import { subcommand } from "./game-common";
import type { Command } from "./types";
export const familyCommand:Command={
 deferred:true,
 definition:{name:"family",description:"Linked family clan contribution reports",type:1,integration_types:[0],contexts:[0],options:[
  {name:"donations",description:"Top family contributors and clan donation totals",type:OptionType.Subcommand,options:[
   ...contributionOptions,{name:"season",description:"Recorded season YYYY-MM (defaults to current)",type:OptionType.String},
   {name:"sort_by",description:"Rank by donated, received or ratio",type:OptionType.String,choices:[{name:"Donated",value:"donated"},{name:"Received",value:"received"},{name:"Ratio",value:"ratio"}]},
   {name:"current_members",description:"Only include current family members (default false)",type:OptionType.Boolean},
  ]},
  {name:"games",description:"Current Clan Games players and totals for linked clans",type:OptionType.Subcommand,options:contributionOptions},
 ]},
 async execute(context){
  const ctx=subcommand(context),guild=requireGuildId(ctx);
  const linked=await ctx.services.api.get<Array<{tag:string}>>(`/v2/server/${guild}/clans-basic`);
  if(!linked.length)throw new CommandInputError("No family clans are linked to this server. Add clans in the dashboard first.");
  const clans:ContributionClan[]=[];
  for(let i=0;i<linked.length;i+=5)clans.push(...await Promise.all(linked.slice(i,i+5).map(clan=>ctx.services.api.get<ContributionClan>(`/v2/bot/clash/clans/${encodeURIComponent(clan.tag)}`,{},AbortSignal.timeout(15000)))));
  return contributionReport(ctx,clans,ctx.path[0]==="games"?"games":"donations",true);
 },
};
