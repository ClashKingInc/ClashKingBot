import { ClashKingApiError } from "../api/client";
import { actionRow, legacyMessage, linkButton } from "../discord/components";
import { InteractionResponseType, MessageFlags, type DiscordInteraction, type DiscordInteractionResponse } from "../discord/types";
import { CommandInputError, OptionType } from "./command-utils";
import { applicationEmojis } from "../discord/emojis";
import type { Command, CommandServices } from "./types";
import type { Env } from "../env";
import { serverEmbedColor } from "./embed-color";

interface Army { shareCode: string; armyLink: string; savedAt: string; mainTroops: Array<{id:number;quantity:number}> }
interface Presentation {
  minimumTownHall:number;troopSpace:number;spellSpace:number;clanCastleSpace:number;
  metadataIncomplete?:boolean;
  units:Array<{id:number;name:string;quantity:number;section:string}>;
  heroes:Array<{id:number;name:string;pet?:string;equipment:string[]}>;
}
interface ArmyReply { items: Army[]; shareCode?: string; armyLink?: string; saved: boolean; presentation?:Presentation; name?:string;notes?:string;
  picker?:{options:Array<{label:string;value:string;description:string;townhall:number}>} }
interface Proof { rawBody: string; timestamp: string; signature: string }
export const armyCommand: Command = {
  definition: { name:"army",description:"Open army links or share from your saved army library",type:1,contexts:[0],integration_types:[0],options:[
    {name:"link",description:"Create a visual message from an army link",type:OptionType.Subcommand,options:[
      {name:"army",description:"Clash CopyArmy link or share code",type:OptionType.String,required:true,max_length:6000},
      {name:"nickname",description:"Name for this army",type:OptionType.String,required:true,min_length:1,max_length:100},
      {name:"notes",description:"Notes about this army",type:OptionType.String,max_length:450},
    ]},
    {name:"share",description:"Choose a saved army to share",type:OptionType.Subcommand},
  ]},
  async execute(){throw new CommandInputError("Army commands require their original signed Discord interaction.");},
};

export async function armyInteraction(interaction:DiscordInteraction,proof:Proof,services:CommandServices,
  waitUntil:(promise:Promise<unknown>)=>void,env:Env):Promise<DiscordInteractionResponse> {
  const errorMessage=(error:unknown)=>{
    if(error instanceof ClashKingApiError){
      if(error.status===401)return "Sign in to the ClashKing app with Discord before saving armies.";
      if(error.status===400||error.status===403){try{const body=JSON.parse(error.body);if(typeof body.message==="string")return body.message;}catch{/* retain safe message */}}
    }
    return "Couldn't load this army. Please try again.";
  };
  if(interaction.type===2&&interaction.data?.options?.[0]?.name==="share"){
    // Discord must receive the modal as the initial response. Deferring first
    // prevents opening it; only the submitted selection posts a public army.
    try{
      const result=await services.api.post<ArmyReply>("/v2/bot/armies/interaction",{interaction:proof});
      if(!result.picker)return {type:InteractionResponseType.ChannelMessageWithSource,data:{content:"Your saved army library is empty. Use /army link, then Save Army.",flags:MessageFlags.Ephemeral}};
      const emoji=await applicationEmojis(services.discordRest),picker=result.picker;
      return {type:InteractionResponseType.Modal,data:{custom_id:`ck:army:share:${interaction.member?.user?.id}`,title:"Share saved army",components:[{
        type:18,label:"Army",component:{type:3,custom_id:"army",required:true,min_values:1,max_values:1,
          options:picker.options.map(({townhall,...option})=>{const icon=emoji.component(townhall);return {...option,...(icon?{emoji:{id:icon.id,name:icon.name,animated:icon.animated??false}}:{})};})},
      }]}};
    }catch(error){return {type:InteractionResponseType.ChannelMessageWithSource,data:{content:errorMessage(error),flags:MessageFlags.Ephemeral,allowed_mentions:{parse:[]}}};}
  }
  waitUntil((async()=>{
    let data:NonNullable<DiscordInteractionResponse["data"]>;
    try {
      const result=await services.api.post<ArmyReply>("/v2/bot/armies/interaction",{interaction:proof});
      if(interaction.data?.custom_id?.startsWith("ck:army:save:")&&result.saved){
        data={content:"Saved to your ClashKing army library.",allowed_mentions:{parse:[]}};
      }else if(result.armyLink&&result.shareCode&&result.presentation){
        const emoji=await applicationEmojis(services.discordRest),army=result.presentation;
        const fields:Array<{name:string;value:string;inline:false}>=[];
        let remaining=5100;
        const add=(name:string,lines:string[])=>{
          if(!lines.length||remaining<100)return;
          let value="";for(const [index,line] of lines.entries()){
            if(value.length+line.length+1>Math.min(950,remaining)){value+=`\n… ${lines.length-index} more entries`;break;}
            value+=(value?"\n":"")+line;
          }
          remaining-=value.length+name.length;fields.push({name,value,inline:false});
        };
        // Reserve notes before long troop lists; Save reads this exact field
        // from the signed bot message, so display truncation must not lose it.
        if(result.notes)add("Notes",[result.notes]);
        for(const section of ["Troops","Super Troops","Spells","Siege Machines"]){
          add(section,army.units.filter(unit=>unit.section===section).map(unit=>`${emoji.get(unit.name)}\`x ${unit.quantity}\` ${unit.name}`));
        }
        add("Heroes Loadout",army.heroes.map(hero=>`${emoji.get(hero.name)} \`${hero.name}\``
          +(hero.pet?`\n- ${emoji.get(hero.pet)} \`${hero.pet}\``:"")
          +hero.equipment.map(name=>`\n- ${emoji.get(name)} \`${name}\``).join("")));
        add("Clan Castle",army.units.filter(unit=>unit.section==="Clan Castle").map(unit=>`${emoji.get(unit.name)}\`x ${unit.quantity}\` ${unit.name}`));
        const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(result.shareCode));
        const hash=[...new Uint8Array(digest)].map(byte=>byte.toString(16).padStart(2,"0")).join("");
        data=legacyMessage({content:result.saved?"Saved to your ClashKing army library.":"",embeds:[{
          title:result.name??"Army Link Results",description:`-# ${emoji.get(army.minimumTownHall)}Town Hall ${army.minimumTownHall}+`,
          color:await serverEmbedColor({interaction,services,env}),fields,footer:{text:`${army.metadataIncomplete?"Partial army • ":""}${army.troopSpace} Troop Space | ${army.spellSpace} Spell Space | ${army.clanCastleSpace} CC Troop${army.metadataIncomplete?"":""}`},
        }],components:[actionRow(linkButton("Copy Army",result.armyLink),{type:2,style:3,label:"Save Army",custom_id:`ck:army:save:${hash}`})],allowed_mentions:{parse:[]}}).data!;
      }else data={content:"Use /army share to choose a saved army.",allowed_mentions:{parse:[]}};
    }catch(error){
      data={content:errorMessage(error),allowed_mentions:{parse:[]}};
    }
    await services.discordRest.editOriginalInteractionResponse(interaction.token,data);
  })());
  const save=interaction.data?.custom_id?.startsWith("ck:army:save:");
  return {type:InteractionResponseType.DeferredChannelMessageWithSource,data:save?{flags:MessageFlags.Ephemeral}:{}};
}
