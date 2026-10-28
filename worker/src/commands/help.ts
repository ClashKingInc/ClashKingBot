import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, OptionType, stringOption } from "./command-utils";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandDefinition, ApplicationCommandOption, Command } from "./types";
function leaves(definitions:ApplicationCommandDefinition[]){
 const rows:Array<{path:string;description:string;options:ApplicationCommandOption[]}>=[];
 for(const root of definitions){
  const visit=(path:string,description:string,options:ApplicationCommandOption[])=>{
   const children=options.filter(option=>option.type===OptionType.Subcommand||option.type===OptionType.SubcommandGroup);
   if(children.length)for(const child of children)visit(`${path} ${child.name}`,child.description,child.options??[]);
   else rows.push({path,description,options});
  };visit(root.name,root.description,root.options??[]);
 }
 return rows;
}
export const helpCommand:Command={
 deferred:true,
 definition:{name:"help",description:"Browse current ClashKing commands and their options",type:1,integration_types:[0,1],contexts:[0,1,2],options:[{name:"command",description:"Command to explain",type:OptionType.String,autocomplete:true}]},
 async autocomplete(ctx){
  const {commandDefinitions}=await import("./registry");
  const query=(stringOption(ctx,"command")??"").toLowerCase().replace(/^\//u,"").trim();
  return leaves(commandDefinitions).filter(row=>row.path.includes(query)).slice(0,25).map(row=>({name:`/${row.path}`.slice(0,100),value:row.path}));
 },
 async execute(ctx){
  // Read registered definitions at execution time. A duplicate help catalogue
  // drifts as commands move or gain flags; a dynamic import avoids the registry cycle.
  const {commandDefinitions}=await import("./registry"),selected=(stringOption(ctx,"command")??"").replace(/^\//u,"").trim().replace(/\s+/gu," ");
  const root=commandDefinitions.find(row=>row.name===selected),leaf=leaves(commandDefinitions).find(row=>row.path===selected);
  if(selected&&!root&&!leaf)throw new CommandInputError("Choose a current command from autocomplete.");
  let title="ClashKing commands",description="";
  if(leaf){
   title=`/${leaf.path}`;description=leaf.description;
   const lines=leaf.options.map(option=>{
    const range=[option.min_value!==undefined?`min ${option.min_value}`:"",option.max_value!==undefined?`max ${option.max_value}`:""].filter(Boolean).join(", ");
    return `**${option.name}** · ${option.required?"Required":"Optional"}\n${option.description}${range?` (${range})`:""}${option.choices?.length?`\nChoices: ${option.choices.map(choice=>choice.name).join(", ")}`:""}`;
   });for(const line of lines){if(description.length+line.length+2>3400){description+="\n\nAdditional options are available in Discord’s command picker.";break;}description+=`\n\n${line}`;}
   if(!lines.length)description+="\n\nNo options required.";
  }else if(root){
   title=`/${root.name}`;description=root.description+"\n\n"+leaves([root]).map(row=>`**/${row.path}**\n${row.description}`).join("\n\n");
  }else description=commandDefinitions.map(row=>`**/${row.name}** · ${row.description}`).join("\n");
  return legacyMessage({allowed_mentions:{parse:[]},embeds:[{title,color:await serverEmbedColor(ctx),description:description.slice(0,3900),footer:{text:"Use /help command:… for options. Server permissions and data access still apply."}}],components:[actionRow({type:2,style:2,label:"Refresh",custom_id:["ck","page","hp",invokingUserId(ctx),selected?selected.replaceAll(" ","~"):"-","0"].join(":")})]});
 }
};
