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
    this.#fetch = options.fetch ?? fetch;
    this.#token = options.token;
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

  async listApplicationEmojis(): Promise<DiscordApplicationEmoji[]> {
    const result = await this.get<{ items: DiscordApplicationEmoji[] }>(
      `/applications/${this.#applicationId}/emojis`,
    );
    return result.items;
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

  async editOriginalInteractionResponse(
    interactionToken: string,
    data: NonNullable<DiscordInteractionResponse["data"]>,
  ): Promise<void> {
    await this.request<unknown>(
      `/webhooks/${this.#applicationId}/${interactionToken}/messages/@original`,
      {
        body: JSON.stringify(data),
        method: "PATCH",
      },
      false,
    );
  }

  async editChannelMessage(
    channelId: string,
    messageId: string,
    data: Record<string, unknown>,
  ): Promise<void> {
    await this.request<unknown>(`/channels/${channelId}/messages/${messageId}`, {
      body: JSON.stringify(data),
      method: "PATCH",
    });
  }

  async download(url: string): Promise<Blob> {
    const response = await this.#fetch(url);
    if (!response.ok) {
      throw new DiscordRestError(response.status, await response.text());
    }
    return response.blob();
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "GET" });
  }

  async request<T>(path: string, init: RequestInit, authenticated = true): Promise<T> {
    const response = await this.#fetch(`${DISCORD_API_BASE_URL}${path}`, {
      ...init,
      headers: {
        ...(authenticated ? { Authorization: `Bot ${this.#token}` } : {}),
        "Content-Type": "application/json",
      },
    });
    if (!response.ok) {
      throw new DiscordRestError(response.status, await response.text());
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return response.json() as Promise<T>;
  }
}
