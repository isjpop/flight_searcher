import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { CrawlerPanel } from "./components/CrawlerPanel";
import { DealsTable } from "./components/DealsTable";
import { Destinations } from "./components/Destinations";
import { SearchForm } from "./components/SearchForm";
import { addDays, fmtStamp, isoDate } from "./format";
import type { Airline, DealParams, DealsResponse } from "./types";

type Tab = "deals" | "destinations" | "crawler";

const today = new Date();
const DEFAULT_PARAMS: DealParams = {
  depart_from: isoDate(addDays(today, 14)),
  return_by: isoDate(addDays(today, 180)),
  min_nights: 4,
  max_nights: 10,
  max_ratio: 0.7,
  airlines: [],
  regions: [],
  mix_programs: false,
  max_taxes_usd: null,
  per_destination: 3,
};

export default function App() {
  const [tab, setTab] = useState<Tab>("deals");
  const [airlines, setAirlines] = useState<Airline[]>([]);
  const [deals, setDeals] = useState<DealsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.airlines().then(setAirlines).catch((e) => setError(e.message));
  }, []);

  const byCode = useMemo(() => Object.fromEntries(airlines.map((a) => [a.code, a])), [airlines]);
  const anyMock = airlines.some((a) => a.mode === "mock");

  async function search(p: DealParams) {
    setLoading(true);
    setError(null);
    try {
      setDeals(await api.deals(p));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>AUS Award Finder</h1>
          <p className="muted">Round trips from Austin priced well below their normal points cost.</p>
        </div>
        <nav className="tabs" role="tablist">
          {(["deals", "destinations", "crawler"] as Tab[]).map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
              {t === "deals" ? "Deals" : t === "destinations" ? "Destinations" : "Crawler"}
            </button>
          ))}
        </nav>
      </header>

      {anyMock && (
        <div className="banner">
          Some programs are using <strong>mock data</strong> until their live scrapers are written. Prices shown for
          them are not real.
        </div>
      )}

      <main>
        {tab === "deals" && (
          <div className="stack">
            <SearchForm airlines={airlines} initial={DEFAULT_PARAMS} loading={loading} onSearch={search} />
            {error && <div className="error">{error}</div>}
            {deals && (
              <>
                <div className="result-meta muted">
                  {deals.total_matches === 0
                    ? "No round trips match."
                    : `Showing ${deals.results.length} of ${deals.total_matches.toLocaleString()} matching round trips, best value first.`}{" "}
                  Data as of {fmtStamp(deals.data_as_of)}.
                </div>
                {deals.notes.map((n) => (
                  <div key={n} className="banner">{n}</div>
                ))}
                {deals.results.length > 0 && <DealsTable trips={deals.results} airlines={byCode} />}
              </>
            )}
          </div>
        )}
        {tab === "destinations" && <Destinations />}
        {tab === "crawler" && <CrawlerPanel airlines={airlines} />}
      </main>
    </div>
  );
}
