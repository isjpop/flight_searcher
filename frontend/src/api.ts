import type { Airline, CrawlStatus, DealParams, DealsResponse, Destination } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body.detail) message = Array.isArray(body.detail) ? body.detail.map(String).join("; ") : String(body.detail);
    } catch {
      /* keep the status text */
    }
    throw new Error(message);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

function dealQuery(p: DealParams): string {
  const q = new URLSearchParams({
    depart_from: p.depart_from,
    return_by: p.return_by,
    min_nights: String(p.min_nights),
    max_nights: String(p.max_nights),
    max_ratio: String(p.max_ratio),
    mix_programs: String(p.mix_programs),
    per_destination: String(p.per_destination),
  });
  if (p.airlines.length) q.set("airlines", p.airlines.join(","));
  if (p.regions.length) q.set("regions", p.regions.join(","));
  if (p.max_taxes_usd !== null) q.set("max_taxes_usd", String(p.max_taxes_usd));
  return q.toString();
}

export const api = {
  airlines: () => request<Airline[]>("/airlines"),
  destinations: () => request<Destination[]>("/destinations"),
  addDestination: (d: Destination) =>
    request<Destination>("/destinations", { method: "POST", body: JSON.stringify(d) }),
  setDestinationEnabled: (code: string, enabled: boolean) =>
    request<Destination>(`/destinations/${code}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  deleteDestination: (code: string) => request<void>(`/destinations/${code}`, { method: "DELETE" }),
  crawlStatus: () => request<CrawlStatus>("/crawl"),
  startCrawl: (airlines?: string[]) =>
    request<{ started: boolean }>("/crawl", { method: "POST", body: JSON.stringify({ airlines: airlines ?? null }) }),
  deals: (p: DealParams) => request<DealsResponse>(`/deals?${dealQuery(p)}`),
};
