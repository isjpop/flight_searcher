import { useEffect, useState } from "react";
import { api } from "../api";
import { fmtPoints, fmtStamp } from "../format";
import type { Airline, CrawlStatus } from "../types";

export function CrawlerPanel({ airlines }: { airlines: Airline[] }) {
  const [status, setStatus] = useState<CrawlStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.crawlStatus().then(setStatus).catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  // Poll while a crawl is running.
  useEffect(() => {
    if (!status?.running) return;
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [status?.running]);

  async function start(codes?: string[]) {
    setError(null);
    try {
      await api.startCrawl(codes);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const runs = Object.fromEntries((status?.runs ?? []).map((r) => [r.airline, r]));

  return (
    <div className="stack">
      <div className="panel crawl-summary">
        <div>
          <div><strong>{status?.running ? "Crawling now…" : "Idle"}</strong></div>
          <div className="muted small">
            Last finished {fmtStamp(status?.last_finished_at ?? null)}
            {status?.next_due_at && <> · next scheduled {fmtStamp(status.next_due_at)}</>}
            {status && <> · runs every {status.interval_hours}h</>}
          </div>
        </div>
        <button className="primary" disabled={status?.running} onClick={() => start()}>
          Crawl all now
        </button>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="cards">
        {airlines.map((a) => {
          const r = runs[a.code];
          const pct = r && r.jobs_total ? Math.round(((r.jobs_done + r.jobs_failed) / r.jobs_total) * 100) : 0;
          return (
            <section key={a.code} className="panel card">
              <header>
                <div>
                  <h3>{a.name}</h3>
                  <div className="muted small">{a.program}</div>
                </div>
                <span className={`pill ${a.mode}`}>{a.mode === "mock" ? "mock data" : "live"}</span>
              </header>
              {r ? (
                <>
                  <div className={`status ${r.status}`}>{r.status}</div>
                  {r.status === "running" && (
                    <div className="bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                      <span style={{ width: `${pct}%` }} />
                    </div>
                  )}
                  <div className="muted small">
                    {r.jobs_done}/{r.jobs_total} pages · {r.jobs_failed} failed · {fmtPoints(r.fares_saved)} fares
                  </div>
                  <div className="muted small">Started {fmtStamp(r.started_at)}</div>
                  {r.error && <div className="error small">{r.error}</div>}
                </>
              ) : (
                <div className="muted">Never crawled</div>
              )}
              <button className="link" disabled={status?.running} onClick={() => start([a.code])}>
                Crawl just {a.name}
              </button>
            </section>
          );
        })}
      </div>
    </div>
  );
}
