import { componentsV2 } from '../discord/components';
import { emojis } from './game-common';
import { CommandInputError } from './command-utils';
import { graphControls, graphScope, type GraphClans } from './graph-controls';
import { chartDate, lineChartSvg } from './graph-renderer';
import type { CommandContext } from './types';
interface Finish {season:string;warLeague:{id:number;name:string}}
export async function graphCwl(ctx:CommandContext,clans:GraphClans,season:string,count:number,limit:number){
 const current=new Date().toISOString().slice(0,7),last=season==='current'?current:season,end=new Date(`${last}-01T00:00:00Z`);
 if(!Number.isFinite(+end))throw new CommandInputError('Choose a valid season.');
 const months=Array.from({length:count},(_,i)=>new Date(Date.UTC(end.getUTCFullYear(),end.getUTCMonth()-count+i+1,1)).toISOString().slice(0,7));
 const names=new Map<number,string>();let missing=false;
 const rows=[];
 for(let i=0;i<clans.selected.length;i+=4){
  const results=await Promise.allSettled(clans.selected.slice(i,i+4).map(async clan=>{
   const history=await ctx.services.api.get<{items:Finish[]}>(`/v2/cwl/${encodeURIComponent(clan.tag)}/seasons`,{limit:240});
   const finishes=new Map(history.items.map(item=>[item.season.slice(0,7),item.warLeague]));
   if(last===current){
    // Only use today's profile for a confirmed current group, never for history.
    try{const group=await ctx.services.api.get<{season:string;state:string}>(`/v2/bot/clash/clans/${encodeURIComponent(clan.tag)}/currentwar/leaguegroup`);
     if(group.season.slice(0,7)===current&&group.state!=='notInWar'){
      const profile=await ctx.services.api.get<{warLeague?:Finish['warLeague']}>(`/v2/bot/clash/clans/${encodeURIComponent(clan.tag)}`);
      if(profile.warLeague)finishes.set(current,profile.warLeague);
     }
    }catch{/* An unavailable current group stays a gap. */}
   }
   const values=months.map(month=>{const league=finishes.get(month);if(!league)return null;const rank=league.id-48000000;if(rank<1||rank>18)return null;names.set(rank,league.name.replace(' League',''));return rank;});
   return {...clan,values};
  }));
  for(const result of results)if(result.status==='fulfilled')rows.push(result.value);else missing=true;
 }
 const latest=(values:Array<number|null>)=>values.findLast((v):v is number=>v!==null)??0;
 const selected=rows.filter(row=>latest(row.values)>0).sort((a,b)=>latest(b.values)-latest(a.values)||a.name.localeCompare(b.name)).slice(0,clans.selectedTags.length || limit);
 const values=selected.flatMap(row=>row.values.filter((v):v is number=>v!==null));
 const min=values.length?Math.max(1,Math.min(...values)-1):1,max=values.length?Math.min(18,Math.max(...values)+1):18;
 const tiers=['','Bronze III','Bronze II','Bronze I','Silver III','Silver II','Silver I','Gold III','Gold II','Gold I','Crystal III','Crystal II','Crystal I','Master III','Master II','Master I','Champion III','Champion II','Champion I'];
 const stride=Math.max(1,Math.ceil((max-min)/5));
 const ticks=Array.from({length:max-min+1},(_,i)=>({value:min+i,label:tiers[min+i]!})).filter(t=>(t.value-min)%stride===0||t.value===max);
 const {posterArtwork}=await import('./legend-poster'),{renderGraphSvg,graphDecoration}=await import('./graph-image');
 const emoji=await emojis(ctx),{posterRemoteImage}=await import('./legend-poster');
 const decorated=await graphDecoration(ctx,'cwlLeague',selected);
 const art=await Promise.all(ticks.map(async tick=>{const found=emoji.component(tick.label.replace(' ',' League '));return {...tick,color:tick.value>=16?'#ff925a':tick.value>=13?'#ced1d8':tick.value>=10?'#bda6fb':tick.value>=7?'#f6c762':tick.value>=4?'#c8cdd5':'#cb9875',icon:found?await posterRemoteImage(`https://cdn.discordapp.com/emojis/${found.id}.png`):undefined};}));
 const svg=lineChartSvg({title:'CWL league',subtitle:`${graphScope(clans,selected.length)} | ${chartDate(months[0]!,true)} – ${chartDate(last,true)}`,logo:posterArtwork.logo,icon:art.find(tick=>tick.value===latest(selected[0]?.values??[]))?.icon??art.at(-1)?.icon,labels:months.map(m=>chartDate(m,true)),series:decorated.rows,axis:{min,max,ticks:art},formatValue:value=>names.get(value)??tiers[value]!,stepped:true,note:missing?'Some clans unavailable':undefined});
 const response=componentsV2([{type:12,items:[{media:{url:'attachment://cwl-leagues.png'}}]},...await graphControls(ctx,{view:'over-time',metric:'cwlLeague',period:season,count,limit,order:'desc'},clans)]);
 response.data!.__files=[{name:'cwl-leagues.png',bytes:await renderGraphSvg(svg)}];return response;
}
