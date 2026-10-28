import type { CommandContext } from "./types";
export const graphMetrics={donated:"Donations",received:"Received troops",clanGames:"Recorded Clan Games points",capitalDonated:"Capital Gold donated",gold:"Recorded gold looted",elixir:"Recorded elixir looted",darkElixir:"Recorded dark elixir looted",attackWins:"Recorded attack wins",activity:"Recorded activity events",troopLevels:"Troop / spell levels gained",heroLevels:"Hero / pet levels gained",warStars:"Completed war score stars",warsWon:"Completed wars won",warsSpun:"Wars started",capitalRaided:"Recorded Capital Gold raided",raidParticipants:"Average raid participants"};
export type GraphMetric=keyof typeof graphMetrics;
const contributions=new Set(["donated","received","clanGames","capitalDonated"]);
export const graphBasis=(metric:string)=>["gold","elixir","darkElixir","attackWins","troopLevels","heroLevels"].includes(metric)?"Latest stored clan members":"Clan recorded on each event or war";
export async function graphTotal(ctx:CommandContext,tag:string,season:string,metric:GraphMetric,signal?:AbortSignal):Promise<{season:string;value:number|null}>{
 const query=season==="current"?{}:{season};
 if(!contributions.has(metric))return ctx.services.api.get<{season:string;value:number|null}>(`/v2/bot/clans/${encodeURIComponent(tag)}/graph-total`,{...query,metric},signal);
 const data=await ctx.services.api.get<{season:string;truncated:boolean;items:Array<Record<string,number>>}>(`/v2/bot/clans/${encodeURIComponent(tag)}/season-stats`,query,signal);
 return {season:data.season,value:data.truncated?null:data.items.reduce((sum,row)=>sum+row[metric]!,0)};
}

export const validGraphValue=(metric:string,value:number)=>Number.isFinite(value)&&value>=0&&(metric==="raidParticipants"?value<=50:Number.isSafeInteger(value));
