import { activityOptions, activityReport } from "./activity";
import { seasonSummary, seasonSummaryOptions } from "./season-summary";
import { upgradeProgress, upgradeProgressOptions } from "./upgrade-progress";
import { familyDirectory, familyDirectoryOptions } from "./family-directory";
import { familyOperations, familyRaidOptions, familyWarOptions } from "./family-operations";
import { memberReport, memberReportOptions } from "./member-reports";
import { contributionOptions, contributionReport, type ContributionClan } from "./contribution-report";
import { CommandInputError, OptionType, requireGuildId } from "./command-utils";
import { subcommand } from "./game-common";
import type { Command } from "./types";
export const familyCommand:Command={
 deferred:true,
 definition:{name:"family",description:"Linked family clan contribution reports",type:1,integration_types:[0],contexts:[0],options:[
  {name:"activity",description:"Recorded activity and current-season last online",type:OptionType.Subcommand,options:activityOptions},
  {name:"summary",description:"Season summary for current members",type:OptionType.Subcommand,options:[...seasonSummaryOptions]},
  {name:"progress",description:"Observed unit upgrade changes and levels gained",type:OptionType.Subcommand,options:[...upgradeProgressOptions]},
  {name:"clans",description:"Browse family clans by category, league or location",type:OptionType.Subcommand,options:familyDirectoryOptions(false)},
  {name:"stats",description:"Rank linked clans by contributions or clan statistics",type:OptionType.Subcommand,options:familyDirectoryOptions(true)},
  {name:"wars",description:"Current family wars, including available CWL matchups",type:OptionType.Subcommand,options:familyWarOptions},
  {name:"raids",description:"Family raid participation for a selected weekend",type:OptionType.Subcommand,options:familyRaidOptions},
  {name:"compo",description:"Group current family members by a selected attribute",type:OptionType.Subcommand,options:memberReportOptions("compo")},
  {name:"sorted",description:"Rank current family members by a selected statistic",type:OptionType.Subcommand,options:memberReportOptions("sorted")},
  {name:"donations",description:"Top family contributors and clan donation totals",type:OptionType.Subcommand,options:[
   ...contributionOptions,{name:"season",description:"Recorded season YYYY-MM (defaults to current)",type:OptionType.String},
   {name:"sort_by",description:"Rank by donated, received or ratio",type:OptionType.String,choices:[{name:"Donated",value:"donated"},{name:"Received",value:"received"},{name:"Ratio",value:"ratio"}]},
   {name:"current_members",description:"Only include current family members (default false)",type:OptionType.Boolean},
  ]},
  {name:"games",description:"Current Clan Games players and totals for linked clans",type:OptionType.Subcommand,options:contributionOptions},
 ]},
 async execute(context){
  const ctx=subcommand(context);
  if(ctx.path[0]==="activity")return activityReport(ctx,"family");
  if(ctx.path[0]==="summary")return seasonSummary(ctx,"family");
  if(ctx.path[0]==="progress")return upgradeProgress(ctx,"family");
  if(["clans","stats"].includes(ctx.path[0]??""))return familyDirectory(ctx);
  if(["wars","raids"].includes(ctx.path[0]??""))return familyOperations(ctx);
  if(["compo","sorted"].includes(ctx.path[0]??""))return memberReport(ctx,"family");
  const guild=requireGuildId(ctx);
  const linked=await ctx.services.api.get<Array<{tag:string}>>(`/v2/server/${guild}/clans-basic`);
  if(!linked.length)throw new CommandInputError("No family clans are linked to this server. Add clans in the dashboard first.");
  const clans:ContributionClan[]=[];
  for(let i=0;i<linked.length;i+=5)clans.push(...await Promise.all(linked.slice(i,i+5).map(clan=>ctx.services.api.get<ContributionClan>(`/v2/bot/clash/clans/${encodeURIComponent(clan.tag)}`,{},AbortSignal.timeout(15000)))));
  return contributionReport(ctx,clans,ctx.path[0]==="games"?"games":"donations",true);
 },
};
