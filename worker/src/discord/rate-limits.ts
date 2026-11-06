// Share learned Discord buckets across REST clients in this isolate. Provider
// 429s remain authoritative across other workers/processes using the same bot.
type Bucket={until:number;tail:Promise<void>};
type Limits={globalUntil:number;nextRequest:number;buckets:Map<string,Bucket>;routes:Map<string,string>};
const applications=new Map<string,Limits>();
const sleep=(ms:number)=>new Promise<void>(resolve=>setTimeout(resolve,ms));
export class DiscordRateWait extends Error {constructor(readonly seconds:number){super('Discord rate limit is active');}}
export async function discordRateLimitedFetch(application:string,path:string,init:RequestInit,send:()=>Promise<Response>):Promise<Response>{
  let limits=applications.get(application);
  if(!limits){limits={globalUntil:0,nextRequest:0,buckets:new Map(),routes:new Map()};applications.set(application,limits);}
  const major=/^\/(?:guilds|channels)\/(\d+)/u.exec(path)?.[1]??'global';
  const route=`${init.method??'GET'}:${path.split('?')[0]!.replace(/\d{15,20}/gu,':id')}:${major}`;
  const key=limits.routes.get(route)??route;
  let bucket=limits.buckets.get(key);
  if(!bucket){bucket={until:0,tail:Promise.resolve()};limits.buckets.set(key,bucket);}
  const previous=bucket.tail;
  let release!:()=>void;bucket.tail=new Promise<void>(resolve=>{release=resolve;});
  await previous;
  try{
    const scheduled=Math.max(Date.now(),limits.globalUntil,bucket.until,limits.nextRequest);
    const wait=scheduled-Date.now();
    // Long waits belong to the durable job's due_at, not an HTTP invocation.
    if(wait>5000)throw new DiscordRateWait(Math.ceil(wait/1000));
    limits.nextRequest=scheduled+25;
    if(wait>0)await sleep(wait);
    if(limits.globalUntil>Date.now())throw new DiscordRateWait(Math.ceil((limits.globalUntil-Date.now())/1000));
    const response=await send();
    const reset=Number(response.headers.get('x-ratelimit-reset-after'));
    const hash=response.headers.get('x-ratelimit-bucket');
    if(hash){
      const learned=`${hash}:${major}`;limits.routes.set(route,learned);
      const shared=limits.buckets.get(learned);
      if(shared&&shared!==bucket){shared.until=Math.max(bucket.until,shared.until);bucket=shared;}
      else limits.buckets.set(learned,bucket);
    }
    if(response.headers.get('x-ratelimit-remaining')==='0'&&Number.isFinite(reset))bucket.until=Math.max(bucket.until,Date.now()+reset*1000+50);
    if(response.status===429){
      let body:{retry_after?:unknown;global?:unknown}={};try{body=await response.clone().json();}catch{/* Header fallback below. */}
      const values=[Number(body.retry_after),Number(response.headers.get('retry-after'))].filter(n=>Number.isFinite(n)&&n>0);
      const delay=(values.length?Math.max(...values):1)*1000+50;
      if(body.global===true||response.headers.get('x-ratelimit-global')==='true')limits.globalUntil=Date.now()+delay;
      else bucket.until=Date.now()+delay;
      console.warn('Discord request deferred by provider',{route:route.replace(/:\d{15,20}$/u,':major'),global:body.global===true,retryAfterSeconds:Math.ceil(delay/1000)});
    }
    return response;
  }finally{release();}
}
