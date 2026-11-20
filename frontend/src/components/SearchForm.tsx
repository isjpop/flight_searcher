import { useState } from "react";
import { REGIONS, type Airline, type DealParams, type Region } from "../types";

interface Props {
  airlines: Airline[];
  initial: DealParams;
  loading: boolean;
  onSearch: (p: DealParams) => void;
}

function toggle<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
}

export function SearchForm({ airlines, initial, loading, onSearch }: Props) {
  const [p, setP] = useState<DealParams>(initial);
  const set = <K extends keyof DealParams>(key: K, value: DealParams[K]) => setP((prev) => ({ ...prev, [key]: value }));
  const pctBelow = Math.round((1 - p.max_ratio) * 100);

  return (
    <form
      className="panel search"
      onSubmit={(e) => {
        e.preventDefault();
        onSearch(p);
      }}
    >
      <div className="grid">
        <label>
          Earliest departure
          <input type="date" value={p.depart_from} onChange={(e) => set("depart_from", e.target.value)} required />
        </label>
        <label>
          Latest return
          <input type="date" value={p.return_by} onChange={(e) => set("return_by", e.target.value)} required />
        </label>
        <label>
          Trip length (nights)
          <span className="range-pair">
            <input type="number" min={1} max={60} value={p.min_nights}
              onChange={(e) => set("min_nights", Number(e.target.value))} aria-label="Minimum nights" />
            <span>to</span>
            <input type="number" min={1} max={60} value={p.max_nights}
              onChange={(e) => set("max_nights", Number(e.target.value))} aria-label="Maximum nights" />
          </span>
        </label>
        <label>
          At least <strong>{pctBelow}%</strong> below normal
          <input type="range" min={0.3} max={0.95} step={0.05} value={p.max_ratio}
            onChange={(e) => set("max_ratio", Number(e.target.value))} />
        </label>
        <label>
          Max taxes &amp; fees (USD)
          <input type="number" min={0} placeholder="Any" value={p.max_taxes_usd ?? ""}
            onChange={(e) => set("max_taxes_usd", e.target.value === "" ? null : Number(e.target.value))} />
        </label>
        <label>
          Results per destination
          <input type="number" min={1} max={50} value={p.per_destination}
            onChange={(e) => set("per_destination", Number(e.target.value))} />
        </label>
      </div>

      <fieldset>
        <legend>Programs <span className="hint">(none selected = all)</span></legend>
        <div className="chips">
          {airlines.map((a) => (
            <button type="button" key={a.code} className={`chip ${p.airlines.includes(a.code) ? "on" : ""}`}
              aria-pressed={p.airlines.includes(a.code)} onClick={() => set("airlines", toggle(p.airlines, a.code))}>
              {a.name}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend>Regions <span className="hint">(none selected = all)</span></legend>
        <div className="chips">
          {REGIONS.map((r) => (
            <button type="button" key={r.value} className={`chip ${p.regions.includes(r.value) ? "on" : ""}`}
              aria-pressed={p.regions.includes(r.value)}
              onClick={() => set("regions", toggle<Region>(p.regions, r.value))}>
              {r.label}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="actions">
        <label className="check">
          <input type="checkbox" checked={p.mix_programs} onChange={(e) => set("mix_programs", e.target.checked)} />
          Allow a different program each way
        </label>
        <button type="submit" className="primary" disabled={loading}>
          {loading ? "Searching…" : "Find deals"}
        </button>
      </div>
    </form>
  );
}
