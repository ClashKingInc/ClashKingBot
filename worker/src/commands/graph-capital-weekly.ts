import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId } from "./command-utils";
import type { CommandContext } from "./types";
interface History{weeks:string[];values:Array<number|null>;sampleDates:Array<string|null>}
const xml=(value:string)=>value.replace(/[&<>"']/gu,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"})[c]!);
const text=(x:number,y:number,value:string,size=22,color="#c6d0e0")=>`<text x="${x}" y="${y}" fill="${color}" font-size="${size}" font-family="Blogger Sans">${xml(value)}</text>`;
export async function graphCapitalWeekly(ctx:CommandContext,refs:Array<{tag:string;name:string}>,season:string,months:number,limit:number,custom:boolean){
 const rows:Array<History&{tag:string;name:string}>=[];let failed=0;let weeks:string[]=[];
 const deadline=AbortSignal.timeout(25000);
 for(let i=0;i<refs.length&&!deadline.aborted;i+=5){
  const result=await Promise.allSettled(refs.slice(i,i+5).map(async ref=>({...ref,...await ctx.services.api.get<History>(`/v2/bot/clans/${encodeURIComponent(ref.tag)}/capital-trophy-history`,{months,...(season==="current"?{}:{season})},deadline)})));
  for(const value of result){if(value.status==="rejected"){failed++;continue;}const row=value.value;
   if(!row.weeks.length||row.weeks.length!==row.values.length||row.sampleDates.length!==row.values.length||row.values.some(n=>n!==null&&(!Number.isSafeInteger(n)||n<0)))throw new CommandInputError("Capital history could not be validated.");
   if(!weeks.length)weeks=row.weeks;else if(JSON.stringify(weeks)!==JSON.stringify(row.weeks))throw new CommandInputError("The history window changed. Refresh the chart.");
   rows.push(row);
  }
 }
 failed=refs.length-rows.length;
 if(!weeks.length)throw new CommandInputError("Capital trophy history is unavailable. Try again later.");
 const latest=(values:Array<number|null>)=>values.findLast((value):value is number=>value!==null)??-1;
 const selected=rows.filter(row=>latest(row.values)>=0).sort((a,b)=>latest(b.values)-latest(a.values)||a.tag.localeCompare(b.tag)).slice(0,limit);
 const largest=Math.max(1,...selected.flatMap(row=>row.values.filter((v):v is number=>v!==null))),colors=["#55c8b0","#f6d882","#95b6ff","#f59ec7","#b8a0ef","#f6aa75","#91cf77","#71d7ed","#e69da4","#c6c4bc"];
 const {posterArtwork,renderPosterSvg}=await import("./legend-poster");
 const x=(i:number)=>weeks.length===1?790:140+i*1300/(weeks.length-1),y=(v:number)=>780-v/largest*520;
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1100"><rect width="1600" height="1100" fill="#101923"/><image href="${posterArtwork.logo}" x="1280" y="45" width="230" height="85"/>`+text(75,100,"Capital trophies · weekly observations",40,"#f6d882")+text(75,150,`${weeks[0]} — ${weeks.at(-1)} · Last recorded snapshot in each Friday–Thursday week`,22);
 for(let tick=0;tick<=4;tick++){const py=780-tick*130;svg+=`<path d="M140 ${py}H1440" stroke="#344454"/>`+text(45,py+8,Math.round(largest*tick/4).toLocaleString("en"),18);}
 weeks.forEach((week,index)=>{if(index%Math.max(1,Math.ceil(weeks.length/6))===0||index===weeks.length-1)svg+=text(x(index)-35,825,week.slice(5),18);});
 selected.forEach((row,index)=>{let path="",pen=false;row.values.forEach((value,day)=>{if(value===null){pen=false;return;}path+=`${pen?"L":"M"}${x(day)} ${y(value)} `;pen=true;svg+=`<circle cx="${x(day)}" cy="${y(value)}" r="4" fill="${colors[index]}"/>`;});svg+=`<path d="${path}" fill="none" stroke="${colors[index]}" stroke-width="3"/>`+text(90+(index%2)*740,875+Math.floor(index/2)*30,row.name.slice(0,40),21,colors[index]);});
 if(!selected.length)svg+=text(370,520,"No recorded Capital trophy snapshots",32);
 svg+=text(75,1060,`Missing weeks stay gaps · Current week is partial · ${failed} clan requests unavailable`,22)+"</svg>";
 const details=selected.map(row=>{const index=row.values.findLastIndex(value=>value!==null);return `${row.name.replace(/[<@`*_~]/gu,"").slice(0,35)}: ${row.values[index]} (recorded ${row.sampleDates[index]})`;}).join("\n");
 const response=legacyMessage({allowed_mentions:{parse:[]},content:`Capital trophies · weekly observations\n${details||"No snapshots recorded."}\nMissing weeks stay gaps; current week is partial. ${failed} clan requests unavailable.`,components:custom?[]:[actionRow({type:2,style:2,label:"Refresh",custom_id:`ck:page:gt:${invokingUserId(ctx)}:capitalTrophies:${season}:${months}:${limit}:0`})]});
 response.data!.attachments=[];response.data!.__files=[{name:"capital-trophy-history.png",bytes:await renderPosterSvg(svg)}];return response;
}
