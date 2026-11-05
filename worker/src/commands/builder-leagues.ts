interface BuilderLeague { name:string; trophy_start:number }
let pending:Promise<BuilderLeague[]>|undefined,expires=0;

/** Use the same generated game thresholds as the app, rather than duplicating league ranges. */
export async function builderLeagues(){
 if(!pending||Date.now()>expires){
  expires=Date.now()+3600000;
  pending=fetch('https://assets.clashk.ing/static_data/builder_leagues.json',{signal:AbortSignal.timeout(8000),redirect:'manual'}).then(async response=>{
   if(!response.ok)throw Error('Builder Base league metadata unavailable');
   const text=await response.text();if(text.length>100000)throw Error('Oversized Builder Base league metadata');
   const body=JSON.parse(text) as {items:BuilderLeague[]};
   if(!Array.isArray(body.items)||body.items.some(item=>typeof item.name!=='string'||!Number.isFinite(item.trophy_start)))throw Error('Invalid Builder Base league metadata');
   return body.items.sort((a,b)=>b.trophy_start-a.trophy_start);
  }).catch(error=>{pending=undefined;throw error;});
 }
 return pending;
}
