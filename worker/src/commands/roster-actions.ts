import { ClashKingApiError } from "../api/client";
import { legacyMessage } from "../discord/components";
import { CommandInputError, normalizeTag, requireGuildId } from "./command-utils";
import { fetchPlayer } from "./game-common";
import { loadRoster } from "./roster";
import type { ApplicationCommandOption, CommandContext } from "./types";
const players:ApplicationCommandOption={name:"players",type:3,description:"Player tags separated by spaces (up to 25)",required:true,max_length:400};
export const rosterActionNames=["add-player","remove-player","move-player","copy","delete"];
export function rosterActionOptions(roster:ApplicationCommandOption):ApplicationCommandOption[]{return [
 {name:"add-player",type:1,description:"Add players using current profiles",options:[roster,players]},
 {name:"remove-player",type:1,description:"Remove players from a roster",options:[roster,players]},
 {name:"move-player",type:1,description:"Move players atomically to another roster",options:[roster,{...roster,name:"destination",description:"Destination roster"},players]},
 {name:"copy",type:1,description:"Copy this roster's settings and optionally its members",options:[roster,{name:"name",type:3,description:"Name for the copy",required:true,max_length:100},{name:"members",type:5,description:"Also copy members (default false)"}]},
 {name:"delete",type:1,description:"Clear members or delete a roster",options:[roster,{name:"type",type:3,description:"What to delete",required:true,choices:[{name:"Clear members",value:"members"},{name:"Delete roster",value:"roster"}]},{name:"confirm",type:5,description:"Confirm this cannot be undone",required:true}]},
];}
export async function rosterAction(ctx:CommandContext,id:string,action:string,options:Map<string,unknown>){
 const server=requireGuildId(ctx),source=await loadRoster(ctx,id),api=ctx.services.api;
 const reply=(content:string)=>legacyMessage({content,allowed_mentions:{parse:[]}},{ephemeral:true});
 try{
  if(action==="copy"){
   const name=String(options.get("name")??"").trim();if(!name||name.length>100)throw new CommandInputError("Choose a name for the copy.");
   const result=await api.post<{new_alias:string;members_copied:number}>(`/v2/roster/${id}/clone?server_id=${server}`,{new_alias:name,copy_members:options.get("members")===true});
   return reply(`Copied roster as ${result.new_alias}: ${result.members_copied} members copied.`);
  }
  if(action==="delete"){
   const kind=String(options.get("type")??"");if(options.get("confirm")!==true||!["members","roster"].includes(kind))throw new CommandInputError("Choose what to delete and set confirm to True.");
   await api.delete(`/v2/roster/${id}?server_id=${server}${kind==="members"?"&members_only=true":""}`);
   return reply(kind==="members"?`Cleared members from ${source.alias}.`:`Deleted roster ${source.alias}.`);
  }
  const tags=[...new Set(String(options.get("players")??"").split(/[\s,]+/u).filter(Boolean).map(value=>normalizeTag(value,ctx.locale)))];
  if(!tags.length||tags.length>25)throw new CommandInputError("Provide 1–25 player tags.");
  const present=new Set(source.members.map(member=>member.playerTag));
  if(action==="add-player"&&tags.some(tag=>present.has(tag)))throw new CommandInputError("One or more players are already in this roster.");
  if(action!=="add-player"&&tags.some(tag=>!present.has(tag)))throw new CommandInputError("One or more players are not in the source roster.");
  if(action==="move-player"){
   const destination=String(options.get("destination")??"");
   if(destination===id)throw new CommandInputError("Choose a different destination roster.");
   if(!/^[0-9a-f-]{36}$/iu.test(destination))throw new CommandInputError("Choose a valid destination roster.");
   const target=await loadRoster(ctx,destination);
   // The API validates and applies the same proposal with expected revisions.
   // Do not retry a conflict automatically: that could move a newer roster state.
   const changes=tags.map(playerTag=>({action:"move",playerTag,fromRosterId:id,toRosterId:destination}));
   const proposal=await api.post<{expectedRevisions:Record<string,number>}>("/v2/roster/membership-changes/validate",{serverId:server,rosterIds:[id,destination],changes});
   await api.post("/v2/roster/membership-changes",{serverId:server,changes,expectedRevisions:proposal.expectedRevisions});
   return reply(`Moved ${tags.length} player(s) from ${source.alias} to ${target.alias}.`);
  }
  // Resolve every requested profile before mutating. The generic API preserves
  // supplied snapshots on lookup failures; a new slash-command add has no old
  // snapshot to preserve and must never silently insert an empty placeholder.
  const members=[];
  if(action==="add-player")for(let i=0;i<tags.length;i+=5){
   const loaded=await Promise.all(tags.slice(i,i+5).map(async tag=>{
    const player=await fetchPlayer(ctx,tag).catch(()=>{throw new CommandInputError(`Could not load ${tag}; no players were added.`);});
    if(player.tag!==tag||!player.name||!Number.isInteger(player.townHallLevel))throw new CommandInputError(`Invalid profile for ${tag}; no players were added.`);
    return {tag,name:player.name,townhall:player.townHallLevel,trophies:player.trophies,current_clan:player.clan?.name??"",current_clan_tag:player.clan?.tag??""};
   }));members.push(...loaded);
  }
  await api.post(`/v2/roster/${id}/members?server_id=${server}`,action==="remove-player"?{operation:"remove",player_tags:tags}:{members});
  return reply(`${action==="remove-player"?"Removed":"Added"} ${tags.length} player(s) ${action==="remove-player"?"from":"to"} ${source.alias}.`);
 }catch(error){
  if(error instanceof ClashKingApiError&&[400,409,422].includes(error.status)){
   let message="Roster changed or the requested players do not meet its rules. Refresh and try again.";
   try{const body=JSON.parse(error.body) as {message?:unknown};if(typeof body.message==="string")message=body.message.slice(0,500);}catch{/* Use the bounded fallback. */}
   throw new CommandInputError(message);
  }
  throw error;
 }
}
