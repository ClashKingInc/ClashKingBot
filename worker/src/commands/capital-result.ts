import background from "../assets/raidweek.png";
import { posterRemoteImage, renderPosterSvg } from "./legend-poster";
import { raidMedals, type Raid } from "./raid-data";

const xml=(value:unknown)=>String(value).replace(/[&<>"']/gu,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"})[char]!);
const bytes=new Uint8Array(background);
let binary="";
for(let offset=0;offset<bytes.length;offset+=8192)binary+=String.fromCharCode(...bytes.subarray(offset,offset+8192));
const backdrop=`data:image/jpeg;base64,${btoa(binary)}`;

export async function capitalResult(raid:Raid,clan:{name:string;badgeUrls?:{small?:string;medium?:string}}){
 const badge=await posterRemoteImage(clan.badgeUrls?.medium??clan.badgeUrls?.small);
 const {offense,defense}=raidMedals(raid);
 const text=(x:number,y:number,value:unknown,size=30,anchor="start")=>`<text x="${x}" y="${y}" text-anchor="${anchor}" dominant-baseline="central" font-family="Supercell-Magic" font-size="${size}" fill="white" stroke="black" stroke-width="${size===60?4:2}" paint-order="stroke">${xml(value)}</text>`;
 const completed=(raid.attackLog??[]).filter(entry=>entry.districtCount!==undefined&&entry.districtsDestroyed===entry.districtCount).length;
 return renderPosterSvg(`<svg xmlns="http://www.w3.org/2000/svg" width="1448" height="1062"><image href="${backdrop}" width="1448" height="1062"/>${badge?`<image href="${badge}" x="1125" y="135" width="200" height="200"/>`:""}${text(1225,117,clan.name,Math.min(30,570/Math.max(clan.name.length,1)),"middle")}${text(750,250,offense+defense,60,"middle")}${text(155,585,raid.capitalTotalLoot)}${text(870,585,completed)}${text(155,817,raid.totalAttacks)}${text(870,817,raid.enemyDistrictsDestroyed)}${text(550,370,offense,25)}${text(1245,370,defense,25)}${text(25,35,raid.startTime.slice(0,8).replace(/^(\d{4})(\d{2})(\d{2})$/u,"$1-$2-$3"))}${raid.state==="ongoing"?text(25,1015,"Estimated medals (raid ongoing)",22):""}</svg>`);
}
