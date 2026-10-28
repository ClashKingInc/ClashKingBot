import { invokingUserId } from "./command-utils";
import { actionRow, legacyMessage } from "../discord/components";
import type { Command } from "./types";
interface Status{configuredServers:number;familyClans:number;cachedGuilds:number;readyGuilds:number;expectedShards:number;healthyShards:number;players:number;clans:number;wars:number;countsRefreshedAt:string;observedAt:string}
export const botInfoCommand:Command={
 deferred:true,definition:{name:"bot",description:"ClashKing service statistics and gateway status",type:1,contexts:[0,1,2],integration_types:[0,1]},
 async execute(ctx){
  let data:Status;try{data=await ctx.services.api.get<Status>("/v2/bot/status",{},AbortSignal.timeout(8000));}
  catch{return legacyMessage({content:"Bot statistics are temporarily unavailable. Try again later."});}
  const number=(value:number)=>value.toLocaleString("en");
  const refreshed=Math.floor(Date.parse(data.countsRefreshedAt)/1000);
  return legacyMessage({allowed_mentions:{parse:[]},embeds:[{title:"ClashKing statistics",color:0xe5ad47,fields:[
   {name:"Configured servers",value:number(data.configuredServers),inline:true},
   {name:"Family clans",value:number(data.familyClans),inline:true},
   {name:"Gateway shards",value:data.expectedShards?`${number(data.healthyShards)}/${number(data.expectedShards)} healthy`:"No gateway snapshot",inline:true},
   {name:"Ready / cached servers",value:`${number(data.readyGuilds)}/${number(data.cachedGuilds)}`,inline:true},
   {name:"Stored players",value:number(data.players),inline:true},
   {name:"Stored clans",value:number(data.clans),inline:true},
   {name:"Recorded wars",value:number(data.wars),inline:true},
   {name:"Data snapshot",value:Number.isFinite(refreshed)?`<t:${refreshed}:R>`:"Unavailable",inline:true},
  ],footer:{text:"Readiness requires fresh matching gateway state. Stored counts are a snapshot."}}],components:[actionRow({type:2,style:2,label:"Refresh",custom_id:`ck:page:bi:${invokingUserId(ctx)}:0`})]});
 }
};
