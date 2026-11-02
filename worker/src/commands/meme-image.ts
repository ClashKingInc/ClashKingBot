import buttons from "../assets/memes/buttons.jpg";
import kingphoto from "../assets/memes/king-photo.jpg";
import skeptical from "../assets/memes/skeptical-bowler.jpg";
import always from "../assets/memes/always.jpg";
import trade from "../assets/memes/trade.jpg";
import awkward from "../assets/memes/awkward.jpg";
import grab from "../assets/memes/grab.jpg";
import presentation from "../assets/memes/presentation.jpg";
import terminator from "../assets/memes/terminator.jpg";
import window from "../assets/memes/window.jpg";
import archer from "../assets/memes/archer.jpg";
import goblin from "../assets/memes/goblin.jpg";
import calm from "../assets/memes/reaction-one.jpg";
import distressed from "../assets/memes/reaction-two.jpg";
import comparison from "../assets/memes/comparison.jpg";
import distracted from "../assets/memes/distracted.png";
import forbetter from "../assets/memes/forbetter.png";
import dragons from "../assets/memes/dragons.png";
import grandma from "../assets/memes/grandma-blank.jpg";
import {renderPosterSvg} from "./legend-poster";
import {memeFontUnits,memeFontWidths} from "./meme-font-metrics";
import type {MemeTemplate} from "./meme-templates";
const xml=(v:string)=>v.replace(/[&<>"']/gu,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"})[c]!);
function uri(buffer:ArrayBuffer,mime="image/png"){let result="";const data=new Uint8Array(buffer);for(let i=0;i<data.length;i+=8192)result+=String.fromCharCode(...data.subarray(i,i+8192));return `data:${mime};base64,${btoa(result)}`;}
const images={kingphoto:uri(kingphoto,"image/jpeg"),archer:uri(archer,"image/jpeg"),goblin:uri(goblin,"image/jpeg"),calm:uri(calm,"image/jpeg"),distressed:uri(distressed,"image/jpeg"),comparison:uri(comparison,"image/jpeg"),grandma:uri(grandma,"image/jpeg"),distracted:uri(distracted),forbetter:uri(forbetter),dragons:uri(dragons),trade:uri(trade,"image/jpeg"),awkward:uri(awkward,"image/jpeg"),grab:uri(grab,"image/jpeg"),presentation:uri(presentation,"image/jpeg"),terminator:uri(terminator,"image/jpeg"),window:uri(window,"image/jpeg")};
function measure(v:string,size:number){return [...v].reduce((sum,c)=>sum+(memeFontWidths[c]??memeFontUnits),0)*size/memeFontUnits;}
function wrap(value:string,size:number,width:number){
 const lines:string[]=[];let current="";
 for(const word of value.split(/\s+/u)){
  const next=current?`${current} ${word}`:word;
  if(measure(next,size)<=width){current=next;continue;}
  if(current){lines.push(current);current="";}
  for(const char of word){if(current&&measure(current+char,size)>width){lines.push(current);current="";}current+=char;}
 }
 if(current)lines.push(current);return lines;
}
function caption(value:string,x:number,y:number,w:number,h:number,outlined=false,max=48){
 let size=max,lines=wrap(value,size,w-20);
 while(size>10&&(lines.length*size*1.25>h-16||value.split(/\s+/u).some(word=>measure(word,size)>w-20))){size--;lines=wrap(value,size,w-20);}
 const lineHeight=size*1.25,top=y+h/2-(lines.length-1)*lineHeight/2;
 // Every template owns its text rectangle. Clipping is a last guard; fitting
 // uses real Clash glyph advances first, including long unbroken captions.
 return `<svg x="${x}" y="${y}" width="${w}" height="${h}" viewBox="${x} ${y} ${w} ${h}">${lines.map((line,i)=>`<text x="${x+w/2}" y="${top+i*lineHeight}" text-anchor="middle" dominant-baseline="central" font-family="Supercell-Magic" font-size="${size}" fill="${outlined?'white':'#111'}" ${outlined?'stroke="black" stroke-width="6" stroke-linejoin="round" paint-order="stroke fill"':''}>${xml(line)}</text>`).join('')}</svg>`;
}
export async function renderMeme(template:MemeTemplate,texts:readonly string[]){
 const c=(i:number,x:number,y:number,w:number,h:number,outlined=false,max=48)=>caption(texts[i]??"",x,y,w,h,outlined,max);
 let width=1280,height=722,body="";
 const img=(url:string,x:number,y:number,w:number,h:number)=>`<image href="${url}" x="${x}" y="${y}" width="${w}" height="${h}"/>`;
 switch(template){
  case 'pepe': {
   const {renderPepe}=await import('./pepe-image');return renderPepe(texts[0]??"");
  }
  case 'archer': body=img(images.archer,0,0,width,height)+c(0,664,18,595,318)+c(1,664,386,595,318);break;
  case 'goblin': width=1200;height=675;body=img(images.goblin,0,0,width,height)+c(0,327,83,233,232,false,34)+c(1,932,83,233,232,false,34)+c(2,327,425,233,229,false,34)+c(3,932,425,233,229,false,34);break;
  case 'giant': height=800;body='<rect width="1280" height="800" fill="white"/>'+img(images.calm,0,160,638,640)+img(images.distressed,642,160,638,640)+c(0,12,8,614,144)+c(1,654,8,614,144);break;
  case 'comparison': width=1024;height=1152;body=img(images.comparison,0,0,width,height)+c(0,49,165,350,424)+c(1,622,165,350,424)+caption('Find the differences.',25,619,974,40,true,26)+caption('They’re the same picture.',25,1090,974,48,true,32);break;
  case 'distracted': body=img(images.distracted,0,0,width,height)+c(0,45,490,370,185,true,40)+c(1,623,490,337,180,true,40)+c(2,986,552,277,145,true,37);break;
  case 'forbetter': width=1024;height=1024;body=img(images.forbetter,0,0,width,height)+c(0,20,425,472,78,true,32)+c(1,532,425,472,78,true,32)+c(2,532,937,472,78,true,32);break;
  case 'dragons': body=img(images.dragons,0,0,width,height)+c(0,24,559,366,146,true,37)+c(1,450,559,366,146,true,37)+c(2,878,559,378,146,true,37);break;
  case 'trade': width=768;height=1024;body=img(images.trade,0,0,width,height)+caption('TRADE OFFER',148,36,472,75,true,43)+caption('I receive:',20,145,336,58,true,26)+caption('You receive:',412,145,336,58,true,26)+c(0,20,215,336,163,true,35)+c(1,412,215,336,163,true,35);break;
  case 'awkward': width=1280;height=790;body='<rect width="1280" height="790" fill="white"/>'+img(images.awkward,0,150,1280,640)+c(0,25,10,1230,130,false,48);break;
  case 'grab': width=1024;height=1280;body=img(images.grab,0,0,width,height)+c(0,35,491,310,128,true,34)+c(1,674,131,319,235,false,36)+c(0,337,1120,304,125,true,34)+c(1,712,784,282,234,false,34)+c(2,20,1017,250,198,true,33);break;
  case 'presentation': width=1280;height=960;body=img(images.presentation,0,0,width,height)+c(0,260,134,770,352,false,68);break;
  case 'terminator': width=1024;height=1280;body=img(images.terminator,0,0,width,height)+c(0,20,780,354,219,true,37)+c(1,578,989,415,207,true,37);break;
  case 'window': width=1280;height=960;body=img(images.window,0,0,width,height)+c(0,30,658,477,260,true,42)+c(1,743,651,502,186,true,42);break;
  case 'kingphoto': width=1024;height=1536;body=img(images.kingphoto,0,0,width,height)+c(0,335,918,360,205,false,48);break;
  case 'skeptical': width=1280;height=1280;body=img(uri(skeptical,"image/jpeg"),0,0,width,height)+c(0,25,15,620,160,true,48)+c(1,25,1110,1230,155,true,48);break;
  case 'always': width=1280;height=720;body=img(uri(always,"image/jpeg"),0,0,width,height)+c(0,445,12,290,140,true,32)+c(1,735,12,230,140,true,32);break;
  case 'buttons': width=1024;height=1536;body=img(uri(buttons,"image/jpeg"),0,0,width,height)+`<g transform="rotate(-10 235 220)">${c(0,85,163,300,114,false,40)}</g><g transform="rotate(-10 581 168)">${c(1,454,113,254,110,false,38)}</g>`;break;
  case 'grandma': width=1024;height=1024;body=img(images.grandma,0,0,width,height)+c(0,240,596,355,120,true,39)+c(1,636,563,360,234,true,39);break;
 }
 return renderPosterSvg(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">${body}</svg>`);
}
