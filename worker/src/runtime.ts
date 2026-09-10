import { Context, Effect, Layer } from "effect";

import type { CommandServices } from "./commands/types";
import type { Env } from "./env";
import { createServices } from "./services";

export class Services extends Context.Tag("@clashking/bot/Services")<Services, CommandServices>() {}

export function servicesLayer(env: Env): Layer.Layer<Services> {
  return Layer.succeed(Services, createServices(env));
}

export function runWithServices<A>(env: Env, program: Effect.Effect<A, unknown, Services>): Promise<A> {
  return Effect.runPromise(Effect.provide(program, servicesLayer(env)));
}
