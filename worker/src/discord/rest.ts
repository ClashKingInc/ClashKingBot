import { DiscordConfig, DiscordREST, DiscordRESTMemoryLive } from 'dfx';
import type { DiscordRestService } from 'dfx/DiscordREST';
import { Effect, Layer, ManagedRuntime, Redacted } from 'effect';
import { FetchHttpClient } from 'effect/http';

export class DiscordRestError extends Error {
 constructor(readonly status:number, readonly body:string, readonly retryAfterSeconds?:number, options?:ErrorOptions) { super('Discord API request failed with '+status, options); }
}
type PromiseMethod<F> = F extends (...args:infer P)=>Effect.Effect<infer A, infer _E, never> ? (...args:P)=>Promise<A> : never;
export type DiscordClient = { [K in Exclude<keyof DiscordRestService,'httpClient'|'withFiles'|'withFormData'>]: PromiseMethod<DiscordRestService[K]> } & {
 readonly applicationId:string;
 run<A,E>(f:(rest:DiscordRestService)=>Effect.Effect<A,E>):Promise<A>;
};

// Only bridges the existing Promise-based command handlers to Effect. The
// method names, requests, authentication, files and rate limits belong to dfx.
// Reuse one SDK runtime per application/token so both bucket knowledge and
// scoped services survive interactions without accumulating unclosed runtimes.
const clients = new Map<string, {token:string;fetch:typeof fetch|undefined;client:DiscordClient;dispose:()=>Promise<void>}>();

export function createDiscordClient(options:{applicationId:string;token:string;fetch?:typeof fetch}):DiscordClient {
 const entry=clients.get(options.applicationId);
 if(entry?.token===options.token&&entry.fetch===options.fetch)return entry.client;
 if(entry)void entry.dispose().catch(()=>undefined);
 const runtime=ManagedRuntime.make(DiscordRESTMemoryLive.pipe(Layer.provide([
  DiscordConfig.layer({token:Redacted.make(options.token)}),
  FetchHttpClient.layer.pipe(Layer.provide(Layer.succeed(FetchHttpClient.Fetch,options.fetch??globalThis.fetch.bind(globalThis)))),
 ])));
 const run=<A,E>(f:(rest:DiscordRestService)=>Effect.Effect<A,E>):Promise<A>=>runtime.runPromise(Effect.flatMap(DiscordREST,f).pipe(Effect.mapError(error=>{
  if(error && typeof error==='object' && 'response' in error && error.response && typeof error.response==='object' && 'status' in error.response){
   const data='data' in error?error.data:undefined;
   const retry=data && typeof data==='object' && 'retry_after' in data ? Number(data.retry_after):undefined;
   return new DiscordRestError(Number(error.response.status),JSON.stringify(data??{}),retry,{cause:new Error('Discord provider failure '+('_tag' in error ? String(Reflect.get(error,'_tag')) : 'HTTP'))});
  }
  return error;
 })),{signal:AbortSignal.timeout(10_000)});
 const client = new Proxy({applicationId:options.applicationId,run},{get(target,key){
  if(key==='applicationId'||key==='run')return Reflect.get(target,key);
  return (...args:unknown[])=>run(rest=>{ const effect=Reflect.apply(Reflect.get(rest,key),rest,args); if(!Effect.isEffect(effect)) return Effect.die(new Error("Invalid dfx method")); return effect as Effect.Effect<unknown,unknown>; });
 }}) as DiscordClient;
 clients.set(options.applicationId,{token:options.token,fetch:options.fetch,client,dispose:()=>runtime.dispose()});
 return client;
}
