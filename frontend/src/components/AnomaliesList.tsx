import type { Anomaly } from "../types";

export function AnomaliesList({ anomalies }: { anomalies: Anomaly[] }) {
  const active = anomalies.filter((a) => a.resolved_at === null);

  if (active.length === 0) {
    return <p className="empty">No active anomalies.</p>;
  }

  return (
    <ul className="anomalies-list">
      {active.map((a) => (
        <li key={`${a.service}-${a.metric}`}>
          <strong>{a.service}</strong> — {a.metric}: {a.value.toFixed(2)} (baseline {a.baseline_mean.toFixed(2)}, z=
          {a.z_score.toFixed(1)})
          <span className="since"> since {new Date(a.started_at).toLocaleTimeString()}</span>
        </li>
      ))}
    </ul>
  );
}
