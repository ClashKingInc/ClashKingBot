import { CommandInputError, normalizeTag, requireGuildId } from "./command-utils";
import { legacyMessage } from "../discord/components";
import type { ApplicationCommandOption, CommandContext } from "./types";
interface Label { id: string; name: string; position: number }
const groupOption: ApplicationCommandOption = { name: "group", type: 3, description: "Roster player label", autocomplete: true };
export function rosterLabelOptions(roster: ApplicationCommandOption): ApplicationCommandOption[] {
 return [
  { name: "groups", type: 1, description: "Manage server labels for players inside rosters", options: [
   { name: "action", type: 3, description: "Action (default list)", choices: ["list", "add", "rename", "delete"].map(value => ({name:value,value})) },
   groupOption, { name: "name", type: 3, description: "New label name", max_length: 49 },
  ] },
  { name: "group-player", type: 1, description: "Assign roster players to a label, or Main", options: [roster,
   { name: "players", type: 3, description: "Player tags separated by spaces (up to 25)", required: true, max_length:400 },
   {...groupOption, description: "Label; omit to move players to Main"},
  ] },
 ];
}
const path = (ctx: CommandContext) => `/v2/server/${requireGuildId(ctx)}/roster-member-groups`;
export async function rosterLabelAutocomplete(ctx: CommandContext, value: string) {
 const {items} = await ctx.services.api.get<{items:Label[]}>(path(ctx), {}, AbortSignal.timeout(1500));
 return items.filter(item=>item.name.toLocaleLowerCase().includes(value.toLocaleLowerCase())).slice(0,25).map(item=>({name:item.name,value:item.id}));
}
export async function rosterLabels(ctx: CommandContext, action: string, options: Map<string, unknown>) {
 const api=ctx.services.api, base=path(ctx);
 const reply=(content:string)=>legacyMessage({content,allowed_mentions:{parse:[]}},{ephemeral:true});
 const id=String(options.get("group")??"");
 if(id&&!/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/iu.test(id))throw new CommandInputError("Choose a label from autocomplete.");
 if(action==="group-player") {
  const roster=String(options.get("roster")??"");
  if(!/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/iu.test(roster))throw new CommandInputError("Choose a roster.");
  const tags=[...new Set(String(options.get("players")??"").split(/[\s,]+/u).filter(Boolean).map(tag=>normalizeTag(tag,ctx.locale)))];
  if(!tags.length||tags.length>25)throw new CommandInputError("Provide 1–25 player tags.");
  await api.patch(`/v2/server/${requireGuildId(ctx)}/rosters/${roster}/member-label`,{playerTags:tags,memberGroupId:id||null});
  return reply(`Updated the label for ${tags.length} roster player(s)${id?"":" to Main"}.`);
 }
 const operation=String(options.get("action")??"list");
 if(operation==="list") {
  const {items}=await api.get<{items:Label[]}>(base);
  const clean=(name:string)=>name.replace(/[\\`*_~|<>\r\n]/gu," ");
  return reply(`**Roster player labels**\nMain (default)${items.map(item=>`\n• ${clean(item.name)}`).join("")}\n\nUse /roster group-player to assign members. These labels are separate from collections of whole rosters.`);
 }
 if(!["add","rename","delete"].includes(operation))throw new CommandInputError("Choose a valid action.");
 if(operation!=="add"&&!id)throw new CommandInputError("Choose the label to change.");
 const name=String(options.get("name")??"").trim();
 if(operation!=="delete"&&(!name||name.length>49))throw new CommandInputError("Enter a label name with 1–49 characters.");
 if(operation==="add")await api.post(base,{name});
 if(operation==="rename")await api.patch(`${base}/${id}`,{name});
 if(operation==="delete")await api.delete(`${base}/${id}`);
 return reply(operation==="delete"?"Deleted the unused roster label.":operation==="add"?"Created the roster label.":"Renamed the roster label.");
}
