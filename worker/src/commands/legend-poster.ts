import { Resvg, initWasm } from "@resvg/resvg-wasm";
import wasm from "@resvg/resvg-wasm/index_bg.wasm";
import blogger from "../assets/legend-poster/blogger.ttf";
import clash from "../assets/legend-poster/clash.ttf";
import sword from "../assets/legend-poster/sword.png";
import shield from "../assets/legend-poster/shield.png";
import trophy from "../assets/legend-poster/trophy.png";
import league from "../assets/legend-poster/legend.png";
import star from "../assets/legend-poster/star.png";
import logo from "../assets/legend-poster/clashking.png";
import prince from "../assets/legend-poster/league-prince.png";
import heart from "../assets/legend-poster/heart.png";
import type { Player } from "./game-common";
import type { LegendSeasonDay, LegendSeasonSummary } from "./legend-season";
import { posterTownHalls } from "./legend-poster-halls";
import { legendPosterSvg } from "./legend-poster-layout";

let initialized: Promise<void> | undefined;
function dataUri(buffer:ArrayBuffer|Uint8Array){
  const bytes=buffer instanceof Uint8Array?buffer:new Uint8Array(buffer);let binary="";
  for(let offset=0;offset<bytes.length;offset+=8192)binary+=String.fromCharCode(...bytes.subarray(offset,offset+8192));
  return `data:image/png;base64,${btoa(binary)}`;
}
const images={sword:dataUri(sword),shield:dataUri(shield),trophy:dataUri(trophy),league:dataUri(league),star:dataUri(star),logo:dataUri(logo),prince:dataUri(prince)};

async function remoteImage(raw:string|undefined){
  if(!raw)return undefined;
  try{
    const url=new URL(raw);
    if(url.protocol!=="https:"||!["cdn.discordapp.com","api-assets.clashofclans.com","assets.clashk.ing"].includes(url.hostname)||url.username||url.password||url.port)return undefined;
    // Workers do not implement redirect:"error". Manual plus the ok check
    // rejects redirects without following them beyond the allowed asset hosts.
    const response=await fetch(url,{redirect:"manual",signal:AbortSignal.timeout(2500)});
    if(!response.ok||Number(response.headers.get("content-length"))>512000)return undefined;
    const reader=response.body?.getReader();if(!reader)return undefined;
    const chunks:Uint8Array[]=[];let size=0;
    while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>512000){await reader.cancel();return undefined;}chunks.push(value);}
    const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
    return dataUri(bytes);
  }catch{return undefined;}
}
export const posterRemoteImage=remoteImage;
export const posterArtwork={...images,heart:dataUri(heart)};
export const posterTownHall=(level:number)=>posterTownHalls[level-1]?dataUri(posterTownHalls[level-1]!):undefined;
export async function renderPosterSvg(svg:string,extraFonts:readonly ArrayBuffer[]=[]){
  initialized??=initWasm(wasm);
  await initialized;
  const renderer=new Resvg(svg,{font:{fontBuffers:[new Uint8Array(blogger),new Uint8Array(clash),...extraFonts.map(font=>new Uint8Array(font))],defaultFontFamily:"Blogger Sans"},fitTo:{mode:"original"}});
  try{const result=renderer.render();try{return new Uint8Array(result.asPng());}finally{result.free();}}finally{renderer.free();}
}

export async function legendPoster(input:{player:Pick<Player,"name"|"tag">&Partial<Player>&{globalRank?:number;location?:{name:string;countryCode?:string}};season:LegendSeasonSummary;days:LegendSeasonDay[];selectedDay:string;today:string;townHallIcon?:string;favoriteIcons?:Record<number,string>}){
  initialized??=initWasm(wasm);
  const countryCode=input.player.location?.countryCode;
  const [,hall,badge,flag,favoriteImages]=await Promise.all([initialized,remoteImage(input.townHallIcon),remoteImage(input.player.clan?.badgeUrls?.small),
    remoteImage(countryCode&&/^[A-Z]{2}$/u.test(countryCode)?`https://assets.clashk.ing/country-flags/${countryCode.toLowerCase()}.png`:undefined),
    Promise.all((input.season.favorites??[]).map(async item=>[item.id,await remoteImage(input.favoriteIcons?.[item.id])] as const))]);
  const localHall=posterTownHalls[(input.player.townHallLevel??0)-1];
  return renderPosterSvg(legendPosterSvg(input,{
    ...images,heart:dataUri(heart),hallImage:hall??(localHall?dataUri(localHall):undefined),
    badge,flag,favoriteImages:Object.fromEntries(favoriteImages),
  }));
}
