import { createDiscordClient } from "../src/discord/rest";
import { commandDefinitions } from "../src/commands/registry";

if (commandDefinitions.length > 100) {
  throw new Error(`Cannot register ${commandDefinitions.length} global commands; Discord allows at most 100`);
}

type Environment = "dev" | "prod";

const environment = process.argv[2] as Environment | undefined;
if (environment !== "dev" && environment !== "prod") {
  throw new Error("Usage: register-commands.ts <dev|prod> [command-name]");
}

const applicationId = required("DISCORD_APPLICATION_ID");
const botToken = required("DISCORD_BOT_TOKEN");
const rest = createDiscordClient({applicationId, token:botToken});
const commandName = process.argv[3];
const definition = commandName ? commandDefinitions.find(command => command.name === commandName) : undefined;
if (commandName && !definition) throw new Error(`Unknown command: ${commandName}`);
// A mistargeted credential must never overwrite another application's commands.
const identity = await rest.getMyUser();
if (identity.id !== applicationId) throw new Error("Bot credential does not match DISCORD_APPLICATION_ID");
if (definition) {
  const installed = (await rest.listApplicationCommands(applicationId)) ?? [];
  const existing = installed.find(command => command.name === definition.name && command.type === definition.type);
  if (!existing) throw new Error(`Command ${commandName} is not installed; use full registration to create it`);
  // Scoped releases must not replace unrelated live command definitions.
  await rest.updateApplicationCommand(applicationId,existing.id,definition as Parameters<typeof rest.updateApplicationCommand>[2]);
  console.log(`Registered global ${environment} command: ${definition.name}`);
} else {
  await rest.bulkSetApplicationCommands(applicationId,commandDefinitions as Parameters<typeof rest.bulkSetApplicationCommands>[1]);
  console.log(`Registered global ${environment} commands`);
}

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}
