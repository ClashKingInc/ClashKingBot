import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import type { CommandContext } from "./types";
export const dailyMetrics={activity:"Recorded activity events",troopLevels:"Troop / spell levels gained",heroLevels:"Hero / pet levels gained",equipmentLevels:"Equipment levels gained",townhallLevels:"Town Hall levels gained",bestTrophies:"Personal-best trophy gains",experienceLevels:"Experience levels gained",nameChanges:"Name changes",warPreferenceChanges:"War preference changes",donated:"Troops donated",received:"Troops received",clanGames:"Clan Games points",capitalDonated:"Capital Gold donated",clanMoves:"Join / leave events"};
interface Data { metric:string; basis:"recorded_clan"|"latest_stored_members"; dates:string[]; series:Array<{tag:string;values:number[]}> }
const xml=(value:string)=>value.replace(/[&<>"']/gu,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"})[c]!);
const text=(x:number,y:number,value:string,size=22,color="#c6d0e0")=>`<text x="${x}" y="${y}" fill="${color}" font-size="${size}" font-family="Blogger Sans">${xml(value)}</text>`;
export async function graphDaily(ctx:CommandContext){
 const metric=stringOption(ctx,"attribute")??"",days=Number(ctx.options.get("days")?.value??30),limit=Number(ctx.options.get("limit")?.value??5),raw=stringOption(ctx,"clans")??"";
 if(!Object.hasOwn(dailyMetrics,metric)||!Number.isInteger(days)||days<1||days>180||!Number.isInteger(limit)||limit<1||limit>10)throw new CommandInputError("Choose a metric, 1–180 days and 1–10 clans.");
 const refs=raw?[...new Set(raw.split(/[\s,]+/u).filter(Boolean).map(tag=>normalizeTag(tag,ctx.locale)))].map(tag=>({tag,name:tag})):await ctx.services.api.get<Array<{tag:string;name:string}>>(`/v2/server/${requireGuildId(ctx)}/clans-basic`);
 if(!refs.length||refs.length>50)throw new CommandInputError("Choose 1–50 clans or configure the server's family.");
 let data:Data;try{data=await ctx.services.api.post<Data>("/v2/bot/clans/daily-stats",{clans:refs.map(ref=>ref.tag),metric,days});}catch{throw new CommandInputError("Daily observations are unavailable. Try again later.");}
 if(data.dates.length!==days||data.series.some(row=>row.values.length!==days||row.values.some(value=>!Number.isSafeInteger(value)||value<0)))throw new CommandInputError("Daily observations could not be validated.");
 const names=new Map(refs.map(ref=>[ref.tag,ref.name]));
 const rows=data.series.map(row=>({...row,name:names.get(row.tag)??row.tag,total:row.values.reduce((sum,value)=>sum+value,0)})).sort((a,b)=>b.total-a.total||a.tag.localeCompare(b.tag)).slice(0,limit);
 if(rows.some(row=>!Number.isSafeInteger(row.total)))throw new CommandInputError("The daily total exceeds the supported numeric range.");
 const largest=Math.max(1,...rows.flatMap(row=>row.values));
 const colors=["#55c8b0","#f6d882","#95b6ff","#f59ec7","#b8a0ef","#f6aa75","#91cf77","#71d7ed","#e69da4","#c6c4bc"];
 const basis=data.basis==="recorded_clan"?"Clan recorded on each event":"Latest stored clan membership";
 const {posterArtwork,renderPosterSvg}=await import("./legend-poster");
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1100"><rect width="1600" height="1100" fill="#101923"/><image href="${posterArtwork.logo}" x="1280" y="45" width="230" height="85"/>`+text(75,100,dailyMetrics[metric as keyof typeof dailyMetrics],42,"#f6d882")+text(75,150,`${data.dates[0]} — ${data.dates.at(-1)} · UTC daily totals`,25)+text(75,190,basis,22);
 const x=(index:number)=>days===1?790:140+index*1300/(days-1),y=(value:number)=>780-value/largest*520;
 for(let tick=0;tick<=4;tick++){const py=780-tick*130;svg+=`<path d="M140 ${py}H1440" stroke="#344454"/>`+text(40,py+8,new Intl.NumberFormat("en",{notation:"compact"}).format(largest*tick/4),18);}
 data.dates.forEach((date,index)=>{if(index%Math.max(1,Math.ceil(days/6))===0||index===days-1)svg+=text(x(index)-35,825,date.slice(5),18);});
 rows.forEach((row,index)=>{const line=row.values.map((value,day)=>`${day?"L":"M"}${x(day)} ${y(value)}`).join(" ");svg+=`<path d="${line}" fill="none" stroke="${colors[index]}" stroke-width="3"/>`;if(days===1)svg+=`<circle cx="${x(0)}" cy="${y(row.values[0]!)}" r="5" fill="${colors[index]}"/>`;svg+=text(90+(index%2)*740,875+Math.floor(index/2)*30,row.name.slice(0,40),21,colors[index]);});
 svg+=text(75,1060,"Today is partial · Zero means no recorded events, not proof of no activity",22)+"</svg>";
 const response=legacyMessage({allowed_mentions:{parse:[]},content:`${dailyMetrics[metric as keyof typeof dailyMetrics]} · ${days} UTC days · ${basis}.\n${rows.map(row=>`${row.name.replace(/[<@`*_~]/gu,"").slice(0,40)}: ${row.total.toLocaleString("en")}`).join(" · ")}\nToday is partial. Zero means no recorded events.`,components:raw?[]:[actionRow({type:2,style:2,label:"Refresh",custom_id:`ck:page:gd:${invokingUserId(ctx)}:${metric}:${days}:${limit}:0`})]});
 response.data!.attachments=[];response.data!.__files=[{name:"daily-clan-statistics.png",bytes:await renderPosterSvg(svg)}];return response;
}
