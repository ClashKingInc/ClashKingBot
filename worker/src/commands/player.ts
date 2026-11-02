import { actionRow, legacyMessage } from "../discord/components";
import { serverEmbedColor } from "./embed-color";
import { CommandInputError } from "./command-utils";
import { loadCurrentWar, warTime } from "./war-data";
import { invokingUserId, OptionType, stringOption } from "./command-utils";
import {
  emojis,
  isDailyLegend,
  fetchPlayer,
  gameReply,
  legendDay,
  linkedAccounts,
  playerAutocomplete,
  playerLabel,
  playerOption,
  resolvePlayerTag,
  subcommand,
  userOption,
} from "./game-common";
import { rankedBattleLimit } from "./ranked";
import type { Command, CommandContext } from "./types";
import { playerProfileReply } from "./player-profile-pages";

interface War {
  state: string;
  endTime: string;
  attacksPerMember?: number;
  clan: WarSide;
  opponent: WarSide;
}
interface WarSide {
  tag: string;
  members?: Array<{ tag: string; attacks?: unknown[] }>;
}
interface Raids {
  items: Array<{
    state: string;
    members?: Array<{
      tag: string;
      attacks: number;
      attackLimit: number;
      bonusAttackLimit: number;
    }>;
  }>;
}

export const playerCommand: Command = {
  deferred: true,
  definition: {
    name: "player",
    description: "Player profiles and remaining attacks",
    type: 1,
    integration_types: [0, 1],
    contexts: [0, 1, 2],
    options: [
      {
        name: "lookup",
        description: "Player overview, troops, upgrades and clan history",
        type: OptionType.Subcommand,
        options: [{ ...playerOption, required: false }, userOption],
      },
      {
        name: "to-do",
        description:
          "Your linked accounts’ attacks, events and other tasks",
        type: OptionType.Subcommand,
        options: [
          userOption,

        ],
      },
    ],
  },
  autocomplete: playerAutocomplete,
  async execute(context) {
    const ctx = subcommand(context),
      emoji = await emojis(ctx);
    if (ctx.path[0] === "lookup") {
      if (stringOption(ctx, "player"))
        return playerProfileReply(
          ctx,
          await fetchPlayer(ctx, await resolvePlayerTag(ctx)),
          emoji,
        );
      const accounts = (await linkedAccounts(ctx)).filter(
        (account) => !account.hidden,
      );
      const first = accounts.sort(
        (a, b) => (b.town_hall ?? 0) - (a.town_hall ?? 0),
      )[0];
      if (!first)
        return gameReply(
          ctx,
          "Player lookup",
          "No visible linked accounts found. Choose a player tag or use /link.",
        );
      const options = new Map(ctx.options);
      options.set("__accounts_user", {
        name: "__accounts_user",
        type: OptionType.String,
        value: stringOption(ctx, "discord_user") ?? invokingUserId(ctx),
      });
      return playerProfileReply(
        { ...ctx, options },
        await fetchPlayer(ctx, first.player_tag),
        emoji,
      );
    }
    if (ctx.path[0] !== "to-do") throw new CommandInputError("Unknown player command.");
    const visible = (await linkedAccounts(ctx)).filter(account => !account.hidden);
    // Bound fan-out before fetching tasks. Preserve API order for small lists;
    // on large lists verified ownership takes precedence over bookmarks.
    const accounts = visible.length > 20
      ? [...visible.filter(account => account.is_verified), ...visible.filter(account => !account.is_verified)].slice(0,20)
      : visible;
    if (!accounts.length)
      return gameReply(
        ctx,
        "Linked accounts",
        "No linked accounts found. Use /link to add an account.",
      );
    return todo(
      ctx,
      accounts.map((account) => account.player_tag),
    );
  },
};

async function todo(ctx: CommandContext, tags: string[]) {
  const emoji=await emojis(ctx),day=legendDay(),now=Date.now();
  const groups=new Map<string,Array<{line:string;sort:number}>>();
  const unavailable=new Set<string>();
  const add=(group:string,line:string,sort=0)=>{const rows=groups.get(group)??[];rows.push({line,sort});groups.set(group,rows);};
  interface Progress {tag:string;clanGamesPoints:number|null;seasonPoints:number|null;lastCapitalDonation:string|null;lastOnline:string|null}
  const progress=new Map<string,Progress>(),attacks=new Map<string,number>();
  let gamesActive=false;
  for(let offset=0;offset<tags.length;offset+=100){
    const selected=tags.slice(offset,offset+100);
    const [legends,tasks]=await Promise.allSettled([
      ctx.services.api.post<{items:Array<{tag:string;attacks:number}>}>("/v2/legends/days",{day,tags:selected}),
      ctx.services.api.post<{clanGamesActive:boolean;items:Progress[]}>("/v2/bot/players/task-progress",{tags:selected}),
    ]);
    if(legends.status==='fulfilled')for(const row of legends.value.items)attacks.set(row.tag,row.attacks);
    else unavailable.add('Legends');
    if(tasks.status==='fulfilled'){gamesActive=tasks.value.clanGamesActive;for(const row of tasks.value.items)progress.set(row.tag,row);}
    else unavailable.add('event progress');
  }
  const wars=new Map<string,Promise<War|undefined>>(),raids=new Map<string,Promise<Raids>>();
  for(let offset=0;offset<tags.length;offset+=5)await Promise.all(tags.slice(offset,offset+5).map(async tag=>{
    try{
      const player=await fetchPlayer(ctx,tag),label=playerLabel(player);
      if(isDailyLegend(player)){
        if(!unavailable.has('Legends')){const used=attacks.get(tag)??0;if(used<8)add('Legend Hits',`(${used}/8) ${label}`);}
      }else if(player.currentLeagueGroupTag&&player.currentLeagueSeasonId){
        try{
          const [group,limit]=await Promise.all([
            ctx.services.api.get<{members:Array<{playerTag:string;attackWinCount:number;attackLoseCount:number}>}>(`/v2/bot/clash/leaguegroup/${encodeURIComponent(player.currentLeagueGroupTag)}/${player.currentLeagueSeasonId}`,{playerTag:tag}),
            rankedBattleLimit(player.leagueTier?.id??0),
          ]);
          const member=group.members.find(row=>row.playerTag===tag);
          if(member&&limit!==undefined){const used=member.attackWinCount+member.attackLoseCount;if(used<limit)add('Ranked Hits',`(${used}/${limit}) ${label}`);}
          else unavailable.add('Ranked');
        }catch{unavailable.add('Ranked');}
      }
      if(player.clan){
        const clan=player.clan.tag;
        if(!wars.has(clan))wars.set(clan,loadCurrentWar(ctx,clan).then(result=>result.war));
        if(!raids.has(clan))raids.set(clan,ctx.services.api.get<Raids>(`/v2/bot/clash/clans/${encodeURIComponent(clan)}/capitalraidseasons`,{limit:1}));
        const [war,raid]=await Promise.allSettled([wars.get(clan)!,raids.get(clan)!]);
        if(war.status==='fulfilled'){
          const active=war.value;
          // Include preparation as the legacy checklist did, but never retain
          // an ended war just because a cached response still contains members.
          if(active&&['preparation','inWar'].includes(active.state)&&warTime(active.endTime)>now){
            const member=[active.clan,active.opponent].flatMap(side=>side.members??[]).find(row=>row.tag===tag);
            if(member){const limit=active.attacksPerMember??1,used=member.attacks?.length??0;if(used<limit)add('War Hits',`(${used}/${limit}) <t:${Math.floor(warTime(active.endTime)/1000)}:R> — ${label}`,warTime(active.endTime));}
          }
        }else unavailable.add('wars');
        if(raid.status==='fulfilled'&&player.townHallLevel>=6){
          const active=raid.value.items.find(row=>row.state==='ongoing');
          if(active){const member=active.members?.find(row=>row.tag===tag),used=member?.attacks??0,limit=member?member.attackLimit+member.bonusAttackLimit:5;if(used<limit)add('Raid Hits',`(${used}/${limit}) ${label}`);}
        }else if(raid.status==='rejected')unavailable.add('raids');
      }
      const task=progress.get(tag);
      if(gamesActive&&player.townHallLevel>=6){
        if(task?.clanGamesPoints==null)unavailable.add('Clan Games');
        else if(task.clanGamesPoints<4000)add('Clan Games',`(${task.clanGamesPoints}/4000) ${label}`,-task.clanGamesPoints);
      }
      // Keep the legacy useful subset: started but unfinished passes, top ten.
      // Missing observations are not zero progress or evidence of completion.
      if(task?.seasonPoints!=null&&task.seasonPoints>0&&task.seasonPoints<4000)add('Season Pass (Top 10)',`(${task.seasonPoints}/4000) ${label}`,-task.seasonPoints);
      const online=task?.lastOnline?Date.parse(task.lastOnline):NaN;
      if(Number.isFinite(online)&&now-online>=48*3600000)add('Inactive Accounts (48+ hr)',`<t:${Math.floor(online/1000)}:R> — ${label}`,-online);
      const donation=task?.lastCapitalDonation?Date.parse(task.lastCapitalDonation):NaN;
      if(Number.isFinite(donation)&&now-donation>=24*3600000)add('Capital Dono (24+ hr)',`<t:${Math.floor(donation/1000)}:R> — ${label}`,-donation);
    }catch{unavailable.add('some accounts');}
  }));
  const sections=['War Hits','Legend Hits','Ranked Hits','Raid Hits','Clan Games','Season Pass (Top 10)','Inactive Accounts (48+ hr)','Capital Dono (24+ hr)'];
  const pages:string[]=[];let content='';
  for(const heading of sections){
    let rows=(groups.get(heading)??[]).sort((a,b)=>a.sort-b.sort||a.line.localeCompare(b.line));
    if(heading==='Season Pass (Top 10)')rows=rows.slice(0,10);
    let block='';
    for(const row of rows){
      if((content+block+row.line).length>3700){if(block)content+=(content?'\n\n':'')+`**${heading}**\n${block}`;pages.push(content);content='';block='';}
      block+=(block?'\n':'')+row.line;
    }
    if(block)content+=(content?'\n\n':'')+`**${heading}**\n${block}`;
  }
  if(content)pages.push(content);
  if(!pages.length)pages.push(unavailable.size?'Could not load all tasks. Refresh to try again.':"You're all caught up, chief!");
  const target=stringOption(ctx,'discord_user')??invokingUserId(ctx);
  const user=await ctx.services.discordRest.getUser(target);
  const name=user.global_name??user.username;
  const requested=Number(ctx.options.get('__page')?.value??0),page=Number.isSafeInteger(requested)?Math.max(0,Math.min(requested,pages.length-1)):0;
  const id=(index:number)=>`ck:page:pt:${invokingUserId(ctx)}:${target}:${index}`;
  return legacyMessage({allowed_mentions:{parse:[]},embeds:[{
    title:`${name} To-Do List`,description:pages[page],color:await serverEmbedColor(ctx),
    ...(pages.length>1||unavailable.size?{footer:{text:[pages.length>1?`Page ${page+1}/${pages.length}`:'',unavailable.size?`Unavailable: ${[...unavailable].join(', ')}`:''].filter(Boolean).join(' | ')}}:{}),
  }],components:[actionRow(
    ...(pages.length>1?[{type:2 as const,style:2 as const,label:'Previous',custom_id:id(page-1),disabled:page===0},{type:2 as const,style:2 as const,label:'Next',custom_id:id(page+1),disabled:page===pages.length-1}]:[]),
    {type:2,style:2,emoji:emoji.component('refresh')??{name:'↻'},custom_id:id(page)},
  )]});
}
