import type { Player, PlayerUnit } from "./game-common";

interface Level { level:number; required_townhall?:number; upgrade_time?:number; upgrade_cost?:number|Record<string,number> }
interface Item { name:string; village?:string; production_building?:string; production_building_level?:number; is_seasonal?:boolean; super_troop?:unknown; upgrade_resource?:string; rarity?:string; levels:Level[] }
export interface UpgradeItem { name:string; category:string; resource?:string; rarity?:string; current:number; maximum:number; previous:number; rushed:boolean; seconds:number; completedSeconds:number; totalSeconds:number; completedResourceWeight:number; totalResourceWeight:number; costs:Record<string,number> }
let cached:Promise<Map<string,Item[]>>|undefined,expires=0;
export async function playerCatalog(){
 if(!cached||Date.now()>expires){
  expires=Date.now()+3600000;
  cached=Promise.all(["troops","spells","heroes","pets","equipment","buildings"].map(async category=>{
   const response=await fetch(`https://assets.clashk.ing/static_data/${category}.json`,{signal:AbortSignal.timeout(8000),redirect:"manual"});
   if(!response.ok)throw Error(`Game metadata unavailable: ${category}`);
   const raw=await response.text();if(raw.length>2_000_000)throw Error("Oversized game metadata");
   const data=JSON.parse(raw) as {items:Item[]};
   if(!Array.isArray(data.items))throw Error("Invalid game metadata");
   return [category,data.items] as const;
  })).then(rows=>new Map(rows)).catch(error=>{cached=undefined;throw error;});
 }
 return cached;
}
export function playerUpgrades(player:Player,catalog:Map<string,Item[]>,targetTownHall=player.townHallLevel):UpgradeItem[]{
 const result:UpgradeItem[]=[];
 for(const category of ["troops","spells","heroes","pets","equipment"]){
  const owned:PlayerUnit[]=category==="spells"?player.spells??[]:category==="heroes"?player.heroes??[]:category==="equipment"?player.heroEquipment??[]:player.troops??[];
  for(const item of catalog.get(category)??[]){
   if((item.village&&item.village!=="home")||item.is_seasonal||item.super_troop!=null||!item.levels?.length)continue;
   const unit=owned.find(unit=>unit.name===item.name&&(!unit.village||unit.village==="home"));
   // Event/shop equipment is not automatically owned when its Town Hall unlocks.
   if(category==="equipment"&&!unit)continue;
   const factory=(catalog.get("buildings")??[]).find(building=>building.name===item.production_building&&building.village==="home");
   const unlock=factory?.levels.find(level=>level.level===item.production_building_level)?.required_townhall;
   if(!unit&&unlock!==undefined&&unlock>targetTownHall)continue;
   const allowed=item.levels.filter(level=>level.required_townhall!==undefined&&level.required_townhall<=targetTownHall);
   if(!allowed.length)continue;
   const maximum=Math.max(...allowed.map(level=>level.level)),current=unit?.level??0;
   const previous=Math.max(0,...item.levels.filter(level=>level.required_townhall!==undefined&&level.required_townhall<player.townHallLevel).map(level=>level.level));
   // Metadata stores the transition FROM this level TO the next one. The
   // maximum-level entry is a zero-cost terminal, not the last upgrade's cost.
   // Include level-zero unlock transitions if metadata supplies one. The current
   // troop catalog has none, so do not invent a separate acquisition charge.
   const transitions=item.levels.filter(level=>level.level<maximum);
   const todo=transitions.filter(level=>level.level>=current),costs:Record<string,number>={};
   for(const level of todo){
    if(typeof level.upgrade_cost==="number")costs[item.upgrade_resource??"Unknown"]=(costs[item.upgrade_resource??"Unknown"]??0)+level.upgrade_cost;
    else for(const [resource,cost] of Object.entries(level.upgrade_cost??{}))costs[resource]=(costs[resource]??0)+cost;
   }
   const completed=transitions.filter(level=>level.level<current);
   // Match the App's equipment resource weighting (shiny:glowy:starry = 1:5:35).
   const oreWeight=(levels:Level[])=>levels.reduce((sum,level)=>{const cost=level.upgrade_cost;return sum+(cost&&typeof cost==="object"?(cost.shiny_ore??0)+5*(cost.glowy_ore??0)+35*(cost.starry_ore??0):0);},0);
   result.push({name:item.name,category:item.production_building==="Workshop"?"siege":category,resource:item.upgrade_resource,rarity:item.rarity,current,maximum,previous,rushed:current<previous,seconds:todo.reduce((sum,level)=>sum+(level.upgrade_time??0),0),completedSeconds:completed.reduce((sum,level)=>sum+(level.upgrade_time??0),0),totalSeconds:transitions.reduce((sum,level)=>sum+(level.upgrade_time??0),0),completedResourceWeight:oreWeight(completed),totalResourceWeight:oreWeight(transitions),costs});
  }
 }
 return result;
}

/** Mirrors App summaryForItems: time-weighted for timed categories, resource-
 * weighted for equipment, and mean per-item completion for mixed summaries. */
export function upgradeCompletion(items:UpgradeItem[]):number|undefined{
 if(!items.length)return undefined;
 const clamp=(value:number)=>Math.max(0,Math.min(1,value));
 const timed=items.filter(item=>item.category!=="equipment"),equipment=items.filter(item=>item.category==="equipment");
 const fallback=(item:UpgradeItem)=>item.current>=item.maximum?1:0;
 const ratio=(item:UpgradeItem)=>item.category==="equipment"?(item.totalResourceWeight?clamp(item.completedResourceWeight/item.totalResourceWeight):item.maximum?clamp(item.current/item.maximum):fallback(item)):(item.totalSeconds?clamp(item.completedSeconds/item.totalSeconds):fallback(item));
 if(timed.length&&equipment.length)return items.reduce((sum,item)=>sum+ratio(item),0)/items.length;
 const total=items.reduce((sum,item)=>sum+(equipment.length?item.totalResourceWeight:item.totalSeconds),0);
 return total?clamp(items.reduce((sum,item)=>sum+(equipment.length?item.completedResourceWeight:item.completedSeconds),0)/total):items.reduce((sum,item)=>sum+ratio(item),0)/items.length;
}
