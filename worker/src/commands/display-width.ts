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

/** One compact budget for Discord's narrow mobile embed column. Icons live
 * outside code spans but still consume room; callers reserve their columns. */
export const COMPACT_TABLE = { columns: 37, iconColumns: 2 } as const;
type TableColumn = string | { value: string; width: number; maximumCodeUnits?: number; isolate?: boolean };

/** Shrink labels, never numeric values or player tags. Keep internal alignment,
 * but omit final padding: Discord can wrap invisible spaces onto another line.
 * Width is approximate because Discord does not expose the viewer's font/size. */
export function compactTableRow(columns: readonly TableColumn[], reservedColumns = 0): string {
 const widths = columns.map(column => typeof column === "string" ? stringWidth(column) : column.width);
 let excess = widths.reduce((sum, width) => sum + width, Math.max(0, columns.length - 1))
   - Math.max(1, COMPACT_TABLE.columns - reservedColumns);
 while (excess > 0) {
  let widest = -1;
  for (let i = 0; i < columns.length; i++) {
   if (typeof columns[i] !== "string" && widths[i]! > 1 && (widest < 0 || widths[i]! > widths[widest]!)) widest = i;
  }
  if (widest < 0) break;
  widths[widest]!--; excess--;
 }
 return columns.map((column, index) => typeof column === "string" ? column
   : (column.isolate ? isolatedNameColumn : displayNameColumn)(column.value, widths[index]!, column.maximumCodeUnits ?? 32))
   .join(" ").trimEnd();
}
