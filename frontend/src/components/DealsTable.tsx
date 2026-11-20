import { Fragment, useState } from "react";
import { fmtDay, fmtPoints, fmtStamp, fmtUsd } from "../format";
import type { Airline, Leg, RoundTrip } from "../types";

interface Props {
  trips: RoundTrip[];
  airlines: Record<string, Airline>;
}

function LegDetail({ label, leg, airline }: { label: string; leg: Leg; airline?: Airline }) {
  return (
    <div className="leg">
      <h4>
        {label}: {leg.origin} → {leg.destination}
      </h4>
      <dl>
        <dt>Date</dt>
        <dd>{fmtDay(leg.date)}</dd>
        <dt>Program</dt>
        <dd>{airline ? `${airline.name} ${airline.program}` : leg.airline}</dd>
        <dt>Price</dt>
        <dd>
          {fmtPoints(leg.points)} {airline?.currency}{" "}
          <span className="muted">(normally {fmtPoints(leg.normal_points)})</span>
        </dd>
        <dt>Taxes &amp; fees</dt>
        <dd>{fmtUsd(leg.taxes_usd)}</dd>
        <dt>Fare</dt>
        <dd>{leg.fare_brand ?? leg.cabin}</dd>
        <dt>Flights</dt>
        <dd>
          {leg.flights.join(" · ") || "—"} ({leg.stops === 0 ? "nonstop" : `${leg.stops} stop${leg.stops > 1 ? "s" : ""}`})
        </dd>
        <dt>Seats</dt>
        <dd>{leg.seats ?? "not shown"}</dd>
        <dt>Checked</dt>
        <dd>{fmtStamp(leg.fetched_at)}</dd>
      </dl>
    </div>
  );
}

function programPoints(t: RoundTrip, airlines: Record<string, Airline>) {
  const currencyOf = (program: string) => Object.values(airlines).find((a) => a.program === program)?.currency ?? "";
  return Object.entries(t.points_by_program).map(([program, pts]) => (
    <div key={program}>
      <strong>{fmtPoints(pts)}</strong> <span className="muted">{currencyOf(program)}</span>
    </div>
  ));
}

export function DealsTable({ trips, airlines }: Props) {
  const [open, setOpen] = useState<string | null>(null);

  return (
    <div className="table-wrap">
      <table className="deals">
        <thead>
          <tr>
            <th>Destination</th>
            <th>Program</th>
            <th>Dates</th>
            <th className="num">Points</th>
            <th className="num">Normally</th>
            <th className="num">Savings</th>
            <th className="num">Taxes</th>
          </tr>
        </thead>
        <tbody>
          {trips.map((t) => {
            const id = `${t.destination.code}|${t.outbound.airline}|${t.outbound.date}|${t.inbound.airline}|${t.inbound.date}`;
            const isOpen = open === id;
            const programs = t.mixed_programs
              ? `${airlines[t.outbound.airline]?.name} / ${airlines[t.inbound.airline]?.name}`
              : airlines[t.outbound.airline]?.name;
            return (
              <Fragment key={id}>
                <tr className={`row ${isOpen ? "open" : ""}`} onClick={() => setOpen(isOpen ? null : id)}
                  tabIndex={0} aria-expanded={isOpen}
                  onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), setOpen(isOpen ? null : id))}>
                  <td>
                    <div className="dest">{t.destination.city}</div>
                    <div className="muted small">
                      {t.destination.code} · {t.destination.country}
                    </div>
                  </td>
                  <td>{programs}</td>
                  <td>
                    <div>{fmtDay(t.outbound.date)}</div>
                    <div className="muted small">
                      back {fmtDay(t.inbound.date)} · {t.nights} nights
                    </div>
                  </td>
                  <td className="num">{programPoints(t, airlines)}</td>
                  <td className="num muted">
                    {Object.values(t.normal_points_by_program).map((n, i) => (
                      <div key={i}>{fmtPoints(n)}</div>
                    ))}
                  </td>
                  <td className="num">
                    <span className="badge">−{Math.round(t.savings_pct)}%</span>
                  </td>
                  <td className="num">{fmtUsd(t.taxes_usd)}</td>
                </tr>
                {isOpen && (
                  <tr className="detail">
                    <td colSpan={7}>
                      <div className="legs">
                        <LegDetail label="Outbound" leg={t.outbound} airline={airlines[t.outbound.airline]} />
                        <LegDetail label="Return" leg={t.inbound} airline={airlines[t.inbound.airline]} />
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
