export type Region =
  | "domestic"
  | "canada"
  | "mexico_caribbean"
  | "central_america"
  | "south_america"
  | "europe"
  | "asia"
  | "oceania"
  | "middle_east_africa";

export const REGIONS: { value: Region; label: string }[] = [
  { value: "domestic", label: "US" },
  { value: "canada", label: "Canada" },
  { value: "mexico_caribbean", label: "Mexico & Caribbean" },
  { value: "central_america", label: "Central America" },
  { value: "south_america", label: "South America" },
  { value: "europe", label: "Europe" },
  { value: "asia", label: "Asia" },
  { value: "oceania", label: "Oceania" },
  { value: "middle_east_africa", label: "Middle East & Africa" },
];

export interface Airline {
  code: string;
  name: string;
  program: string;
  currency: string;
  mode: "mock" | "live";
}

export interface Destination {
  code: string;
  city: string;
  country: string;
  region: Region;
  enabled: boolean;
}

export interface Leg {
  airline: string;
  origin: string;
  destination: string;
  date: string;
  points: number;
  normal_points: number;
  ratio: number;
  taxes_usd: number;
  cabin: string;
  fare_brand: string | null;
  seats: number | null;
  stops: number;
  flights: string[];
  fetched_at: string;
}

export interface RoundTrip {
  destination: Destination;
  outbound: Leg;
  inbound: Leg;
  nights: number;
  ratio: number;
  savings_pct: number;
  points_by_program: Record<string, number>;
  normal_points_by_program: Record<string, number>;
  taxes_usd: number;
  mixed_programs: boolean;
}

export interface DealsResponse {
  results: RoundTrip[];
  total_matches: number;
  data_as_of: string | null;
  notes: string[];
}

export interface DealParams {
  depart_from: string;
  return_by: string;
  min_nights: number;
  max_nights: number;
  max_ratio: number;
  airlines: string[];
  regions: Region[];
  mix_programs: boolean;
  max_taxes_usd: number | null;
  per_destination: number;
}

export interface CrawlRun {
  airline: string;
  mode: string;
  status: "running" | "ok" | "partial" | "failed" | "interrupted";
  started_at: string;
  finished_at: string | null;
  jobs_total: number;
  jobs_done: number;
  jobs_failed: number;
  fares_saved: number;
  error: string | null;
}

export interface CrawlStatus {
  running: boolean;
  interval_hours: number;
  last_finished_at: string | null;
  next_due_at: string | null;
  runs: CrawlRun[];
}
