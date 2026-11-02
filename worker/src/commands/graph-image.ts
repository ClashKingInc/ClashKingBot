import { graphMetricIcons } from "./graph-data";
import inter from '../assets/graph/Inter.ttf';
import { renderPosterSvg } from './legend-poster';
export const renderGraphSvg=(svg:string)=>renderPosterSvg(svg,[inter]);

import { emojis } from './game-common';
import { posterRemoteImage } from './legend-poster';
import type { CommandContext } from './types';
const badgeCache=new Map<string,{expires:number;image:Promise<string|undefined>}>();
export async function graphDecoration<T extends {tag:string;name:string}>(ctx:CommandContext,metric:string,rows:T[]){
 const emoji=await emojis(ctx),mark=emoji.component(graphMetricIcons[metric]??'');
 const icon=mark?await posterRemoteImage(`https://cdn.discordapp.com/emojis/${mark.id}.png`):undefined;
 const decorated=await Promise.all(rows.map(async row=>{
  const key=`${ctx.env.CLASHKING_API_BASE_URL}:${row.tag}`;let cache=badgeCache.get(key);
  if(!cache||cache.expires<Date.now()){
   const image=ctx.services.api.get<{badgeUrls?:{small?:string}}>(`/v2/bot/clash/clans/${encodeURIComponent(row.tag)}`).then(clan=>posterRemoteImage(clan.badgeUrls?.small)).catch(()=>undefined);
   cache={expires:Date.now()+300000,image};if(badgeCache.size>=200)badgeCache.delete(badgeCache.keys().next().value!);badgeCache.set(key,cache);
  }
  return {...row,icon:await cache.image};
 }));
 return {icon,rows:decorated};
}
