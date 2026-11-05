import stringWidth from "string-width";

const graphemes=new Intl.Segmenter(undefined,{granularity:"grapheme"});
/** Approximate Discord's monospace columns without cutting an emoji or combining
 * sequence. Font fallback can still vary, so place this column last in a row. */
export function displayNameColumn(value:string,columns:number,maximumCodeUnits=32):string{
 const clean=value.replace(/[\p{Control}\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069`]/gu,"");
 let text="",used=0;
 for(const {segment} of graphemes.segment(clean)){
  const width=stringWidth(segment);
  // Bound raw Discord message length as well as visible columns: a single
  // joined emoji can contain many code units even though it is only two cells.
  if(used+width>columns||text.length+segment.length>maximumCodeUnits)break;
  if(width===0)continue;
  text+=segment;used+=width;
 }
 return text+" ".repeat(Math.max(0,columns-used));
}

/** Keep RTL names inside their own directional span so they cannot reorder
 * adjacent ranks and statistics. Padding remains outside the name span. */
export function isolatedNameColumn(value:string,columns:number,maximumCodeUnits=32):string{
 const padded=displayNameColumn(value,columns,maximumCodeUnits),text=padded.trimEnd();
 return `\u2068${text}\u2069${padded.slice(text.length)}`;
}
