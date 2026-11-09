import type { CommandContext } from './types';
import { normalizeTag } from './command-utils';

export interface PlayerSuggestion {name:string;tag:string;townHallLevel?:number}
const superscript='⁰¹²³⁴⁵⁶⁷⁸⁹';
export function playerSuggestion(item:PlayerSuggestion){
 const hall=String(item.townHallLevel??0).split('').map(digit=>superscript[Number(digit)]??digit).join('');
 const prefix=item.townHallLevel?`${hall} `:"",suffix=` | ${item.tag}`;
 return {name:prefix+item.name.slice(0,100-prefix.length-suffix.length)+suffix,value:item.tag};
}
export function uniqueSuggestions<T extends {value:string}>(items:T[]):T[]{
 return [...new Map(items.map(item=>[item.value,item])).values()].slice(0,25);
}
export async function personalSuggestions(ctx:CommandContext,type:'player'|'clan',query:string,legendsOnly=false,signal=AbortSignal.timeout(1800)){
 const user=ctx.interaction.member?.user?.id??ctx.interaction.user?.id;
 if(!user)return [];
 const result=await ctx.services.api.get<{items:PlayerSuggestion[]}>(`/v2/bot/users/${user}/search-suggestions`,{type,query,legendsOnly},signal).catch(()=>({items:[]}));
 return result.items;
}
export async function clanAutocomplete(ctx:CommandContext){
 const query=String(ctx.options.get('clan')?.value??'').trim(),deadline=AbortSignal.timeout(1800);
 const label=(item:PlayerSuggestion)=>({name:`${item.name} | ${item.tag}`.slice(0,100),value:item.tag});
 let preferred:PlayerSuggestion[]=[];
 if(ctx.interaction.guild_id){
  const clans=await ctx.services.api.get<PlayerSuggestion[]>(`/v2/server/${ctx.interaction.guild_id}/clans-basic`,{},deadline).catch(()=>[]);
  preferred=clans.filter(item=>`${item.name} ${item.tag}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
 }else preferred=await personalSuggestions(ctx,'clan',query,false,deadline);
 if(query.length<3||preferred.length>=25)return preferred.slice(0,25).map(label);
 if(/^#?[0289PYLQGRJCUV]{3,15}$/iu.test(query)){
  const clan=await ctx.services.api.get<PlayerSuggestion>(`/v2/bot/clash/clans/${encodeURIComponent(normalizeTag(query,ctx.locale))}`,{},deadline).catch(()=>undefined);
  if(clan)return uniqueSuggestions([...preferred.map(label),label(clan)]);
 }
 const result=await ctx.services.api.get<{items:PlayerSuggestion[]}>('/v2/bot/clash/clans',{name:query,limit:25,memberList:false},deadline).catch(()=>({items:[]}));
 return uniqueSuggestions([...preferred.map(label),...result.items.map(label)]);
}
