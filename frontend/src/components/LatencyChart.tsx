import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MetricPoint } from "../types";

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString();
}

export function LatencyChart({ serviceName, points }: { serviceName: string; points: MetricPoint[] }) {
  const data = points.map((p) => ({ time: formatTime(p.timestamp), latency_ms: p.latency_ms }));

  return (
    <div className="latency-chart">
      <h4>{serviceName}</h4>
      {data.length === 0 ? (
        <p className="empty">No recent data.</p>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" minTickGap={30} tick={{ fontSize: 11 }} />
            <YAxis width={40} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="latency_ms" stroke="#1565c0" dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
