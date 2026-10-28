import { boostsCommand } from "./boosts";
import { statsCommand } from "./stats";
import { helpCommand } from "./help";
import { InteractionResponseType, MessageFlags, type InteractionOption } from "../discord/types";
import { CommandInputError, OptionType } from "./command-utils";
import { playerCommand } from "./player";
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
  let command:Command,action:string,options:InteractionOption[];
  const string=(name:string,value:string):InteractionOption=>({name,type:OptionType.String,value});
  const tag=(value:string|undefined)=>{if(!value||!/^#[0289PYLQGRJCUV]+$/u.test(value))throw new CommandInputError("Invalid player tag.");return value;};
  if(kind==="bs"&&parts.length===4){
    command=boostsCommand;action="";
    options=[{name:"limit",type:OptionType.Integer,value:Number(parts[2])},string("sort_order",parts[3]!)];
    if(parts[0]!=="-")options.push(string("clan",tag(parts[0])));
    if(parts[1]!=="-")options.push(string("super_troop",parts[1]!.replaceAll("~"," ")));
  }else if(kind==="ws"&&parts.length===10){
    command=statsCommand;action="war";
    const [target,view,war,th,stars,period,min,limit,sort,order]=parts;
    if(!/^[0-3]+$/u.test(stars!)||! /^(?:s-current|s\d{4}-\d{2}|[dw]\d+)$/u.test(period!))throw new CommandInputError("Invalid war statistics control.");
    options=[string("type",view!),string("war_types",war!),string("th_filter",th!),string("star_filter",stars!.split("").join(",")),{name:"min_attacks",type:OptionType.Integer,value:Number(min)},{name:"limit",type:OptionType.Integer,value:Number(limit)},string("sort_by",sort!),string("sort_order",order!)];
    if(target!=="-")options.push(string("clan",tag(target)));
    if(period!=="s-current")options.push(period!.startsWith("s")?string("season",period!.slice(1)):{name:period!.startsWith("d")?"num_days":"num_wars",type:OptionType.Integer,value:Number(period!.slice(1))});
  }else if(kind==="hp"&&parts.length===1){
    command=helpCommand;action="";options=parts[0]==="-"?[]:[string("command",parts[0]!.replaceAll("~"," "))];
  }else if(kind==="wp"&&parts.length===4){
    command=clanCommand;action="war-preference";
    options=[string("clan",tag(parts[0])),string("view",parts[1]!),string("status",parts[2]!),{name:"townhall",type:OptionType.Integer,value:Number(parts[3])}];
  }else if((kind==="sc"&&parts.length===5)||(kind==="sf"&&parts.length===4)){
    command=kind==="sc"?clanCommand:familyCommand;action="summary";
    const values=kind==="sc"?parts.slice(1):parts;
    options=[string("view",values[0]!),{name:"limit",type:OptionType.Integer,value:Number(values[2])},{name:"townhall",type:OptionType.Integer,value:Number(values[3])}];
    if(kind==="sc")options.push(string("clan",tag(parts[0])));
    if(values[1]!=="current")options.push(string("season",values[1]!));
  }else if((kind==="uc"&&parts.length===7)||(kind==="up"&&parts.length===6)){
    command=kind==="uc"?clanCommand:familyCommand;action="progress";
    const values=kind==="uc"?parts.slice(1):parts;
    options=[string("type",values[0]!),{name:"limit",type:OptionType.Integer,value:Number(values[2])},string("sort_order",values[3]!),string("sort_by",values[4]!),{name:"townhall",type:OptionType.Integer,value:Number(values[5])}];
    if(kind==="uc")options.push(string("clan",tag(parts[0])));
    if(values[1]!=="current")options.push(string("season",values[1]!));
  }else if(kind==="cr"&&parts.length===7&&["capital","war-log"].includes(parts[1]!)&&["members","all"].includes(parts[6]!)){
    command=clanCommand;action=parts[1]!;
    options=[string("clan",tag(parts[0])),string("view",parts[2]!),{name:"limit",type:OptionType.Integer,value:Number(parts[4])},string("sort_order",parts[5]!),{name:"current_members",type:OptionType.Boolean,value:parts[6]==="members"}];
    if(parts[3]!=="current")options.push(string("weekend",parts[3]!));
  }else if(kind==="fd"&&parts.length===5&&["clans","stats"].includes(parts[0]!)){
    command=familyCommand;action=parts[0]!;
    options=[string("type",parts[1]!),{name:"limit",type:OptionType.Integer,value:Number(parts[2])},string("sort_order",parts[3]!)];
    if(parts[4]!=="current")options.push(string("season",parts[4]!));
  }else if(kind==="fo"&&parts.length===4&&["wars","raids"].includes(parts[0]!)){
    command=familyCommand;action=parts[0]!;
    options=[{name:"limit",type:OptionType.Integer,value:Number(parts[1])},string("sort_order",parts[2]!)];
    if(action==="wars"){
      if(!["yes","no"].includes(parts[3]!))throw new CommandInputError("Invalid war report.");
      options.push({name:"include_ended",type:OptionType.Boolean,value:parts[3]==="yes"});
    }else if(parts[3]!=="current")options.push(string("weekend",parts[3]!));
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
  }else if((kind==="ac"&&parts.length===1||kind==="pt"&&[1,4].includes(parts.length))&&/^\d{15,22}$/u.test(parts[0]!)){
    command=playerCommand;action=kind==="ac"?"accounts":"to-do";options=[string("discord_user",parts[0]!)];
    if(kind==="pt"&&parts.length===4){
      if(!["0","1"].includes(parts[3]!))throw new CommandInputError("Invalid to-do options.");
      options.push({name:"clan_games_goal",type:OptionType.Integer,value:Number(parts[1])},{name:"show_completed",type:OptionType.Boolean,value:parts[3]==="1"});
      if(parts[2]!=="none")options.push({name:"season_goal",type:OptionType.Integer,value:Number(parts[2])});
    }
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
  }else if(kind==="lp"&&parts.length===2&&(parts[1]==="today"||/^\d{4}-\d{2}-\d{2}$/u.test(parts[1]!))){
    command=legendsCommand;action="poster";options=[string("player",tag(parts[0]))];
    if(parts[1]!=="today")options.push(string("day",parts[1]!));
  }else if(kind==="lg"&&parts.length===2&&["cutoffs","buckets","winners","daily","streaks"].includes(parts[0]!)&&/^[1-9][0-9]?$/u.test(parts[1]!)&&Number(parts[1])<=50){
    command=legendsCommand;action="stats";options=[string("type",parts[0]!),{name:"limit",type:OptionType.Integer,value:Number(parts[1])}];
  }else if((kind==="lh"&&(parts.length===1||parts.length===2))||(kind==="lc"&&parts.length===1)){
    command=legendsCommand;action=kind==="lh"?"history":"clan";options=[string(kind==="lh"?"player":"clan",tag(parts[0]))];
    // Keep the requested history window when navigating a long result.
    if(parts.length===2){
      if(!/^[1-9][0-9]{0,2}$/u.test(parts[1]!)||Number(parts[1])>240)throw new CommandInputError("Invalid history limit.");
      options.push({name:"limit",type:OptionType.Integer,value:Number(parts[1])});
    }
  }else if(kind==="bl"&&parts.length===3&&/^(global|\d{1,12})$/u.test(parts[0]!)&&["home","builder"].includes(parts[1]!)){
    command=leaderboardCommand;action="location";options=[string("location",parts[0]!),string("village",parts[1]!),{name:"limit",type:OptionType.Integer,value:Number(parts[2])}];
  }else if(kind==="bf"&&parts.length===2&&["donations","legends","clan-games"].includes(parts[0]!)){
    command=leaderboardCommand;action="family";options=[string("type",parts[0]!),{name:"limit",type:OptionType.Integer,value:Number(parts[1])}];
  }else throw new CommandInputError("Invalid page control.");
  options.push({name:"__page",type:OptionType.Integer,value:Number(rawPage)});
  const context:CommandContext={...ctx,options:["hp","bs"].includes(kind??"")?new Map(options.map(option=>[option.name,option])):new Map([[action,{name:action,type:OptionType.Subcommand,options}]])};
  const run=async()=>command.execute(context);
  if(!waitUntil){const result=await run();return typeof result.data?.flags==="number"&&(result.data.flags&MessageFlags.Ephemeral)?result:{...result,type:InteractionResponseType.UpdateMessage};}
  waitUntil(run().then(result=>typeof result.data?.flags==="number"&&(result.data.flags&MessageFlags.Ephemeral)
    ?ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token,result.data)
    :ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token,result.data??{}))
    .catch(error=>{
      // Keep interaction tokens and full payloads out of logs, but preserve the
      // failure stage/status so a failed Discord edit is not mistaken for bad data.
      let code: unknown;
      let validation: unknown;
      if(typeof error?.body==="string")try{const body=JSON.parse(error.body);code=body?.code;validation=body?.errors;}catch{}
      console.warn("game_page_failed",{kind,error:error?.name,status:error?.status,code,validation,message:error instanceof Error?error.message:"Unknown error"});
      return ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token,{content:error instanceof CommandInputError?error.message:"Couldn't load this page. Try again.",flags:MessageFlags.Ephemeral});
    }));
  return {type:InteractionResponseType.DeferredUpdateMessage};
}
