import type { DiscordClient } from "./rest";

type CommandInventory = { expires: number; ids: ReadonlyMap<string, string>; pending?: Promise<ReadonlyMap<string, string>> };
const inventories = new Map<string, CommandInventory>();

export async function commandMentions(rest: DiscordClient): Promise<(path: string) => string> {
  const key = rest.applicationId;
  const entry = inventories.get(key) ?? { expires: 0, ids: new Map<string, string>() };
  if (entry.expires <= Date.now() && !entry.pending) {
    entry.pending = rest.listApplicationCommands(rest.applicationId).then(commands => {
      entry.ids = new Map((commands ?? []).filter(command => command.type === 1).map(command => [command.name, command.id]));
      entry.expires = Date.now() + 300_000;
      return entry.ids;
    }).catch(() => {
      // Help remains readable during a Discord outage. Keep known IDs and retry
      // shortly; an unavailable inventory must not break a valid help request.
      entry.expires = Date.now() + 30_000;
      return entry.ids;
    }).finally(() => { entry.pending = undefined; });
    inventories.set(key, entry);
  }
  const ids = await (entry.pending ?? Promise.resolve(entry.ids));
  return path => {
    const id = ids.get(path.split(" ")[0]!);
    return id ? `</${path}:${id}>` : `**/${path}**`;
  };
}
