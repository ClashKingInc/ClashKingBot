import { legacyMessage } from "../discord/components";
import { CommandInputError, stringOption, OptionType } from "./command-utils";
import type { Command } from "./types";
export const pepeCommand:Command={
 deferred:true,
 // Visibility is chosen at acknowledgement, before rendering. Do not publish
 // a private sign and try to hide it afterward with an edit flag.
 ephemeral:ctx=>stringOption(ctx,"hidden")!=="No",
 definition:{name:"pepe",description:"Create the classic Pepe sign with your text",type:1,integration_types:[0,1],contexts:[0,1,2],options:[
  {name:"sign_text",description:"Text on the sign (up to 40 characters)",type:OptionType.String,required:true,min_length:1,max_length:40},
  {name:"hidden",description:"Only show the image to you (default Yes)",type:OptionType.String,choices:[{name:"Yes",value:"Yes"},{name:"No",value:"No"}]},
 ]},
 async execute(ctx){
  const raw=stringOption(ctx,"sign_text")??"",value=raw.trim().replace(/[\p{Control}\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu," ").replace(/\s+/gu," ").trim(),hidden=stringOption(ctx,"hidden")??"Yes";
  if(!value||raw.length>40||!["Yes","No"].includes(hidden))throw new CommandInputError("Use 1–40 characters and choose Yes or No for hidden.");
  const {renderPepe}=await import("./pepe-image");
  const response=legacyMessage({allowed_mentions:{parse:[]}},{ephemeral:hidden==="Yes"});
  response.data!.attachments=[];
  response.data!.__files=[{name:"pepe.png",bytes:await renderPepe(value)}];return response;
 },
};
