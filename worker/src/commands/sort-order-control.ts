import { actionRow } from "../discord/components";

/** Keep a report's other filters in its existing state while changing order. */
export function sortOrderControl(pageId:string,order:string){
 return actionRow({type:3,custom_id:pageId.replace(/:\d+$/u,":sort:0"),placeholder:"Sort order",options:[
  {label:"Highest first",value:"desc",default:order==="desc"},
  {label:"Lowest first",value:"asc",default:order==="asc"},
 ]});
}

export function donationSortControl(pageId:string,metric:string,order:string){
 return actionRow({type:3,custom_id:pageId.replace(/:\d+$/u,":donation-sort:0"),placeholder:"Sort by",options:
  ([['donated','Donations'],['received','Received'],['ratio','Ratio']] as const).flatMap(([key,label])=>
   (['desc','asc'] as const).map(direction=>({label,description:direction==='desc'?'High to low':'Low to high',value:`${key}:${direction}`,default:key===metric&&direction===order}))),
 });
}
