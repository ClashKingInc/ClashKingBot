import { actionRow, legacyMessage } from "../discord/components";
import { escapeMarkdown, playerAppUrl, playerUrl } from "./game-common";
import { invokingUserId } from "./command-utils";
import type { CommandContext } from "./types";
import { serverEmbedColor } from "./embed-color";

export interface LegendFinish { season:string; name?:string; trophies:number; rank:number }
const months=["January","February","March","April","May","June","July","August","September","October","November","December"];

/** Keep the legacy history presentation shared by slash commands and buttons. */
export async function legendHistoryReply(ctx:CommandContext, player:{name:string;tag:string}, finishes:LegendFinish[], iconUrl?:string) {
  const color=await serverEmbedColor(ctx);
  if(!finishes.length)return legacyMessage({allowed_mentions:{parse:[]},embeds:[{
    color,description:`${escapeMarkdown(player.name)} has no recorded Legend season finishes.`,
  }],components:[]});
  const fields:Array<{name:string;value:string;inline:false}>=[];
  // History contains snapshots of the current name too; only past names belong here.
  const currentName=player.name.trim();
  const names=[...new Set(finishes.map(item=>item.name?.trim()).filter((name):name is string=>Boolean(name)&&name!==currentName))];
  let nameChunk="";
  for(const name of names){
    const escaped=escapeMarkdown(name);
    if(nameChunk.length+escaped.length+2>1024){fields.push({name:"Previous Names",value:nameChunk,inline:false});nameChunk="";}
    nameChunk+=(nameChunk?", ":"")+escaped;
  }
  if(nameChunk)fields.push({name:"Previous Names",value:nameChunk,inline:false});
  for(const item of [...finishes].sort((a,b)=>b.season.localeCompare(a.season))){
    // Both YYYY-MM and YYYY-MM-DD occur in retained history. Use the month
    // component, not the last component (which would turn December 1 into January).
    const date=/^(?:v2-)?(\d{4})-(\d{2})(?:-|$)/u.exec(item.season);
    const month=date?months[Number(date[2])-1]:undefined;
    const year=date?.[1]??"Other seasons";
    const label=month??item.season.replace(/`/gu,"");
    const line=`\`${label.padEnd(9)}\` | 🏆${item.trophies} | 🌎${item.rank}\n`;
    let field=fields.at(-1);
    if(!field||field.name!==year||field.value.length+line.length>1024){field={name:year,value:"",inline:false};fields.push(field);}
    field.value+=line;
  }
  const pages:Array<typeof fields>=[[]];
  for(const field of fields){
    const current=pages.at(-1)!;
    if(current.length>=25||current.reduce((sum,value)=>sum+value.name.length+value.value.length,0)+field.name.length+field.value.length>5500)pages.push([]);
    pages.at(-1)!.push(field);
  }
  const requested=Number(ctx.options.get("__page")?.value??0);
  const page=Number.isSafeInteger(requested)?Math.max(0,Math.min(requested,pages.length-1)):0;
  const limit=ctx.options.get("limit")?.value;
  const pageArgs=limit===undefined?player.tag:`${player.tag}:${limit}`;
  return legacyMessage({allowed_mentions:{parse:[]},embeds:[{
    color,author:{name:`${player.name} Legend History`.slice(0,256),url:playerUrl(player.tag),...(iconUrl?{icon_url:iconUrl}:{})},
    description:`[Open in ClashKing](${playerAppUrl(player.tag,ctx.env.APP_ENV)})`,fields:pages[page],
    ...(pages.length>1?{footer:{text:`Page ${page+1}/${pages.length}`}}:{}),
  }],components:pages.length>1?[actionRow(
    {type:2,style:2,label:"Previous",custom_id:`ck:page:lh:${invokingUserId(ctx)}:${pageArgs}:${page-1}`,disabled:page===0},
    {type:2,style:2,label:"Next",custom_id:`ck:page:lh:${invokingUserId(ctx)}:${pageArgs}:${page+1}`,disabled:page===pages.length-1},
  )]:[]});
}
