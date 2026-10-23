import type { CommandContext } from "./types";

const defaultColor=2829617;
const colors=new Map<string,{expires:number;value:Promise<number>}>();

/** Use the server setting for ordinary game embeds, including explicit black.
 * The short, environment-scoped cache avoids a settings request per button. */
export function serverEmbedColor(ctx:Pick<CommandContext,"interaction"|"services"|"env">):Promise<number>{
  const guild=ctx.interaction.guild_id;
  if(!guild)return Promise.resolve(defaultColor);
  const key=`${ctx.env.CLASHKING_API_BASE_URL}:${ctx.env.DISCORD_APPLICATION_ID}:${guild}`;
  const cached=colors.get(key);
  if(cached&&cached.expires>Date.now())return cached.value;
  const value=ctx.services.api.get<{embed_color?:string|number}>(`/v2/server/${guild}/settings`)
    .then(settings=>{
      const raw=settings.embed_color;
      const parsed=typeof raw==="string"&&raw.startsWith("#")?Number.parseInt(raw.slice(1),16):raw===undefined||String(raw).trim()===""?NaN:Number(raw);
      return Number.isInteger(parsed)&&parsed>=0&&parsed<=0xffffff?parsed:defaultColor;
    }).catch(()=>defaultColor);
  if(colors.size>=512)colors.delete(colors.keys().next().value!);
  colors.set(key,{expires:Date.now()+30_000,value});
  return value;
}
