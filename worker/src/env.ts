export type AppEnvironment = "dev" | "prod";

export interface Env {
  APP_ENV: AppEnvironment;
  CLASHKING_API_BASE_URL: string;
  CLASHKING_API_TOKEN: string;
  DISCORD_APPLICATION_ID: string;
  DISCORD_BOT_TOKEN: string;
  DISCORD_PUBLIC_KEY: string;
}
