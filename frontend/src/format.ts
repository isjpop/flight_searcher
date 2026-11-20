const num = new Intl.NumberFormat("en-US");
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const day = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
const stamp = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export const fmtPoints = (n: number) => num.format(n);
export const fmtUsd = (n: number) => usd.format(n);
// Travel dates are plain YYYY-MM-DD; format in UTC so they never shift a day.
export const fmtDay = (iso: string) => day.format(new Date(`${iso}T00:00:00Z`));
export const fmtStamp = (iso: string | null) => (iso ? stamp.format(new Date(iso)) : "never");

export function isoDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function addDays(d: Date, days: number): Date {
  const out = new Date(d);
  out.setDate(out.getDate() + days);
  return out;
}
