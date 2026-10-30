import { CommandInputError } from "./command-utils";
import type { CommandContext } from "./types";
import { warTime } from "./war-data";
export interface Raid {
  state:string;startTime:string;endTime:string;totalAttacks:number;capitalTotalLoot:number;
  raidsCompleted:number;enemyDistrictsDestroyed:number;
  offensiveReward?:number;defensiveReward?:number;
  members?:Array<{tag:string;name:string;attacks:number;attackLimit:number;bonusAttackLimit:number;capitalResourcesLooted:number}>;
  attackLog?:Array<{districts:Array<{name:string;attacks?:unknown[]}>}>;
  defenseLog?:Array<{districts:Array<{name:string;attacks?:unknown[]}>}>;
}
export function currentRaidWeekend(){
  const now=new Date(),friday=new Date(now);
  friday.setUTCDate(now.getUTCDate()-(now.getUTCDay()+2)%7);friday.setUTCHours(7,0,0,0);
  if(friday>now)friday.setUTCDate(friday.getUTCDate()-7);
  return friday.toISOString().slice(0,10);
}
export function validateRaidWeekend(weekend:string){
  if(!/^\d{4}-\d{2}-\d{2}$/u.test(weekend)||!Number.isFinite(Date.parse(weekend))||new Date(weekend).toISOString().slice(0,10)!==weekend||new Date(weekend).getUTCDay()!==5||weekend>currentRaidWeekend())throw new CommandInputError("Choose a Friday on or before the most recent raid weekend.");
  return weekend;
}
export async function loadRaidWeekend(ctx:CommandContext,tag:string,weekend:string){
  const result=await ctx.services.api.get<{items:Raid[]}>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}/capitalraidseasons`,{limit:10},AbortSignal.timeout(15000));
  // A skipped weekend must not be replaced with the first available API row.
  return result.items.find(item=>{const time=warTime(item.startTime);return Number.isFinite(time)&&new Date(time).toISOString().slice(0,10)===weekend;});
}
