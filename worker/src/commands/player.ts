import { ClashKingApiError } from "../api/client";
import { invokingUserId, OptionType, stringOption } from "./command-utils";
import { emojis, isDailyLegend, fetchPlayer, gameReply, pagedGameReply, legendDay, linkedAccounts, playerAutocomplete, playerLabel, playerOption, resolvePlayerTag, subcommand, userOption } from "./game-common";
import { rankedBattleLimit } from "./ranked";
import type { Command, CommandContext } from "./types";
import { playerAccountsReply } from "./player-profile";
import { playerProfileReply } from "./player-profile-pages";

interface War { state: string; attacksPerMember?: number; clan: WarSide; opponent: WarSide }
interface WarSide { tag: string; members?: Array<{ tag: string; attacks?: unknown[] }> }
interface Raids { items: Array<{ state: string; members?: Array<{ tag: string; attacks: number; attackLimit: number; bonusAttackLimit: number }> }> }

export const playerCommand: Command = {
  deferred: true,
  definition: { name: "player", description: "Player profiles, linked accounts and remaining attacks", type: 1,
    integration_types: [0, 1], contexts: [0, 1, 2], options: [
      { name: "lookup", description: "Player overview, troops, upgrades and clan history", type: OptionType.Subcommand, options: [{...playerOption,required:false}, userOption] },
      { name: "accounts", description: "List linked accounts and their clans", type: OptionType.Subcommand, options: [userOption] },
      { name: "to-do", description: "Show remaining war, CWL, Legend and raid attacks", type: OptionType.Subcommand, options: [userOption] },
    ] },
  autocomplete: playerAutocomplete,
  async execute(context) {
    const ctx = subcommand(context), emoji = await emojis(ctx);
    if (ctx.path[0] === "lookup") {
      if(stringOption(ctx,"player"))return playerProfileReply(ctx,await fetchPlayer(ctx,await resolvePlayerTag(ctx)),emoji);
      const accounts=(await linkedAccounts(ctx)).filter(account=>!account.hidden);
      const first=accounts.sort((a,b)=>(b.town_hall??0)-(a.town_hall??0))[0];
      if(!first)return gameReply(ctx,"Player lookup","No visible linked accounts found. Choose a player tag or use /link.");
      const options=new Map(ctx.options);
      options.set("__accounts_user",{name:"__accounts_user",type:OptionType.String,value:stringOption(ctx,"discord_user")??invokingUserId(ctx)});
      return playerProfileReply({...ctx,options},await fetchPlayer(ctx,first.player_tag),emoji);
    }
    const accounts = (await linkedAccounts(ctx)).filter(account=>!account.hidden);
    if (!accounts.length) return gameReply(ctx,"Linked accounts", "No linked accounts found. Use /link to add an account.");
    if (ctx.path[0] === "accounts") {
      return playerAccountsReply(ctx, accounts, emoji);
    }
    return todo(ctx, accounts.map(account => account.player_tag));
  },
};

async function todo(ctx: CommandContext, tags: string[]) {
  const emoji = await emojis(ctx), day = legendDay();
  const days: { items: Array<{ tag: string; attacks: number }> } = { items: [] };
  for (let offset = 0; offset < tags.length; offset += 100) {
    const batch = await ctx.services.api.post<typeof days>("/v2/legends/days", { day, tags: tags.slice(offset,offset+100) });
    days.items.push(...batch.items);
  }
  const clanWars = new Map<string, Promise<War | undefined>>(), clanRaids = new Map<string, Promise<Raids>>();
  async function war(clanTag: string): Promise<War | undefined> {
    // A private regular-war log must not prevent an independent CWL lookup.
    const current = await ctx.services.api.get<War>(`/v2/bot/clash/clans/${encodeURIComponent(clanTag)}/currentwar`).catch(error => {
      if(error instanceof ClashKingApiError && [403,404].includes(error.status)) return undefined;
      throw error;
    });
    if (current?.state === "inWar") return current;
    try {
      const group = await ctx.services.api.get<{ rounds?: Array<{ warTags: string[] }> }>(`/v2/bot/clash/clans/${encodeURIComponent(clanTag)}/currentwar/leaguegroup`);
      for (const round of [...(group.rounds ?? [])].reverse()) {
        const wars = await Promise.all(round.warTags.filter(tag => tag !== "#0").map(tag => ctx.services.api.get<War>(`/v2/bot/clash/clanwarleagues/wars/${encodeURIComponent(tag)}`)));
        const active = wars.find(item => item.state === "inWar" && [item.clan.tag,item.opponent.tag].includes(clanTag));
        if (active) return active;
      }
      return undefined;
    } catch (error) { if (error instanceof ClashKingApiError && error.status === 404) return undefined; throw error; }
  }
  const lines: string[] = [];
  // Bound upstream concurrency while sharing clan reads across linked accounts.
  for (let offset = 0; offset < tags.length; offset += 5) {
    lines.push(...await Promise.all(tags.slice(offset,offset+5).map(async tag => {
      try {
        const player = await fetchPlayer(ctx,tag), chores: string[] = [];
        const summary = days.items.find(item => item.tag === tag);
        if (isDailyLegend(player)) chores.push(`${Math.max(0,8-(summary?.attacks ?? 0))}/8 Legend attacks left`);
        else if(player.currentLeagueGroupTag&&player.currentLeagueSeasonId){
          try{
            const [group,limit]=await Promise.all([
              ctx.services.api.get<{members:Array<{playerTag:string;attackWinCount:number;attackLoseCount:number}>}>(`/v2/bot/clash/leaguegroup/${encodeURIComponent(player.currentLeagueGroupTag)}/${player.currentLeagueSeasonId}`,{playerTag:tag}),
              rankedBattleLimit(player.leagueTier?.id??0),
            ]);
            const member=group.members.find(item=>item.playerTag===tag);
            if(member&&limit!==undefined)chores.push(`${Math.max(0,limit-member.attackWinCount-member.attackLoseCount)}/${limit} Ranked attacks left`);
            else chores.push("Ranked attacks unavailable");
          }catch{chores.push("Ranked attacks unavailable");}
        }
        if (player.clan) {
          const clanTag = player.clan.tag;
          if (!clanWars.has(clanTag)) clanWars.set(clanTag,war(clanTag));
          if (!clanRaids.has(clanTag)) clanRaids.set(clanTag,ctx.services.api.get<Raids>(`/v2/bot/clash/clans/${encodeURIComponent(clanTag)}/capitalraidseasons`,{limit:1}));
          const [warResult,raidResult] = await Promise.allSettled([clanWars.get(clanTag)!,clanRaids.get(clanTag)!]);
          if (warResult.status === "fulfilled") {
            const active = warResult.value, member = active && [active.clan,active.opponent].flatMap(side => side.members ?? []).find(item => item.tag === tag);
            if (member) { const limit=active?.attacksPerMember ?? 1; chores.push(`${Math.max(0,limit-(member.attacks?.length ?? 0))}/${limit} war/CWL attacks left`); }
          } else chores.push("War/CWL unavailable");
          if (raidResult.status === "fulfilled") {
            const raid = raidResult.value.items.find(item => item.state === "ongoing"), member=raid?.members?.find(item => item.tag === tag);
            if (raid) { const limit=member ? member.attackLimit+member.bonusAttackLimit : 5; chores.push(`${Math.max(0,limit-(member?.attacks ?? 0))}/${limit} raid attacks left`); }
          } else chores.push("Raids unavailable");
        }
        return `${emoji.get(player.townHallLevel)} ${playerLabel(player)}\n${chores.join(" · ") || "No active attack tasks."}`;
      } catch { return `${tag} · Player unavailable`; }
    })));
  }
  return pagedGameReply(ctx,"Attack to-do",lines,"pt",[stringOption(ctx,"discord_user")??invokingUserId(ctx)],undefined,`Legend day ${day} · Tracked Legend attacks may lag the game`);
}
