import { discordRateLimitedFetch, DiscordRateWait } from "./rate-limits";
import { normalizeMessageControls } from "./message-controls";
import type {
  DiscordApplicationEmoji,
  DiscordChannel,
  DiscordGuild,
  DiscordInteractionResponse,
  DiscordMember,
  DiscordRole,
  DiscordUser,
} from "./types";

const DISCORD_API_BASE_URL = "https://discord.com/api/v10";

export class DiscordRestError extends Error {
  constructor(
    readonly status: number,
    readonly body: string,
    readonly retryAfterSeconds?: number,
  ) {
    super(`Discord API request failed with ${status}`);
  }
}

export class DiscordRestClient {
  readonly #applicationId: string;
  readonly #fetch: typeof fetch;
  readonly #token: string;

  constructor(options: { applicationId: string; fetch?: typeof fetch; token: string }) {
    this.#applicationId = options.applicationId;
    this.#fetch = options.fetch ?? globalThis.fetch.bind(globalThis);
    this.#token = options.token;
  }

  get applicationId(): string {
    return this.#applicationId;
  }

  getGuild(id: string): Promise<DiscordGuild> {
    return this.get(`/guilds/${id}`);
  }

  getChannel(id: string): Promise<DiscordChannel> {
    return this.get(`/channels/${id}`);
  }

  getUser(id: string): Promise<DiscordUser> {
    return this.get(`/users/${id}`);
  }

  getGuildMember(guildId: string, userId: string): Promise<DiscordMember> {
    return this.get(`/guilds/${guildId}/members/${userId}`);
  }

  getGuildRoles(guildId: string): Promise<DiscordRole[]> {
    return this.get(`/guilds/${guildId}/roles`);
  }

  async listApplicationEmojis(signal?: AbortSignal): Promise<DiscordApplicationEmoji[]> {
    const result = await this.request<{ items: DiscordApplicationEmoji[] }>(
      `/applications/${this.#applicationId}/emojis`,
      { method: "GET", ...(signal ? { signal } : {}) },
    );
    return result.items;
  }

  createGuildEmoji(guildId: string, name: string, image: string): Promise<{id:string;name:string}> {
    return this.request(`/guilds/${guildId}/emojis`, { method: "POST", body: JSON.stringify({ name, image }) });
  }

  createApplicationEmoji(name: string, image: string): Promise<DiscordApplicationEmoji> {
    return this.request(`/applications/${this.#applicationId}/emojis`, {
      body: JSON.stringify({ image, name }),
      method: "POST",
    });
  }

  renameApplicationEmoji(id: string, name: string): Promise<DiscordApplicationEmoji> {
    return this.request(`/applications/${this.#applicationId}/emojis/${id}`, {
      body: JSON.stringify({ name }),
      method: "PATCH",
    });
  }

  async deleteApplicationEmoji(id: string): Promise<void> {
    await this.request<undefined>(`/applications/${this.#applicationId}/emojis/${id}`, {
      method: "DELETE",
    });
  }

  async getOriginalInteractionResponse(interactionToken: string): Promise<{id:string;channel_id:string}> {
    for(let attempt=0;;attempt++){
      try{return await this.request(`/webhooks/${this.#applicationId}/${interactionToken}/messages/@original`,{method:"GET"},false);}
      catch(error){
        // The deferred HTTP acknowledgement can still be in flight when the
        // background handler first asks Discord for its public message.
        if(!(error instanceof DiscordRestError)||error.status!==404||attempt>=3)throw error;
        await new Promise(resolve=>setTimeout(resolve,100));
      }
    }
  }

  async editOriginalInteractionResponse(
    interactionToken: string,
    data: NonNullable<DiscordInteractionResponse["data"]>,
  ): Promise<void> {
    const { __files, ...payload } = await normalizeMessageControls(data, this);
    let body: BodyInit = JSON.stringify(payload);
    if (Array.isArray(__files) && __files.length) {
      // Files are internal command output, never Discord JSON fields. Replace
      // attachments on each page update so old graphs do not accumulate.
      const form = new FormData();
      const files = __files as Array<{ name: string; bytes: Uint8Array }>;
      form.set("payload_json", JSON.stringify({ ...payload, attachments: files.map((file,index)=>({id:index,filename:file.name})) }));
      files.forEach((file,index)=>form.set(`files[${index}]`,new Blob([new Uint8Array(file.bytes)],{type:"image/png"}),file.name));
      body = form;
    }
    await this.request<unknown>(
      `/webhooks/${this.#applicationId}/${interactionToken}/messages/@original`,
      {
        body,
        method: "PATCH",
      },
      false,
    );
  }

  async createInteractionFollowup(interactionToken: string, data: NonNullable<DiscordInteractionResponse["data"]>): Promise<void> {
    await this.request<unknown>(`/webhooks/${this.#applicationId}/${interactionToken}`, {
      body: JSON.stringify(await normalizeMessageControls(data, this)), method: "POST",
    }, false);
  }

  async deleteOriginalInteractionResponse(interactionToken:string):Promise<void>{
    await this.request<undefined>(`/webhooks/${this.#applicationId}/${interactionToken}/messages/@original`,{method:"DELETE"},false);
  }

  async editChannelMessage(
    channelId: string,
    messageId: string,
    data: Record<string, unknown>,
  ): Promise<void> {
    await this.request<unknown>(`/channels/${channelId}/messages/${messageId}`, {
      body: JSON.stringify(await normalizeMessageControls(data, this)),
      method: "PATCH",
    });
  }

  async download(url: string, maxBytes = 25 * 1024 * 1024): Promise<Blob> {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || !["cdn.discordapp.com", "media.discordapp.net"].includes(parsed.hostname)
      || parsed.username || parsed.password || parsed.port) throw new Error("Untrusted attachment URL");
    const response = await this.#fetch(url, { redirect: "manual" });
    if (!response.ok) {
      throw new DiscordRestError(response.status, await response.text());
    }
    if (Number(response.headers.get("content-length")) > maxBytes) {
      await response.body?.cancel();
      throw new Error("Attachment exceeds size limit");
    }
    if (!response.body) throw new Error("Attachment has no body");
    const reader = response.body.getReader();
    const chunks: Uint8Array<ArrayBuffer>[] = [];
    let bytes = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > maxBytes) {
          await reader.cancel();
          throw new Error("Attachment exceeds size limit");
        }
        chunks.push(new Uint8Array(value));
      }
    } finally { reader.releaseLock(); }
    return new Blob(chunks, { type: response.headers.get("content-type") ?? "application/octet-stream" });
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "GET" });
  }

  async request<T>(path: string, init: RequestInit, authenticated = true): Promise<T> {
    const send = () => this.#fetch(`${DISCORD_API_BASE_URL}${path}`, {
      ...init,
      signal: init.signal ?? AbortSignal.timeout(10_000),
      headers: {
        ...(authenticated ? { Authorization: `Bot ${this.#token}` } : {}),
        ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      },
    });
    let response:Response;
    try{response=authenticated?await discordRateLimitedFetch(this.#applicationId,path,init,send):await send();}
    catch(error){if(error instanceof DiscordRateWait)throw new DiscordRestError(429,"",error.seconds);throw error;}
    if (!response.ok) {
      const body=await response.text();let delay:number|undefined;
      if(response.status===429){let seconds=Number(response.headers.get("retry-after"));try{seconds=Math.max(seconds,Number(JSON.parse(body).retry_after)||0);}catch{/* Header remains authoritative. */}delay=Number.isFinite(seconds)&&seconds>0?Math.ceil(seconds)+1:1;}
      throw new DiscordRestError(response.status, body,delay);
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return response.json() as Promise<T>;
  }
}
