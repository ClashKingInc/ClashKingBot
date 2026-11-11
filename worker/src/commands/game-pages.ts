import { createInteractionFollowup, editOriginalInteractionResponse } from "../discord/message-actions";
import { sendInteractionError } from "./errors";
import { warCommand } from "./war";
import { botInfoCommand } from "./bot-info";
import { roleUsersCommand } from "./role-users";
import { helpCommand } from "./help";
import { InteractionResponseType, MessageFlags, type InteractionOption } from "../discord/types";
import { CommandInputError, OptionType } from "./command-utils";
import { playerCommand } from "./player";
import { linkCommand } from "./link";
import { rankedCommand } from "./ranked";
import { legendsCommand } from "./legends";
import { leaderboardCommand } from "./leaderboard";
import { familyCommand } from "./family";
import { clanCommand } from "./clan";
import type { Command, CommandContext } from "./types";

export async function dispatchGamePage(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>)=>void) {
  const [prefix,domain,kind,owner,...parts]=(ctx.interaction.data?.custom_id??"").split(":");
  // These controls only navigate public game data. The embedded actor remains
  // in existing message IDs for compatibility, not as an ownership lock. Keep
  // using the actual clicker's context so visibility checks are never borrowed
  // from the original command author. Private/mutating controls use other handlers.
  if(prefix!=="ck"||domain!=="page"||!owner||!/^\d{15,22}$/u.test(owner))throw new CommandInputError("Invalid page control.");
  const rawPage=parts.pop();
  if(!rawPage||!/^\d{1,6}$/u.test(rawPage))throw new CommandInputError("Invalid page.");
  if(parts.at(-1)==="preference-view"){
    parts.pop();const selected=ctx.interaction.data?.values;
    if(kind!=="wp"||selected?.length!==1||!["last_change","last_war","timer"].includes(selected[0]!))throw new CommandInputError("Choose a war preference view.");
    parts[1]=selected[0]!;
  }
  if(parts.at(-1)==="directory-type"){
    parts.pop();const value=ctx.interaction.data?.values;
    if(kind!=="fd"||value?.length!==1||!["categories","overview","cwl","capital","location"].includes(value[0]!))throw new CommandInputError("Choose a directory type.");
    parts[1]=value[0]!;
  }
  if(parts.at(-1)==="progress-type"){
    parts.pop();
    const selected=ctx.interaction.data?.values;
    if(!["uc","up"].includes(kind??"")||selected?.length!==1||!["heroes","troops","equipment","all"].includes(selected[0]!))throw new CommandInputError("Choose an upgrade type.");
    parts[kind==="uc"?1:0]=selected[0]!;
  }
  if(parts.at(-1)==="donation-sort"){
    parts.pop();
    const selected=ctx.interaction.data?.values;
    const choice=selected?.[0]?.split(":");
    const indexes:Record<string,[number,number]>={cl:[5,6],cg:[6,4],fm:[5,3]};
    const index=indexes[kind??""];
    if(!index||selected?.length!==1||choice?.length!==2||!["donated","received","ratio"].includes(choice[0]!)||!["asc","desc"].includes(choice[1]!))throw new CommandInputError("Choose a donation sort.");
    parts[index[0]]=choice[0]!;parts[index[1]]=choice[1]!;
  }
  if(parts.at(-1)==="sort"){
    parts.pop();
    const selected=ctx.interaction.data?.values;
    const orderIndex:Record<string,number>={cl:6,cg:4,fm:3,uc:4,up:3};
    const index=orderIndex[kind??""];
    if(index===undefined||selected?.length!==1||!["asc","desc"].includes(selected[0]!))throw new CommandInputError("Choose a valid sort order.");
    parts[index]=selected[0]!;
  }
  let command:Command,action:string,options:InteractionOption[];
  const string=(name:string,value:string):InteractionOption=>({name,type:OptionType.String,value});
  const tag=(value:string|undefined)=>{if(!value||!/^#[0289PYLQGRJCUV]+$/u.test(value))throw new CommandInputError("Invalid player tag.");return value;};
  if(kind==="bi"&&parts.length===0){
    command=botInfoCommand;action="";options=[];
  }else if(kind==="ru"&&parts.length===1&&/^\d{15,20}$/u.test(parts[0]!)){
    command=roleUsersCommand;action="";options=[string("role",parts[0]!)];
  }else if(kind==="hp"&&parts.length===1){
    command=helpCommand;action="";options=parts[0]==="-"?[]:[string("command",parts[0]!.replaceAll("~"," "))];
  }else if(kind==="wp"&&parts.length===4){
    command=warCommand;action="preference";
    options=[string("clan",tag(parts[0])),string("view",parts[1]!),string("status",parts[2]!),{name:"townhall",type:OptionType.Integer,value:Number(parts[3])}];
  }else if((kind==="ca"&&parts.length===5)||(kind==="fa"&&parts.length===5)){
    command=kind==="ca"?clanCommand:familyCommand;action="activity";
    const values=kind==="ca"?parts.slice(1):parts;
    options=kind==="ca"?[string("season",values[0]!),{name:"limit",type:OptionType.Integer,value:Number(values[1])},string("sort_by",values[2]!),string("sort_order",values[3]!)]:[string("season",values[0]!),{name:"townhall",type:OptionType.Integer,value:Number(values[1])},{name:"limit",type:OptionType.Integer,value:Number(values[2])},string("sort_by",values[3]!),string("sort_order",values[4]!)];
    if(kind==="ca")options.push(string("clan",tag(parts[0])));
  }else if((kind==="sc"&&parts.length===3)||(["sf","fs"].includes(kind??"")&&parts.length===2)){
    command=kind==="sc"?clanCommand:familyCommand;action="summary";
    const values=kind==="sc"?parts.slice(1):parts;
    options=[{name:"limit",type:OptionType.Integer,value:Number(values[1])}];
    if(kind==="sc")options.push(string("clan",tag(parts[0])));
    if(kind==="fs"||kind==="sf")options.push(string("type",kind==="fs"?"clan":"player"));
    if(values[0]!=="current")options.push(string("season",values[0]!));
  }else if((kind==="uc"&&parts.length===7)||(kind==="up"&&parts.length===6)){
    command=kind==="uc"?clanCommand:familyCommand;action="progress";
    const values=kind==="uc"?parts.slice(1):parts;
    options=[string("type",values[0]!),{name:"limit",type:OptionType.Integer,value:Number(values[2])},string("sort_order",values[3]!),string("sort_by",values[4]!),{name:"townhall",type:OptionType.Integer,value:Number(values[5])}];
    if(kind==="uc")options.push(string("clan",tag(parts[0])));
    if(values[1]!=="current")options.push(string("season",values[1]!));
  }else if(kind==="cc"&&parts.length===3){
    command=clanCommand;action="capital";
    options=[string("clan",tag(parts[0])),string("view",parts[1]!)];
    if(parts[2]!=="current")options.push(string("weekend",parts[2]!));
  }else if(kind==="cr"&&parts.length===7&&["capital","war-log"].includes(parts[1]!)&&["members","all"].includes(parts[6]!)){
    command=clanCommand;action=parts[1]!;
    options=[string("clan",tag(parts[0])),string("view",parts[2]!),{name:"limit",type:OptionType.Integer,value:Number(parts[4])},string("sort_order",parts[5]!),{name:"current_members",type:OptionType.Boolean,value:parts[6]==="members"}];
    if(parts[3]!=="current")options.push(string("weekend",parts[3]!));
  }else if(kind==="fd"&&parts.length===5&&parts[0]==="clans"){
    command=familyCommand;action=parts[0]!;
    options=[string("type",parts[1]!),{name:"limit",type:OptionType.Integer,value:Number(parts[2])},string("sort_order",parts[3]!)];
    if(parts[4]!=="current")options.push(string("season",parts[4]!));
  }else if(kind==="fo"&&parts.length===2&&["wars","raids"].includes(parts[0]!)){
    command=familyCommand;action="ongoing";
    options=[string("type",parts[0]!),{name:"__page",type:OptionType.Integer,value:Number(parts[1])}];
  }else if((kind==="fm"&&parts.length===7)||(kind==="cg"&&parts.length===8)){
    const values=kind==="cg"?parts.slice(1):parts;
    if(!["donations","games"].includes(values[0]!)||!["asc","desc"].includes(values[3]!)||!["m","a"].includes(values[6]!))throw new CommandInputError("Invalid contribution report.");
    command=kind==="fm"?familyCommand:clanCommand;action=values[0]==="games"?"games":"donations";
    options=[{name:"limit",type:OptionType.Integer,value:Number(values[2])},string("sort_order",values[3]!),{name:"townhall",type:OptionType.Integer,value:Number(values[4])},string("sort_by",values[5]!),{name:"current_members",type:OptionType.Boolean,value:values[6]==="m"}];
    if(kind==="cg")options.push(string("clan",tag(parts[0])));
    if(values[1]!=="current")options.push(string("season",values[1]!));
  }else if(kind==="cl"&&parts.length===9&&["o","d","O","D","vo","vd"].includes(parts[1]!)&&["m","a"].includes(parts[7]!)&&["d","b","m"].includes(parts[8]!)){
    command=clanCommand;action=parts[1]!.toLowerCase().endsWith("d")?"donations":"search";
    options=[string("clan",tag(parts[0])),string("sort_by",parts[5]!),string("sort_order",parts[6]!),{name:"townhall",type:OptionType.Integer,value:Number(parts[3])},{name:"limit",type:OptionType.Integer,value:Number(parts[4])}];
    options.push(string("__members_only",String(parts[7]==="m")));
    options.push(string("type",parts[8]!));
    if(parts[2]!=="current")options.push(string("season",parts[2]!));
  }else if((kind==="ac"&&parts.length===1||kind==="pt"&&parts.length===1)&&/^\d{15,22}$/u.test(parts[0]!)){
    // Account-list buttons belong to /link list, including their selected
    // user and page. Never dispatch them to the removed /player accounts path.
    command=kind==="ac"?linkCommand:playerCommand;action=kind==="ac"?"list":"to-do";options=[string("discord_user",parts[0]!)];

  }else if((kind==="rh"||kind==="rg")&&parts.length===(kind==="rh"?1:2)){
    command=rankedCommand;action=kind==="rh"?"history":"group";options=[string("player",tag(parts[0]))];
    if(kind==="rg"&&parts[1]!=="current"){
      if(!/^[1-9][0-9]{0,15}$/u.test(parts[1]!))throw new CommandInputError("Invalid season.");
      options.push(string("season",parts[1]!));
    }
  }else if(kind==="pp"&&(parts.length===2||parts.length===3)){
    const accountSelect=parts[1]==="account";
    const selected=accountSelect?"overview":parts[1]==="select"?ctx.interaction.data?.values?.[0]:parts[1];
    if(!selected||!["overview","troops","upgrades","history","history-cos"].includes(selected))throw new CommandInputError("Invalid player page.");
    command=playerCommand;action="lookup";options=[string("player",tag(accountSelect?ctx.interaction.data?.values?.[0]:parts[0])),string("__view",selected)];
    if(parts[2]&&parts[2]!=="none"){
      if(!/^\d{15,22}$/u.test(parts[2]))throw new CommandInputError("Invalid account picker.");
      options.push(string("__accounts_user",parts[2]));
    }
  }else if(kind==="rp"&&parts.length===3&&["overview","group"].includes(parts[2]!)){
    command=rankedCommand;action="player";options=[string("player",tag(parts[0])),string("__view",parts[2]!)];
    if(parts[1]!=="current"){
      if(!/^[1-9][0-9]{0,15}$/u.test(parts[1]!))throw new CommandInputError("Invalid season.");
      options.push(string("season",parts[1]!));
    }
  }else if(kind==="ls"&&parts.length===3&&["day","season"].includes(parts[1]!)&&/^\d{4}-\d{2}-\d{2}$/u.test(parts[2]!)){
    command=legendsCommand;action="player";options=[string("player",tag(parts[0])),string("__view",parts[1]!),string("__day",parts[2]!)];
  }else if(kind==="lg"&&parts.length===2&&["cutoffs","buckets","winners","daily","streaks"].includes(parts[0]!)&&/^[1-9][0-9]?$/u.test(parts[1]!)&&Number(parts[1])<=50){
    command=legendsCommand;action="stats";options=[string("type",parts[0]!),{name:"limit",type:OptionType.Integer,value:Number(parts[1])}];
  }else if((kind==="lh"&&(parts.length===1||parts.length===2))||(kind==="lc"&&parts.length===1)){
    command=legendsCommand;action=kind==="lh"?"history":"clan";options=[string(kind==="lh"?"player":"clan",tag(parts[0]))];
    // Keep the requested history window when navigating a long result.
    if(parts.length===2){
      if(!/^[1-9][0-9]{0,2}$/u.test(parts[1]!)||Number(parts[1])>240)throw new CommandInputError("Invalid history limit.");
      options.push({name:"limit",type:OptionType.Integer,value:Number(parts[1])});
    }
  }else if(kind==="bl"&&parts.length===3&&/^(global|\d{1,12})$/u.test(parts[0]!)&&["player","clan","bb_player","bb_clan","capital"].includes(parts[1]!)){
    command=leaderboardCommand;action="location";options=[string("location",parts[0]!),string("type",parts[1]!),{name:"limit",type:OptionType.Integer,value:Number(parts[2])}];
  }else throw new CommandInputError("Invalid page control.");
  options.push({name:"__page",type:OptionType.Integer,value:Number(rawPage)});
  const context:CommandContext={...ctx,options:["hp","ru"].includes(kind??"")?new Map(options.map(option=>[option.name,option])):new Map([[action,{name:action,type:OptionType.Subcommand,options}]])};
  const run=async()=>command.execute(context);
  if(!waitUntil){const result=await run();return typeof result.data?.flags==="number"&&(result.data.flags&MessageFlags.Ephemeral)?result:{...result,type:InteractionResponseType.UpdateMessage};}
  waitUntil(run().then(result=>typeof result.data?.flags==="number"&&(result.data.flags&MessageFlags.Ephemeral)
    ?createInteractionFollowup(ctx.services.discordRest,ctx.interaction.token,result.data)
    :editOriginalInteractionResponse(ctx.services.discordRest,ctx.interaction.token,result.data??{}))
    .catch(error=>{
      return sendInteractionError(ctx,error);
    }));
  return {type:InteractionResponseType.DeferredUpdateMessage};
}
