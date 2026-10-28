import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import { graphMetrics } from "./graph";
import type { CommandContext } from "./types";
type Metric=keyof typeof graphMetrics;
interface Stats{season:string;truncated:boolean;items:Array<Record<Metric,number>>}
const xml=(value:string)=>value.replace(/[&<>"']/gu,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"})[c]!);
const text=(x:number,y:number,value:string,size=22,color="#c6d0e0")=>`<text x="${x}" y="${y}" fill="${color}" font-size="${size}" font-family="Blogger Sans">${xml(value)}</text>`;
export async function graphSeries(ctx:CommandContext){
 const metric=stringOption(ctx,"attribute") as Metric,requested=stringOption(ctx,"season")??"current",count=Number(ctx.options.get("months")?.value??4),limit=Number(ctx.options.get("limit")?.value??5),raw=stringOption(ctx,"clans")??"";
 if(!Object.hasOwn(graphMetrics,metric)||!Number.isInteger(count)||count<2||count>12||!Number.isInteger(limit)||limit<1||limit>10)throw new CommandInputError("Choose 2–12 seasons and 1–10 clans.");
 const refs=raw?[...new Set(raw.split(/[\s,]+/u).filter(Boolean).map(tag=>normalizeTag(tag,ctx.locale)))].map(tag=>({tag,name:tag})):await ctx.services.api.get<Array<{tag:string;name:string}>>(`/v2/server/${requireGuildId(ctx)}/clans-basic`);
 if(!refs.length||refs.length>50)throw new CommandInputError("Choose 1–50 clans.");
 let season=requested;
 if(season==="current"){
  try{season=(await Promise.any(refs.slice(0,5).map(ref=>ctx.services.api.get<Stats>(`/v2/bot/clans/${encodeURIComponent(ref.tag)}/season-stats`,{},AbortSignal.timeout(8000))))).season;}
  catch{throw new CommandInputError("Could not resolve the current game season. Try again.");}
 }
 const end=new Date(`${season}-01T00:00:00Z`);
 if(!Number.isFinite(+end)||end.toISOString().slice(0,7)!==season)throw new CommandInputError("Choose a season in YYYY-MM format.");
 const seasons=Array.from({length:count},(_,i)=>new Date(Date.UTC(end.getUTCFullYear(),end.getUTCMonth()-count+i+1,1)).toISOString().slice(0,7));
 const rows=refs.map(ref=>({...ref,values:Array.from<number|null>({length:count}).fill(null)}));
 const jobs=rows.flatMap(row=>seasons.map((value,index)=>({row,value,index})));let next=0,missing=jobs.length;
 const deadline=AbortSignal.timeout(25_000);
 // Missing/truncated requests stay null. Do not connect a line through a gap
 // or treat an unfinished request as a season with zero recorded contributions.
 await Promise.all(Array.from({length:Math.min(5,jobs.length)},async()=>{
  while(next<jobs.length&&!deadline.aborted){const job=jobs[next++]!;try{
   const data=await ctx.services.api.get<Stats>(`/v2/bot/clans/${encodeURIComponent(job.row.tag)}/season-stats`,{season:job.value},deadline);
   const sum=data.items.reduce((total,item)=>total+item[metric],0);
   if(data.season===job.value&&!data.truncated&&Number.isSafeInteger(sum)&&sum>=0){job.row.values[job.index]=sum;missing--;}
  }catch{/* The chart marks this observation unavailable. */}}
 }));
 const selected=rows.filter(row=>row.values[count-1]!==null).sort((a,b)=>b.values[count-1]!-a.values[count-1]!||a.tag.localeCompare(b.tag)).slice(0,limit);
 const largest=Math.max(1,...selected.flatMap(row=>row.values.filter((value):value is number=>value!==null)));
 const colors=["#55c8b0","#f6d882","#95b6ff","#f59ec7","#b8a0ef","#f6aa75","#91cf77","#71d7ed","#e69da4","#c6c4bc"];
 const {posterArtwork,renderPosterSvg}=await import("./legend-poster");
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1100"><rect width="1600" height="1100" fill="#101923"/><image href="${posterArtwork.logo}" x="1280" y="45" width="230" height="85"/>`+text(75,100,graphMetrics[metric],42,"#f6d882")+text(75,150,`${seasons[0]} — ${season} · Recorded clan-attributed totals`,25);
 const x=(i:number)=>140+i*1300/(count-1),y=(value:number)=>780-value/largest*520;
 for(let n=0;n<=4;n++){const py=780-n*130;svg+=`<path d="M140 ${py}H1440" stroke="#344454"/>`+text(45,py+8,new Intl.NumberFormat("en",{notation:"compact"}).format(largest*n/4),18);}
 seasons.forEach((value,i)=>{svg+=text(x(i)-36,825,value,18);});
 selected.forEach((row,index)=>{let path="",pen=false;row.values.forEach((value,i)=>{if(value===null){pen=false;return;}path+=`${pen?"L":"M"}${x(i)} ${y(value)} `;pen=true;svg+=`<circle cx="${x(i)}" cy="${y(value)}" r="5" fill="${colors[index]}"/>`;});svg+=`<path d="${path}" fill="none" stroke="${colors[index]}" stroke-width="3"/>`+text(90+(index%2)*740,885+Math.floor(index/2)*30,row.name.slice(0,40),21,colors[index]);});
 if(!selected.length)svg+=text(370,520,"No complete final-season totals available",32);
 svg+=text(75,1060,`${missing}/${jobs.length} observations unavailable · Gaps are unknown; zero means no recorded events`,22)+"</svg>";
 let details="",omitted=0;
 for(const row of selected){const line=`${row.name.replace(/[<@`*_~]/gu,"").slice(0,40)}: ${row.values.map(value=>value===null?"?":String(value)).join(" → ")}`;if(details.length+line.length+1>1650){omitted++;continue;}details+=(details?"\n":"")+line;}
 const response=legacyMessage({allowed_mentions:{parse:[]},content:`${graphMetrics[metric]} · ${seasons.join(", ")}\n${details}\n${missing} observations unavailable. Clans ranked by final-season total.${omitted?` ${omitted} text rows omitted; see chart.`:""}`,components:raw?[]:[actionRow({type:2,style:2,label:"Refresh",custom_id:`ck:page:gt:${invokingUserId(ctx)}:${metric}:${requested}:${count}:${limit}:0`})]});
 response.data!.attachments=[];response.data!.__files=[{name:"clan-contributions.png",bytes:await renderPosterSvg(svg)}];return response;
}
