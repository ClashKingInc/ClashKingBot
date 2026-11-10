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
const route = `/applications/${applicationId}/commands`;
const commandName = process.argv[3];
const definition = commandName ? commandDefinitions.find(command => command.name === commandName) : undefined;
if (commandName && !definition) throw new Error(`Unknown command: ${commandName}`);
const headers = {Authorization: `Bot ${botToken}`, "Content-Type": "application/json"};

async function request(path: string, method: string, body?: unknown): Promise<unknown> {
  const response = await fetch(`https://discord.com/api/v10${path}`, {
    method, headers, ...(body === undefined ? {} : {body: JSON.stringify(body)}),
  });
  if (!response.ok) throw new Error(`Discord command registration failed with HTTP ${response.status}`);
  return response.json();
}

// A mistargeted credential must never overwrite another application's commands.
const identity = await request("/users/@me", "GET") as {id: string};
if (identity.id !== applicationId) throw new Error("Bot credential does not match DISCORD_APPLICATION_ID");
if (definition) {
  const installed = await request(route, "GET") as Array<{id: string; name: string; type: number}>;
  const existing = installed.find(command => command.name === definition.name && command.type === definition.type);
  if (!existing) throw new Error(`Command ${commandName} is not installed; use full registration to create it`);
  // Scoped releases must not replace unrelated live command definitions.
  await request(`${route}/${existing.id}`, "PATCH", definition);
  console.log(`Registered global ${environment} command: ${definition.name}`);
} else {
  await request(route, "PUT", commandDefinitions);
  console.log(`Registered global ${environment} commands`);
}

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}
