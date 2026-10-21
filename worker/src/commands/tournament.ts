import { actionRow, legacyMessage, linkButton } from '../discord/components';
import { CommandInputError, invokingUserId, OptionType, requireGuildId, stringOption } from './command-utils';
import { escapeMarkdown, subcommand } from './game-common';
import { serverEmbedColor } from './embed-color';
import type { Command, CommandContext } from './types';

interface Tournament {
  id: string; serverId: string; name: string; format: string; teamSize: number;
  startsAt: string; endsAt: string; status: string;
}
interface Participant { teamId: string; clanName: string; withdrawnAt?: string | null }
interface Match {
  id: string; round: number; homeTeamId: string; awayTeamId: string;
  homeScore: number | null; awayScore: number | null; status: string;
}
const idPattern = /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/iu;
const appUrl = (ctx: CommandContext, id?: string) =>
  `https://${ctx.env.APP_ENV === 'dev' ? 'local-app' : 'app'}.clashk.ing/tournaments${id ? `/${encodeURIComponent(id)}` : ''}`;
const date = (value: string) => {
  const seconds = Math.floor(Date.parse(value) / 1000);
  return Number.isFinite(seconds) ? `<t:${seconds}:f>` : 'Not scheduled';
};
const label = (value: string) => escapeMarkdown(value.replace(/[\r\n\u202a-\u202e\u2066-\u2069]/gu, ' ').slice(0, 100));
const tournamentOption = { name: 'tournament', description: 'Choose a tournament', type: OptionType.String, required: true, autocomplete: true };

export const tournamentCommand: Command = {
  deferred: true,
  definition: {
    name: 'tournament', description: 'Browse tournaments, results and organizer tools', type: 1,
    contexts: [0], integration_types: [0], options: [
      { name: 'browse', description: 'Browse this server’s tournaments', type: OptionType.Subcommand },
      { name: 'view', description: 'View a tournament and its latest results', type: OptionType.Subcommand, options: [tournamentOption] },
      { name: 'manage', description: 'Open the server dashboard to manage tournaments', type: OptionType.Subcommand },
    ],
  },
  async autocomplete(ctx) {
    const serverId = requireGuildId(ctx);
    const query = String(ctx.interaction.data?.options?.[0]?.options?.find(o => o.focused)?.value ?? '').toLocaleLowerCase();
    const { items } = await ctx.services.api.get<{ items: Tournament[] }>('/v2/competitive/tournaments', {}, AbortSignal.timeout(1500));
    return items.filter(t => t.serverId === serverId && idPattern.test(t.id) && t.name.toLocaleLowerCase().includes(query))
      .slice(0, 25).map(t => ({ name: `${t.name} · ${t.teamSize}v${t.teamSize} · ${t.status}`.slice(0, 100), value: t.id }));
  },
  async execute(context) {
    const ctx = subcommand(context);
    const serverId = requireGuildId(ctx);
    if (ctx.path[0] === 'manage') {
      // Grant consumption checks the clicking Discord identity again. Never put
      // the one-use code in a query string or give it to a public message.
      const grant = await ctx.services.api.post<{ code: string }>(`/v2/server/${serverId}/dashboard-access-grants`, { source: 'bot', userId: invokingUserId(ctx) });
      const url = new URL('/access', ctx.env.DASHBOARD_BASE_URL);
      url.hash = new URLSearchParams({ code: grant.code }).toString();
      return legacyMessage({ content: 'Open Tournaments in this server’s dashboard. This private sign-in link expires in 2 minutes.', components: [actionRow(linkButton('Open dashboard', url.toString()))] }, { ephemeral: true });
    }
    if (ctx.path[0] === 'browse') {
      const { items } = await ctx.services.api.get<{ items: Tournament[] }>('/v2/competitive/tournaments');
      const selected = items.filter(t => t.serverId === serverId).slice(0, 12);
      return legacyMessage({ embeds: [{ title: 'Tournaments', color: await serverEmbedColor(ctx), description: selected.length
        ? selected.map(t => `**[${label(t.name)}](${appUrl(ctx, t.id)})**\n${t.teamSize}v${t.teamSize} · ${label(t.status)} · Free entry\n${date(t.startsAt)}`).join('\n\n')
        : 'No published tournaments for this server yet.' }], components: [actionRow(linkButton('Open tournaments', appUrl(ctx)))] });
    }
    const id = stringOption(ctx, 'tournament') ?? '';
    if (!idPattern.test(id)) throw new CommandInputError('Choose a valid tournament.');
    const result = await ctx.services.api.get<{ tournament: Tournament; participants: Participant[]; matches: Match[] }>(`/v2/competitive/tournaments/${id}`);
    // A copied autocomplete ID must not make this server command display another
    // server's event or leak its administrative/internal team names.
    if (result.tournament.serverId !== serverId) throw new CommandInputError('Choose a tournament from this server.');
    const t = result.tournament;
    const names = new Map(result.participants.map(p => [p.teamId, label(p.clanName)]));
    const matches = result.matches.slice(-8).map(m => `${names.get(m.homeTeamId) ?? 'Clan'} **${m.homeScore ?? '—'} – ${m.awayScore ?? '—'}** ${names.get(m.awayTeamId) ?? 'Clan'} · ${label(m.status)}`);
    return legacyMessage({ embeds: [{ title: label(t.name), color: await serverEmbedColor(ctx), description: [
      `${t.teamSize}v${t.teamSize} · ${label(t.format.replaceAll('_', ' '))} · Free entry`,
      `${date(t.startsAt)} → ${date(t.endsAt)}`,
      `${result.participants.filter(p => !p.withdrawnAt).length} teams · ${label(t.status)}`,
      ...(matches.length ? ['**Matches**', ...matches] : ['No matches scheduled yet.']),
    ].join('\n'), }], components: [actionRow(linkButton('Open tournament', appUrl(ctx, id)))] });
  },
};
