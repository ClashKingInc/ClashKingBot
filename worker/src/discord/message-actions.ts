import type { DiscordClient } from './rest';
import { DiscordRestError } from './rest';
import { normalizeMessageControls } from './message-controls';

export async function getOriginalInteractionResponse(rest:DiscordClient,token:string){
 for(let attempt=0;;attempt++){
  try{return await rest.getOriginalWebhookMessage(rest.applicationId,token);}
  catch(error){if(!(error instanceof DiscordRestError)||error.status!==404||attempt>=3)throw error;await new Promise(r=>setTimeout(r,100));}
 }
}
export async function editOriginalInteractionResponse(rest:DiscordClient,token:string,data:Record<string,unknown>){
 const {__files,...payload}=await normalizeMessageControls(data,rest);
 const files=Array.isArray(__files)?(__files as Array<{name:string;bytes:Uint8Array}>).map(f=>new File([new Uint8Array(f.bytes)],f.name,{type:'image/png'})):[];
 if(files.length)payload.attachments=files.map((f,id)=>({id,filename:f.name}));
 return rest.run(api=>api.updateOriginalWebhookMessage(rest.applicationId,token,{payload:payload as Parameters<typeof api.updateOriginalWebhookMessage>[2]['payload']}).pipe(files.length ? api.withFiles(files) : effect => effect));
}
export async function createInteractionFollowup(rest:DiscordClient,token:string,data:Record<string,unknown>){
 const {__files,...payload}=await normalizeMessageControls(data,rest);
 const files=Array.isArray(__files)?(__files as Array<{name:string;bytes:Uint8Array}>).map(f=>new File([new Uint8Array(f.bytes)],f.name,{type:'image/png'})):[];
 if(files.length)payload.attachments=files.map((f,id)=>({id,filename:f.name}));
 return rest.run(api=>api.executeWebhook(rest.applicationId,token,{payload:payload as Parameters<typeof api.executeWebhook>[2]['payload']}).pipe(files.length ? api.withFiles(files) : effect => effect));
}
export async function editChannelMessage(rest:DiscordClient,channel:string,message:string,data:Record<string,unknown>){
 const payload=await normalizeMessageControls(data,rest);
 return rest.updateMessage(channel,message,payload as Parameters<DiscordClient['updateMessage']>[2]);
}
export async function downloadDiscordAttachment(url: string, maxBytes = 25 * 1024 * 1024): Promise<Blob> {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || !["cdn.discordapp.com", "media.discordapp.net"].includes(parsed.hostname)
      || parsed.username || parsed.password || parsed.port) throw new Error("Untrusted attachment URL");
    const response = await fetch(url, { redirect: "manual" });
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

