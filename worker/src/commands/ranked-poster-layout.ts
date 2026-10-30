/** Shared bot/app Ranked composition. Runtime adapters load images and rasterize. */
import { posterTextWidth } from './legend-poster-layout';

export interface RankedPosterHit { stars:number; destructionPercentage:number; trophies:number; creationTime:string; opponentName?:string }
export interface RankedPosterMember { name:string; tag:string; trophies:number; attacks:number; wins:number; losses:number; defenses?:number; placement:number }
export interface RankedPosterInput { player:{name:string;tag:string;townHallLevel:number;clan?:{name:string}}; league:string; season:string; member:RankedPosterMember; members:readonly RankedPosterMember[]; attacks:RankedPosterHit[]; defenses:RankedPosterHit[]; cutoffs?:{promotion?:number;demotion?:number} }
export interface RankedPosterArtwork { logo:string; trophy:string; sword:string; shield:string; star:string; heart:string; badge?:string; hall?:string; clan?:string }
const xml=(value:unknown)=>String(value).replace(/[&<>"']/gu,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"})[c]!);
const text=(x:number,y:number,value:unknown,size=24,color="#fafafa",extra="")=>`<text x="${x}" y="${y}" fill="${color}" font-family="Blogger Sans" font-size="${size}" ${extra}>${xml(value)}</text>`;
const image=(uri:string|undefined,x:number,y:number,w:number,h=w,extra="")=>uri?`<image href="${uri}" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="xMidYMid meet" ${extra}/>`:"";
export function rankedPosterSvg(input:RankedPosterInput,images:RankedPosterArtwork):string {
 const {player,league,member,members,attacks,defenses}=input;
 const {badge,hall,clan}=images;
 const art=images;
 // The badge, not a skin, is the hero artwork. The tint follows its league
 // family; every value/chart is computed from this player's actual logs.
 const accent=/electro/i.test(league)?"#63b9ef":/dragon/i.test(league)?"#bc75ef":/pekka/i.test(league)?"#ca80dc":/titan/i.test(league)?"#f5c568":"#83b7ee";
 const positiveColor="#14A37F",negativeColor="#D90709";
 const total=(logs:RankedPosterHit[])=>logs.reduce((sum,hit)=>sum+hit.trophies,0);
 const average=(logs:RankedPosterHit[],key:"trophies"|"destructionPercentage")=>logs.length?(logs.reduce((sum,hit)=>sum+hit[key],0)/logs.length).toFixed(1):"—";
 // The ranked season ID is its UTC start instant, not its closing date.
 // Match the app's seven-day period; never infer dates from the current week.
 const start=new Date(Number(input.season)*1000),end=new Date(start.getTime()+7*86400000);
 const dateLabel=(date:Date,year:boolean)=>date.toLocaleDateString("en-US",{month:"short",day:"numeric",...(year?{year:"numeric" as const}:{}),timeZone:"UTC"});
 const date=`${dateLabel(start,start.getUTCFullYear()!==end.getUTCFullYear())} – ${dateLabel(end,true)}`;
 const rankingX=Math.min(900,Math.max(176+posterTextWidth(player.name.slice(0,35),40),(clan?212:176)+posterTextWidth(player.clan?.name??player.tag,25))+64);
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1100" viewBox="0 0 1600 1100"><defs>
 <radialGradient id="glow"><stop stop-color="${accent}" stop-opacity=".32"/><stop offset=".18" stop-color="${accent}" stop-opacity=".1"/><stop offset=".5" stop-color="${accent}" stop-opacity=".035"/><stop offset="1" stop-color="${accent}" stop-opacity="0"/></radialGradient>
 </defs><rect width="1600" height="1100" fill="#000"/><circle cx="1360" cy="144" r="1450" fill="url(#glow)"/>
 ${image(badge,1240,24,240)}${image(art.logo,48,38,76)}
 <text x="146" y="76" dominant-baseline="central" fill="#f5f2e8" font-family="Supercell-Magic" font-size="38">RANKED SEASON<tspan dx="18" dominant-baseline="central" font-family="Blogger Sans" font-size="24" fill="#a1a1aa">(${xml(date)})</tspan></text>
 ${image(hall,48,142,106,112)}
 ${text(176,176,player.name.slice(0,35),40,"#fff",'font-weight="700"')}
 ${image(clan,176,190,28)}${text(clan?212:176,213,player.clan?.name??player.tag,25,"#d4d4d8")}
 ${text(176,246,league,20,"#a1a1aa")}${text(rankingX,202,member.placement > 0 ? `#${member.placement}` : '—',56,"#fafafa",'font-weight="700"')}
 ${members.length > 0 ? text(rankingX,230,`of ${members.length} players`,26,"#a1a1aa") : ''}`;
 const metrics=[
  ["Current trophies",member.trophies.toLocaleString("en"),art.trophy,"#ffffff"],
  ["Attacks",String(member.attacks),art.sword,"#ffffff"],
  ["Win rate",member.attacks?`${(member.wins/member.attacks*100).toFixed(1)}%`:"—",art.star,"#ffffff"],
  ["Average offense",average(attacks,"trophies"),art.sword,"#ffffff"],
 ];
 metrics.forEach(([label,value,icon,color],i)=>{const center=80+180+i*360;svg+=image(icon,center-124,317,48)+text(center-56,321,label,23,"#a1a1aa")+text(center-56,384,value,56,color,'font-weight="700"');});
 const stars=(logs:RankedPosterHit[],x:number,title:string,color:string)=>{
  svg+=image(title==="Offense"?art.sword:art.shield,x,426,28)+text(x+40,448,title,26)+text(x+710,448,`${total(logs)} trophies · ${average(logs,"destructionPercentage")}% avg.`,20,color,'text-anchor="end"');
  for(let star=3;star>=0;star--){const y=472+(3-star)*35,count=logs.filter(hit=>hit.stars===star).length,ratio=logs.length?count/logs.length:0;
   for(let s=0;s<3;s++)svg+=image(art.star,x+20+s*23,y-15,21,21,s>=star?'opacity=".13"':"");
   svg+=`<rect x="${x+102}" y="${y-10}" width="456" height="12" rx="6" fill="#0d121c"/><rect x="${x+102}" y="${y-10}" width="${ratio*456}" height="12" rx="6" fill="${color}"/>`;
   svg+=text(x+710,y+2,`${count} · ${(ratio*100).toFixed(0)}%`,19,"#d4d4d8",'text-anchor="end"');
  }
 };
 stars(attacks,48,"Offense",positiveColor);stars(defenses,830,"Defense",negativeColor);
 const events=[...attacks.map(hit=>({...hit,kind:"attack"})),...defenses.map(hit=>({...hit,kind:"defense"}))].filter(hit=>Number.isFinite(Date.parse(hit.creationTime))).sort((a,b)=>Date.parse(a.creationTime)-Date.parse(b.creationTime));
 // Anchor the recorded segment to actual trophies, including when older
 // battles are absent. Cutoffs and the curve must use the same score axis.
 const initial=member.trophies-total(events);
 let running=initial;const values=events.map(hit=>({value:running+=hit.trophies,hit}));
 const boundaries=[
  {label:"Promotion cutoff",value:input.cutoffs?.promotion,color:positiveColor},
  {label:"Demotion cutoff",value:input.cutoffs?.demotion,color:negativeColor},
 ].filter((entry):entry is {label:string;value:number;color:string}=>typeof entry.value==="number"&&Number.isFinite(entry.value));
 const left=126,right=1508,top=666,bottom=986,min=Math.min(0,initial,...values.map(point=>point.value),...boundaries.map(entry=>entry.value)),peak=Math.max(1,initial,...values.map(point=>point.value),...boundaries.map(entry=>entry.value)),max=peak+Math.max(1,(peak-min)*.08);
 const py=(n:number)=>bottom-(bottom-top)*(n-min)/(max-min);
 // Keep labels below their cutoff and mask the chart behind them. Reserve
 // their rectangles so nearby point values cannot collide with the text.
 const cutoffLabels=boundaries.map((entry,index)=>{
  const y=py(entry.value),label=`${entry.label} · ${entry.value.toLocaleString("en")}`;
  const width=posterTextWidth(label,20)+24;
  let boxY=y+8;
  if(boxY+32>bottom)boxY=y-40;
  if(index>0&&Math.abs(y-py(boundaries[0]!.value))<45)boxY=y-40;
  return {...entry,y,label,width,x:right-width,boxY};
 });
 for(let i=0;i<=4;i++){const value=min+(max-min)*i/4,y=py(value);svg+=`<path d="M${left} ${y}H${right}" stroke="#27272a"/>`+text(left-15,y+5,Math.round(value),17,"#71717a",'text-anchor="end"');}
 if(values.length){
  const px=(i:number)=>left+(right-left)*(i+1)/values.length,zero=py(0);
  const line=`M${left} ${py(initial)} `+values.map((v,i)=>`L${px(i)} ${py(v.value)}`).join(" ");
  // Match Legends: cumulative results, not league identity or hit type,
  // determine graph colors. Crossing segments change color exactly at zero.
  svg+=`<defs><clipPath id="positive"><rect x="${left-10}" y="${top-10}" width="${right-left+20}" height="${zero-top+10}"/></clipPath><clipPath id="negative"><rect x="${left-10}" y="${zero}" width="${right-left+20}" height="${bottom-zero+10}"/></clipPath></defs>`;
  for(const [clip,color] of [["positive",positiveColor],["negative",negativeColor]])svg+=`<g clip-path="url(#${clip})"><path d="${line} L${right} ${zero}Z" fill="${color}" opacity=".1"/><path d="${line}" fill="none" stroke="${color}" stroke-width="3.5"/></g>`;
  values.forEach((v,i)=>{const x=px(i),y=py(v.value),color=v.value>=0?positiveColor:negativeColor;svg+=`<circle cx="${x}" cy="${y}" r="4" fill="#000" stroke="${color}" stroke-width="2"/>`;
   const labelWidth=posterTextWidth(String(v.value),17),labelTop=y-32;
   const overlapsCutoff=cutoffLabels.some(box=>x+labelWidth/2>box.x&&x-labelWidth/2<right&&labelTop+22>box.boxY&&labelTop<box.boxY+32);
   if(!overlapsCutoff&&(i%Math.max(1,Math.ceil(values.length/10))===0||i===values.length-1))svg+=text(x,y-14,v.value,17,"#fafafa",'text-anchor="middle"');
  });
  for(const i of new Set([0,Math.floor((values.length-1)/2),values.length-1]))svg+=text(px(i),1016,new Date(values[i]!.hit.creationTime).toLocaleDateString("en-US",{month:"short",day:"numeric",timeZone:"UTC"}),18,"#a1a1aa",'text-anchor="middle"');
 }else svg+=text(800,845,"No recorded battles",28,"#a1a1aa",'text-anchor="middle"');
 cutoffLabels.forEach(entry=>{
  svg+=`<path d="M${left} ${entry.y}H${right}" stroke="${entry.color}" stroke-width="1.5" stroke-dasharray="8 7" opacity=".8"/>`;
  svg+=`<rect x="${entry.x}" y="${entry.boxY}" width="${entry.width}" height="32" rx="6" fill="#0d1218"/><rect x="${entry.x}" y="${entry.boxY+8}" width="3" height="16" rx="1.5" fill="${entry.color}"/>`;
  svg+=text(right-12,entry.boxY+23,entry.label,20,"#fafafa",'text-anchor="end"');
 });
 svg+=image(art.heart,1350,1057,22)+text(1552,1075,"Made by Clashking",20,"#a1a1aa",'text-anchor="end"')+"</svg>";
 return svg;
}
