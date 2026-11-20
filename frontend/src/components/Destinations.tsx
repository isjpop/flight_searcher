import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { REGIONS, type Destination, type Region } from "../types";

const EMPTY: Destination = { code: "", city: "", country: "", region: "domestic", enabled: true };
const regionLabel = (r: Region) => REGIONS.find((x) => x.value === r)?.label ?? r;

export function Destinations() {
  const [list, setList] = useState<Destination[]>([]);
  const [draft, setDraft] = useState<Destination>(EMPTY);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.destinations().then(setList).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const grouped = useMemo(
    () => REGIONS.map((r) => ({ ...r, items: list.filter((d) => d.region === r.value) })).filter((g) => g.items.length),
    [list],
  );
  const enabledCount = list.filter((d) => d.enabled).length;

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="stack">
      <p className="muted">
        {enabledCount} of {list.length} destinations are searched. Each one adds requests to every crawl, so with
        live scrapers keep this list to places you'd actually go.
      </p>

      <form
        className="panel add-dest"
        onSubmit={(e) => {
          e.preventDefault();
          run(() => api.addDestination({ ...draft, code: draft.code.toUpperCase() })).then(() => setDraft(EMPTY));
        }}
      >
        <input placeholder="Code (e.g. LHR)" maxLength={3} value={draft.code} required
          onChange={(e) => setDraft({ ...draft, code: e.target.value })} aria-label="Airport code" />
        <input placeholder="City" value={draft.city} required
          onChange={(e) => setDraft({ ...draft, city: e.target.value })} aria-label="City" />
        <input placeholder="Country" value={draft.country} required
          onChange={(e) => setDraft({ ...draft, country: e.target.value })} aria-label="Country" />
        <select value={draft.region} onChange={(e) => setDraft({ ...draft, region: e.target.value as Region })}
          aria-label="Region">
          {REGIONS.map((r) => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>
        <button type="submit" className="primary">Add</button>
      </form>

      {error && <div className="error">{error}</div>}

      {grouped.map((g) => (
        <section key={g.value} className="panel">
          <h3>{regionLabel(g.value)}</h3>
          <ul className="dest-list">
            {g.items.map((d) => (
              <li key={d.code} className={d.enabled ? "" : "disabled"}>
                <label className="check">
                  <input type="checkbox" checked={d.enabled}
                    onChange={(e) => run(() => api.setDestinationEnabled(d.code, e.target.checked))} />
                  <span className="code">{d.code}</span> {d.city}, {d.country}
                </label>
                <button className="link danger" onClick={() => run(() => api.deleteDestination(d.code))}
                  aria-label={`Remove ${d.code}`}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
