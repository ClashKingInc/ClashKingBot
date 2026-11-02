import sign from "../assets/pepe/sign.png";

import { renderPosterSvg } from "./legend-poster";
import { memeFontWidths, memeFontUnits } from "./meme-font-metrics";
const pepeFontFamily="Supercell-Magic";
const xml=(value:string)=>value.replace(/[&<>"']/gu,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"})[c]!);
let binary="";for(const byte of new Uint8Array(sign))binary+=String.fromCharCode(byte);
const artwork=`data:image/png;base64,${btoa(binary)}`;
// The white sign occupies x=36..204, y=20..86 in the artwork. Keep text
// inside its inner padding; the image's full width includes Pepe's hands.
const textWidth=152,textHeight=54;
const width=(value:string,size:number)=>[...value].reduce((sum,c)=>sum+(memeFontWidths[c]??memeFontUnits),0)*size/memeFontUnits;
function linesAt(value:string,size:number){
 const lines:string[]=[];let line="";
 for(const word of value.split(/\s+/u)){
  const next=line?line+" "+word:word;
  if(width(next,size)<=textWidth){line=next;continue;}
  if(line){lines.push(line);line="";}
  for(const char of word){if(line&&width(line+char,size)>textWidth){lines.push(line);line="";}line+=char;}
 }
 if(line)lines.push(line);return lines;
}
export async function renderPepe(value:string){
  let size=30,lines=linesAt(value,size);
  // Fit both words and unbroken strings inside the original sign, rather than
  // clipping long text or shrinking based only on character count.
  while(size>8&&lines.length*size*1.15>textHeight){size--;lines=linesAt(value,size);}
  const top=53-(lines.length-1)*size*1.15/2;
  const text=lines.map((line,i)=>`<text x="120" y="${top+i*size*1.15}" text-anchor="middle" dominant-baseline="central" font-family="${xml(pepeFontFamily)}" font-size="${size}" fill="black">${xml(line)}</text>`).join("");
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="750" height="750" viewBox="0 0 250 250"><defs><clipPath id="sign"><rect x="43" y="25" width="154" height="56"/></clipPath></defs><image href="${artwork}" width="250" height="250"/><g clip-path="url(#sign)">${text}</g></svg>`;
  return renderPosterSvg(svg);
}
