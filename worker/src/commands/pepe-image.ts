import sign from "../assets/pepe/sign.png";
import font from "../assets/pepe/font.ttf";
import { renderPosterSvg } from "./legend-poster";
import { pepeAdvances, pepeFontFamily, pepeUnitsPerEm } from "./pepe-font-metrics";
const xml=(value:string)=>value.replace(/[&<>"']/gu,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"})[c]!);
let binary="";for(const byte of new Uint8Array(sign))binary+=String.fromCharCode(byte);
const artwork=`data:image/png;base64,${btoa(binary)}`;
const width=(value:string,size:number)=>[...value].reduce((sum,c)=>sum+(pepeAdvances[c.codePointAt(0)!-32]??pepeUnitsPerEm),0)*size/pepeUnitsPerEm;
function linesAt(value:string,size:number){
 const lines:string[]=[];let line="";
 for(const word of value.split(/\s+/u)){
  const next=line?line+" "+word:word;
  if(width(next,size)<=205){line=next;continue;}
  if(line){lines.push(line);line="";}
  for(const char of word){if(line&&width(line+char,size)>205){lines.push(line);line="";}line+=char;}
 }
 if(line)lines.push(line);return lines;
}
export async function renderPepe(value:string){
  let size=36,lines=linesAt(value,size);
  // Fit both words and unbroken strings inside the original sign, rather than
  // clipping long text or shrinking based only on character count.
  while(size>10&&lines.length*size*1.15>80){size--;lines=linesAt(value,size);}
  const top=55-(lines.length-1)*size*1.15/2;
  const text=lines.map((line,i)=>`<text x="120" y="${top+i*size*1.15}" text-anchor="middle" dominant-baseline="central" font-family="${xml(pepeFontFamily)}" font-size="${size}" fill="black">${xml(line)}</text>`).join("");
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="250" height="250"><defs><clipPath id="sign"><rect x="15" y="10" width="215" height="90"/></clipPath></defs><image href="${artwork}" width="250" height="250"/><g clip-path="url(#sign)">${text}</g></svg>`;
  return renderPosterSvg(svg,[font]);
}
