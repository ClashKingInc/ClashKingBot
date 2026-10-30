/** Shared image grammar for Discord charts: readable at phone width, with data first. */
export interface ChartSeries {
  name: string;
  values: Array<number | null>;
}
interface ChartBase {
  title: string;
  subtitle: string;
  logo: string;
  note?: string;
}
export interface BarChartInput extends ChartBase {
  rows: Array<{ name: string; value: number }>;
}
export interface LineChartInput extends ChartBase {
  labels: string[];
  series: ChartSeries[];
}
const colors = [
  "#ef6677",
  "#67cdb2",
  "#7aafff",
  "#d3a0ef",
  "#eac56c",
  "#74d3e3",
  "#eaa27b",
  "#b0ce7c",
  "#d88eaa",
  "#b6b9ce",
];
const ink = "#f4f5f8",
  muted = "#969eaf",
  grid = "#272d38";
const xml = (value: string) =>
  value.replace(
    /[&<>"']/gu,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&apos;",
      })[character]!,
  );
const label = (
  x: number,
  y: number,
  value: string,
  size = 24,
  color = muted,
  anchor = "start",
  weight = 400,
) =>
  `<text x="${x}" y="${y}" text-anchor="${anchor}" fill="${color}" font-family="Blogger Sans" font-size="${size}" font-weight="${weight}">${xml(value)}</text>`;
const short = (value: string, length = 32) =>
  [...value].length > length
    ? [...value].slice(0, length - 1).join("") + "…"
    : value;
export const chartNumber = (value: number) =>
  new Intl.NumberFormat("en", {
    notation: value >= 10000 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value);
function ceiling(value: number) {
  const maximum = Math.max(1, value),
    magnitude = 10 ** Math.floor(Math.log10(maximum));
  return (
    ([1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].find(
      (step) => step * magnitude >= maximum,
    ) ?? 10) * magnitude
  );
}
function frame(input: ChartBase, height: number) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="${height}" viewBox="0 0 1280 ${height}"><title>${xml(input.title)}</title><desc>${xml(input.subtitle)}</desc><rect width="1280" height="${height}" rx="32" fill="#101319"/><rect x="48" y="52" width="5" height="38" rx="2.5" fill="${colors[0]}"/>${label(70, 86, input.title, 48, ink, "start", 600)}${label(70, 126, short(input.subtitle, 72), 26)}<image href="${input.logo}" x="1090" y="49" width="135" height="50" preserveAspectRatio="xMidYMid meet"/>`;
}
function footer(note: string | undefined, height: number) {
  return (note ? label(70, height - 30, note, 20) : "") + "</svg>";
}
export function barChartSvg(input: BarChartInput) {
  const rowHeight = 78,
    height = Math.max(
      350,
      224 + input.rows.length * rowHeight + (input.note ? 30 : 0),
    ),
    x = 430,
    right = 1120;
  const max = Math.max(1, ...input.rows.map((row) => row.value)),
    width = right - x;
  let svg = frame(input, height);
  // Every bar already has an exact value. A second numeric axis adds noise,
  // so keep only the shared zero baseline and let the lengths show comparison.
  svg += `<path d="M${x} 181V${180 + input.rows.length * rowHeight}" stroke="${grid}"/>`;
  input.rows.forEach((row, index) => {
    const y = 181 + index * rowHeight,
      length = (width * row.value) / max;
    svg += label(70, y + 36, short(row.name, 20), 36, ink);
    svg += `<rect x="${x}" y="${y + 5}" width="${Math.max(2, length)}" height="43" rx="8" fill="${index === 0 ? colors[0] : "#465064"}"/>`;
    svg += label(
      x + length + 12,
      y + 36,
      chartNumber(row.value),
      36,
      index === 0 ? ink : "#c6ccda",
    );
  });
  if (!input.rows.length)
    svg += label(640, 258, "No data for this period", 30, muted, "middle");
  return svg + footer(input.note, height);
}
export function chartDate(value: string, monthOnly = false) {
  if (value === "current") return "Current season";
  const date = new Date(
    value.length === 7 ? `${value}-01T12:00:00Z` : `${value}T12:00:00Z`,
  );
  if (!Number.isFinite(+date)) return value;
  return new Intl.DateTimeFormat(
    "en",
    monthOnly
      ? { month: "short", year: "numeric", timeZone: "UTC" }
      : { month: "short", day: "numeric", timeZone: "UTC" },
  ).format(date);
}
interface Point {
  x: number;
  y: number;
}
function curve(points: Point[]) {
  if (!points.length) return "";
  if (points.length === 1) return `M${points[0]!.x},${points[0]!.y}`;
  const slopes = points
    .slice(1)
    .map(
      (point, index) =>
        (point.y - points[index]!.y) / (point.x - points[index]!.x),
    );
  const tangents = points.map((_, index) =>
    index === 0
      ? slopes[0]!
      : index === points.length - 1
        ? slopes.at(-1)!
        : slopes[index - 1]! * slopes[index]! <= 0
          ? 0
          : 2 / (1 / slopes[index - 1]! + 1 / slopes[index]!),
  );
  // Monotone Hermite curves preserve observed extrema rather than overshooting
  // into invented peaks. Call separately per segment so missing data stays a gap.
  let path = `M${points[0]!.x},${points[0]!.y}`;
  for (let index = 0; index < points.length - 1; index++) {
    const from = points[index]!,
      to = points[index + 1]!,
      distance = (to.x - from.x) / 3;
    path += ` C${from.x + distance},${from.y + distance * tangents[index]!} ${to.x - distance},${to.y - distance * tangents[index + 1]!} ${to.x},${to.y}`;
  }
  return path;
}
export function lineChartSvg(input: LineChartInput) {
  const legendRows = Math.ceil(input.series.length / 2),
    height = Math.max(700, 638 + legendRows * 42),
    top = 188,
    bottom = 510,
    left = 116,
    right = 1195;
  const max = ceiling(
    Math.max(
      0,
      ...input.series.flatMap((series) =>
        series.values.filter((value): value is number => value !== null),
      ),
    ),
  );
  const x = (index: number) =>
    input.labels.length <= 1
      ? (left + right) / 2
      : left + ((right - left) * index) / (input.labels.length - 1);
  const y = (value: number) => bottom - (value / max) * (bottom - top);
  let svg = frame(input, height);
  if (input.series.length === 1)
    svg += `<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${colors[0]}" stop-opacity=".24"/><stop offset="100%" stop-color="${colors[0]}" stop-opacity=".015"/></linearGradient></defs>`;
  for (let tick = 0; tick <= 4; tick++) {
    const py = y((max * tick) / 4);
    svg +=
      `<path d="M${left} ${py}H${right}" stroke="${grid}" stroke-dasharray="3 8"/>` +
      label(left - 18, py + 7, chartNumber((max * tick) / 4), 20, muted, "end");
  }
  const stride = Math.max(1, Math.ceil((input.labels.length - 1) / 5));
  input.labels.forEach((value, index) => {
    if (index % stride === 0 || index === input.labels.length - 1)
      svg += label(x(index), bottom + 41, value, 26, muted, "middle");
  });
  input.series.forEach((series, index) => {
    const segments: Point[][] = [];
    let segment: Point[] = [];
    series.values.forEach((value, at) => {
      if (value === null) {
        if (segment.length) segments.push(segment);
        segment = [];
        return;
      }
      segment.push({ x: x(at), y: y(value) });
    });
    if (segment.length) segments.push(segment);
    for (const points of segments) {
      const path = curve(points),
        first = points[0]!,
        last = points.at(-1)!;
      if (input.series.length === 1 && points.length > 1)
        svg += `<path d="${path} L${last.x},${bottom} L${first.x},${bottom} Z" fill="url(#area)"/>`;
      svg += `<path d="${path}" fill="none" stroke="${colors[index % colors.length]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`;
      points.forEach((point, at) => {
        if (input.labels.length <= 12 || at === 0 || at === points.length - 1)
          svg += `<circle cx="${point.x}" cy="${point.y}" r="4.5" fill="${colors[index % colors.length]}" stroke="#101319" stroke-width="2"/>`;
      });
    }
    const lx = 70 + (index % 2) * 590,
      ly = 602 + Math.floor(index / 2) * 42;
    svg +=
      `<circle cx="${lx + 5}" cy="${ly - 8}" r="5" fill="${colors[index % colors.length]}"/>` +
      label(lx + 22, ly, short(series.name, 22), 32, ink) +
      label(
        lx + 525,
        ly,
        series.values.at(-1) === null || series.values.at(-1) === undefined
          ? "—"
          : chartNumber(series.values.at(-1)!),
        36,
        colors[index % colors.length],
        "end",
      );
  });
  if (!input.series.length)
    svg += label(640, 348, "No data for this period", 30, muted, "middle");
  return svg + footer(input.note, height);
}
