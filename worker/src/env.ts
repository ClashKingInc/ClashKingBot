export type Env = Omit<Cloudflare.Env, "LOCAL_TEST_USER_ID" | "DASHBOARD_BASE_URL" | "CLASHKING_API_BASE_URL"> & {
  LOCAL_TEST_USER_ID: string;
  DASHBOARD_BASE_URL: string;
  CLASHKING_API_BASE_URL: string;
};
export type AppEnvironment = Env["APP_ENV"];
