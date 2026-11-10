/** One quiet chart language, sized for a Discord image on a phone. */
export interface ChartSeries { name:string; values:Array<number|null>; headline?:number|null; icon?:string }
interface ChartBase { title:string; subtitle:string; logo:string; note?:string; valueSuffix?:string; icon?:string; accent?:string }
export interface BarChartInput extends ChartBase {rows:Array<{name:string;value:number;icon?:string}>}
export interface LineChartInput extends ChartBase {labels:string[];series:ChartSeries[]; axis?:{min:number;max:number;ticks:Array<{value:number;label:string;icon?:string;color?:string}>}; formatValue?:(value:number)=>string; stepped?:boolean}
const colors=['#0a84ff','#30d5a0','#ffb340','#bf8cff','#ff7487','#64d2ff','#ffd460','#acdc80','#e995cf','#b6c3df'];
const ink='#f5f5f7',muted='#98989f',grid='#27272a';
const xml=(v:string)=>v.replace(/[&<>"']/gu,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'})[c]!);
const text=(x:number,y:number,value:string,size=26,color=muted,anchor='start',weight=400)=>`<text x="${x}" y="${y}" text-anchor="${anchor}" fill="${color}" font-family="Inter Variable" font-size="${size}" font-weight="${weight}" letter-spacing="${size>=38?-.8:0}">${xml(value)}</text>`;
const short=(value:string,length=32)=>[...value].length>length?[...value].slice(0,length-1).join('')+'…':value;
export const chartNumber=(value:number)=>new Intl.NumberFormat('en',{notation:Math.abs(value)>=10000?'compact':'standard',maximumFractionDigits:1}).format(value);
function scale(value:number){
 const maximum=Math.max(1,Math.ceil(value)),raw=maximum/4,magnitude=10**Math.floor(Math.log10(raw));
 const step=Math.max(1,([1,2,5,10].find(n=>n*magnitude>=raw)??10)*magnitude);
 const max=step*Math.ceil(maximum/step);
 return {max,ticks:Array.from({length:Math.round(max/step)+1},(_,i)=>i*step)};
}
const axisNumber=(value:number)=>{
 for(const [unit,suffix] of [[1e9,'B'],[1e6,'M'],[1e3,'K']] as const)if(value>=unit&&value%unit===0)return `${value/unit}${suffix}`;
 return new Intl.NumberFormat('en',{maximumFractionDigits:0}).format(value);
};
function frame(input:ChartBase,height:number){
 return `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="${height}" viewBox="0 0 1280 ${height}"><title>${xml(input.title)}</title><desc>${xml(input.subtitle)}</desc><rect width="1280" height="${height}" fill="#000000"/>${input.icon?`<image href="${input.icon}" x="64" y="35" width="48" height="48"/>`:""}${text(input.icon?130:64,76,short(input.title,47),42,ink,'start',600)}${text(64,120,short(input.subtitle,78),25)}<image href="${input.logo}" x="1105" y="46" width="111" height="41" preserveAspectRatio="xMidYMid meet"/>`;
}
const finish=(input:ChartBase,height:number)=>`${input.note?text(64,height-30,input.note,21):''}</svg>`;
export function barChartSvg(input:BarChartInput){
 const pitch=70,height=Math.max(330,210+input.rows.length*pitch+(input.note?32:0)),left=405,right=1050,width=right-left;
 const max=Math.max(1,...input.rows.map(row=>row.value));
 let svg=frame(input,height);
 input.rows.forEach((row,index)=>{
  const y=187+index*pitch,length=width*row.value/max;
  svg+=`${row.icon?`<image href="${row.icon}" x="64" y="${y-6}" width="38" height="38"/>`:""}`+text(row.icon?116:64,y+21,short(row.name,18),30,ink);
  if(row.value>0)svg+=`<rect x="${left}" y="${y}" width="${length}" height="26" rx="${Math.min(8,length/2)}" fill="${input.accent??colors[0]}"/>`;
  svg+=text(1216,y+23,chartNumber(row.value)+(input.valueSuffix??""),32,ink,'end',500);
 });
 if(!input.rows.length)svg+=text(64,225,'No data for this period',28);
 return svg+finish(input,height);
}
export function chartDate(value:string,monthOnly=false){
 if(value==='current')return 'Current season';
 const date=new Date(value.length===7?`${value}-01T12:00:00Z`:`${value}T12:00:00Z`);
 return Number.isFinite(+date)?new Intl.DateTimeFormat('en',monthOnly?{month:'short',year:'numeric',timeZone:'UTC'}:{month:'short',day:'numeric',timeZone:'UTC'}).format(date):value;
}
interface Point {
  x: number;
  y: number;
}
function curve(points: Point[]) {
  if (!points.length) return "";
  if (points.length === 1) return `M${points[0]!.x},${points[0]!.y}`;
  const slopes = points
    .slice(1)
    .map(
      (point, index) =>
        (point.y - points[index]!.y) / (point.x - points[index]!.x),
    );
  const tangents = points.map((_, index) =>
    index === 0
      ? slopes[0]!
      : index === points.length - 1
        ? slopes.at(-1)!
        : slopes[index - 1]! * slopes[index]! <= 0
          ? 0
          : 2 / (1 / slopes[index - 1]! + 1 / slopes[index]!),
  );
  // Monotone Hermite curves preserve observed extrema rather than overshooting
  // into invented peaks. Call separately per segment so missing data stays a gap.
  let path = `M${points[0]!.x},${points[0]!.y}`;
  for (let index = 0; index < points.length - 1; index++) {
    const from = points[index]!,
      to = points[index + 1]!,
      distance = (to.x - from.x) / 3;
    path += ` C${from.x + distance},${from.y + distance * tangents[index]!} ${to.x - distance},${to.y - distance * tangents[index + 1]!} ${to.x},${to.y}`;
  }
  return path;
}
function segments(series:ChartSeries,x:(index:number)=>number,y:(value:number)=>number){
 const result:Point[][]=[];let points:Point[]=[];
 series.values.forEach((value,index)=>{
  if(value===null||!Number.isFinite(value)){if(points.length)result.push(points);points=[];}
  else points.push({x:x(index),y:y(value)});
 });
 if(points.length)result.push(points);
 return result;
}
function marks(series:ChartSeries,x:(index:number)=>number,y:(value:number)=>number,color:string,bottom:number,areaId?:string,stepped=false){
 let svg='';
 for(const points of segments(series,x,y)){
  const path=stepped?points.map((p,i)=>i===0?`M${p.x},${p.y}`:`H${p.x}V${p.y}`).join(" "):curve(points),first=points[0]!,last=points.at(-1)!;
  if(areaId&&points.length>1)svg+=`<path d="${path} L${last.x},${bottom} L${first.x},${bottom} Z" fill="url(#${areaId})"/>`;
  svg+=`<path d="${path}" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`;
  // Isolated observations remain visible; no line crosses a missing period.
  if(points.length===1)svg+=`<circle cx="${last.x}" cy="${last.y}" r="5" fill="${color}"/>`;
 }
 const last=series.values.at(-1);
 if(last!==null&&last!==undefined)svg+=`<circle cx="${x(series.values.length-1)}" cy="${y(last)}" r="5" fill="${color}" stroke="#000" stroke-width="2"/>`;
 return svg;
}
const area=(id:string,color:string)=>`<linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".18"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient>`;
export function lineChartSvg(input:LineChartInput){
 const automatic=scale(Math.max(0,...input.series.flatMap(s=>s.values.filter((v):v is number=>v!==null&&Number.isFinite(v)))));
 // Many overlapping series stop being readable. Give each clan its own plot
 // with the same vertical scale, so visual comparison stays honest.
 const min=input.axis?.min??0,max=input.axis?.max??automatic.max;
 const ticks:Array<{value:number;label:string;icon?:string;color?:string}>=input.axis?.ticks??automatic.ticks.map(value=>({value,label:axisNumber(value)+(input.valueSuffix??"")}));
 if(input.series.length>3&&!input.axis)return multiples(input,max);
 const dense=input.series.length>3,top=dense?190+Math.ceil(input.series.length/2)*54:260,bottom=top+372,height=bottom+108+(input.note?32:0),left=64,right=input.axis?1010:1110;
 const x=(i:number)=>input.labels.length<=1?(left+right)/2:left+(right-left)*i/(input.labels.length-1);
 const y=(v:number)=>bottom-(v-min)/(max-min)*(bottom-top);
 let svg=frame(input,height)+`<defs>${area('area',colors[0]!)}</defs>`;
 // The clan selector supports 24 series; keep every league line colored even
 // after the palette repeats. Numeric trends already use separate clan plots.
 input.series.forEach((series,index)=>{
  const col=dense?64+(index%2)*576:64+index*(1152/Math.max(1,input.series.length));
  const base=dense?185+Math.floor(index/2)*54:183;
  if(series.icon)svg+=`<image href="${series.icon}" x="${col}" y="${base-28}" width="34" height="34"/>`;
  svg+=text(series.icon?col+46:col,base,short(series.name,input.series.length===1?48:22),27,colors[index%colors.length], 'start',500);
  const last=series.headline!==undefined?series.headline:series.values.at(-1);
  svg+=text(dense?col+535:col,dense?base:230,last===null||last===undefined?'—':input.formatValue?.(last)??chartNumber(last)+(input.valueSuffix??""),input.formatValue?28:38,ink,dense?'end':'start',600);
 });
 for(const tick of ticks){
  const py=y(tick.value);
  if(tick.icon)svg+=`<image href="${tick.icon}" x="${right+17}" y="${py-16}" width="32" height="32"/>`;
  svg+=`<path d="M${left} ${py}H${right}" stroke="${grid}" stroke-width="1"/>`+text(1216,py+8,tick.label,input.axis?21:23,tick.color??muted,'end');
 }
 const xTicks=Math.min(5,input.labels.length);
 for(let i=0;i<xTicks;i++){
  const index=xTicks<=1?0:Math.round(i*(input.labels.length-1)/(xTicks-1));
  svg+=text(x(index),bottom+45,input.labels[index]!,24,muted,index===0?'start':index===input.labels.length-1?'end':'middle');
 }
 input.series.forEach((series,index)=>svg+=marks(series,x,y,colors[index%colors.length]!,bottom,input.series.length===1&&!input.stepped?'area':undefined,input.stepped));
 if(!input.series.length||!input.series.some(series=>series.values.some(v=>v!==null)))svg+=text(64,435,'No data for this period',28);
 return svg+finish(input,height);
}
function multiples(input:LineChartInput,max:number){
 const pitch=236,columns=2,height=190+Math.ceil(input.series.length/columns)*pitch+(input.note?32:0);
 let svg=frame(input,height)+'<defs>'+input.series.map((_,i)=>area(`area${i}`,colors[i%colors.length]!)).join('')+'</defs>';
 input.series.forEach((series,i)=>{
  const left=64+(i%columns)*610,right=left+520,top=225+Math.floor(i/columns)*pitch,bottom=top+123;
  const x=(index:number)=>input.labels.length<=1?(left+right)/2:left+(right-left)*index/(input.labels.length-1),y=(v:number)=>bottom-v/max*(bottom-top);
  const color=colors[i%colors.length]!;
  if(series.icon)svg+=`<image href="${series.icon}" x="${left}" y="${top-52}" width="32" height="32"/>`;
  svg+=text(series.icon?left+42:left,top-25,short(series.name,20),27,color,'start',500);
  const last=series.headline!==undefined?series.headline:series.values.at(-1);
  svg+=text(right,top-25,last===null||last===undefined?'—':chartNumber(last)+(input.valueSuffix??""),30,ink,'end',500);
  for(let t=0;t<=2;t++)svg+=`<path d="M${left} ${y(max*t/2)}H${right}" stroke="${grid}" stroke-width="1"/>`;
  svg+=marks(series,x,y,color,bottom,`area${i}`);
  if(input.labels.length){svg+=text(left,bottom+32,input.labels[0]!,22)+text(right,bottom+32,input.labels.at(-1)!,22,muted,'end');}
 });
 return svg+finish(input,height);
}
