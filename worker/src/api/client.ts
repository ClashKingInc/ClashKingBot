export interface ClashKingApiClientOptions {
  baseUrl: string;
  fetch?: typeof fetch;
  token: string;
}

export class ClashKingApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: string,
    readonly path?: string,
    readonly retryAfterSeconds?: number,
  ) {
    super(`ClashKing API request failed with ${status}`);
  }
}

/** Business data always goes through this client, never through Hyperdrive. */
export class ClashKingApiClient {
  readonly #baseUrl: string;
  readonly #fetch: typeof fetch;
  readonly #token: string;
  #readObserver?: (path:string,body:unknown)=>void;
  observeSuccessfulReads(observer:(path:string,body:unknown)=>void){this.#readObserver=observer;}

  constructor(options: ClashKingApiClientOptions) {
    this.#baseUrl = stripTrailingSlash(options.baseUrl);
    this.#fetch = options.fetch ?? globalThis.fetch.bind(globalThis);
    this.#token = options.token;
  }

  get<T>(path: string, query: Record<string, string | number | boolean | undefined> = {}, signal?: AbortSignal): Promise<T> {
    const url = new URL(`${this.#baseUrl}${normalizePath(path)}`);
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
    return this.#request<T>(url, { method: "GET", ...(signal ? { signal } : {}) });
  }

  post<T>(path: string, body: unknown): Promise<T> {
    return this.#write<T>("POST", path, body);
  }

  postIfAbsent<T>(path: string, body: unknown): Promise<T> {
    return this.#request<T>(new URL(`${this.#baseUrl}${normalizePath(path)}`), {
      method: "POST", body: JSON.stringify(body), headers: { "X-ClashKing-Create-Only": "true" },
    });
  }

  postEmpty<T>(path: string): Promise<T> {
    return this.#request<T>(new URL(`${this.#baseUrl}${normalizePath(path)}`), { method: "POST" });
  }

  postForm<T>(path: string, body: FormData): Promise<T> {
    return this.#request<T>(new URL(`${this.#baseUrl}${normalizePath(path)}`), {
      body,
      method: "POST",
    });
  }

  put<T>(path: string, body: unknown): Promise<T> {
    return this.#write<T>("PUT", path, body);
  }

  patch<T>(path: string, body: unknown): Promise<T> {
    return this.#write<T>("PATCH", path, body);
  }

  delete<T>(path: string, body?: unknown): Promise<T> {
    return this.#write<T>("DELETE", path, body);
  }

  #write<T>(method: "DELETE" | "PATCH" | "POST" | "PUT", path: string, body?: unknown): Promise<T> {
    return this.#request<T>(new URL(`${this.#baseUrl}${normalizePath(path)}`), {
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      method,
    });
  }

  async #request<T>(url: URL, init: RequestInit): Promise<T> {
    const response = await this.#fetch(url, {
      ...init,
      signal: init.signal ? AbortSignal.any([init.signal, AbortSignal.timeout(30000)]) : AbortSignal.timeout(30000),
      headers: {
        ...Object.fromEntries(new Headers(init.headers)),
        Accept: "application/json",
        Authorization: `Bearer ${this.#token}`,
        ...(typeof init.body === "string" ? { "Content-Type": "application/json" } : {}),
      },
    });
    if (!response.ok) {
      throw new ClashKingApiError(response.status, await response.text(), url.pathname, response.status===429?Number(response.headers.get("retry-after"))||undefined:undefined);
    }
    if (response.status === 204) {
      return undefined as T;
    }
    const body=await response.json<T>();
    if(init.method === "GET")this.#readObserver?.(url.pathname,body);
    return body;
  }
}

function normalizePath(path: string): string {
  return path.startsWith("/") ? path : `/${path}`;
}

function stripTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}
