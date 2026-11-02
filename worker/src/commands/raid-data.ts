import { CommandInputError } from "./command-utils";
import type { CommandContext } from "./types";
import { warTime } from "./war-data";
export interface Raid {
  state:string;startTime:string;endTime:string;totalAttacks:number;capitalTotalLoot:number;
  raidsCompleted:number;enemyDistrictsDestroyed:number;
  offensiveReward?:number;defensiveReward?:number;
  members?:Array<{tag:string;name:string;attacks:number;attackLimit:number;bonusAttackLimit:number;capitalResourcesLooted:number}>;
  attackLog?:Array<{name?:string;attacker?:{name:string};defender?:{name:string};attackCount?:number;districtsDestroyed?:number;districtCount?:number;districts:Array<{name:string;id?:number;districtHallLevel?:number;destructionPercent?:number;totalLooted?:number;attacks?:unknown[]}>}>;
  defenseLog?:Array<{name?:string;attacker?:{name:string};defender?:{name:string};attackCount?:number;districtsDestroyed?:number;districtCount?:number;districts:Array<{name:string;id?:number;districtHallLevel?:number;destructionPercent?:number;totalLooted?:number;attacks?:unknown[]}>}>;
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

/** Match the raid poster's six-attack estimate until official rewards arrive. */
export function raidMedals(raid:Raid){
 const districtRewards:Record<number,number>={1:135,2:225,3:350,4:405,5:460};
 const capitalRewards:Record<number,number>={2:180,3:360,4:585,5:810,6:1115,7:1240,8:1260,9:1375,10:1450};
 const attacks=(raid.attackLog??[]).reduce((sum,entry)=>sum+(entry.attackCount??0),0);
 const pool=(raid.attackLog??[]).flatMap(entry=>entry.districts).reduce((sum,district)=>sum+(district.destructionPercent===100?(district.id===70000000?capitalRewards:districtRewards)[district.districtHallLevel??0]??0:0),0);
 const offense=raid.offensiveReward?raid.offensiveReward*6:attacks?Math.ceil(pool/attacks)*6:0;
 return {offense,defense:raid.defensiveReward??0,estimated:raid.state==="ongoing"};
}
