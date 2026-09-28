import { useEffect, useState } from "react";
import "./App.css";
import { getAnomalies, getLogs, getServiceMetrics, getServices } from "./api";
import { AnomaliesList } from "./components/AnomaliesList";
import { LatencyChart } from "./components/LatencyChart";
import { LogsTable } from "./components/LogsTable";
import { StatusGrid } from "./components/StatusGrid";
import type { Anomaly, LogEntry, MetricPoint, ServiceStatus } from "./types";

const POLL_INTERVAL_MS = 3000;
const METRICS_RANGE_SECONDS = 300;
const LOGS_LIMIT = 50;

export default function App() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [metricsByService, setMetricsByService] = useState<Record<string, MetricPoint[]>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      try {
        const [servicesData, anomaliesData, logsData] = await Promise.all([
          getServices(),
          getAnomalies(),
          getLogs(LOGS_LIMIT),
        ]);
        if (cancelled) return;
        setServices(servicesData);
        setAnomalies(anomaliesData);
        setLogs(logsData);
        setError(null);

        const metricsEntries = await Promise.all(
          servicesData.map(
            async (s) => [s.name, await getServiceMetrics(s.name, METRICS_RANGE_SECONDS)] as const,
          ),
        );
        if (cancelled) return;
        setMetricsByService(Object.fromEntries(metricsEntries));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    };

    tick();
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="app">
      <h1>Service Health Dashboard</h1>
      {error && <p className="error-banner">API error: {error}</p>}

      <section>
        <h2>Status</h2>
        <StatusGrid services={services} />
      </section>

      <section>
        <h2>Latency (last {Math.round(METRICS_RANGE_SECONDS / 60)} min)</h2>
        <div className="charts-grid">
          {services.map((s) => (
            <LatencyChart key={s.name} serviceName={s.name} points={metricsByService[s.name] ?? []} />
          ))}
        </div>
      </section>

      <section>
        <h2>Active Anomalies</h2>
        <AnomaliesList anomalies={anomalies} />
      </section>

      <section>
        <h2>Recent Logs</h2>
        <LogsTable logs={logs} />
      </section>
    </div>
  );
}
