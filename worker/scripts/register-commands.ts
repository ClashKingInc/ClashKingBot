import { commandDefinitions } from "../src/commands/registry";

if (commandDefinitions.length > 100) {
  throw new Error(`Cannot register ${commandDefinitions.length} global commands; Discord allows at most 100`);
}

type Environment = "dev" | "prod";

const environment = process.argv[2] as Environment | undefined;
if (environment !== "dev" && environment !== "prod") {
  throw new Error("Usage: register-commands.ts <dev|prod>");
}

const applicationId = required("DISCORD_APPLICATION_ID");
const botToken = required("DISCORD_BOT_TOKEN");
const route = `/applications/${applicationId}/commands`;

const response = await fetch(`https://discord.com/api/v10${route}`, {
  body: JSON.stringify(commandDefinitions),
  headers: {
    Authorization: `Bot ${botToken}`,
    "Content-Type": "application/json",
  },
  method: "PUT",
});

if (!response.ok) {
  throw new Error(`Discord command registration failed with HTTP ${response.status}`);
}

const registered = (await response.json()) as unknown[];
console.log(`Registered ${registered.length} global ${environment} commands`);

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}
