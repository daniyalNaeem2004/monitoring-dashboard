import type { Anomaly, LogEntry, MetricPoint, ServiceStatus } from "./types";

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export function getServices(): Promise<ServiceStatus[]> {
  return getJson<ServiceStatus[]>("/services");
}

export function getServiceMetrics(name: string, rangeSeconds: number): Promise<MetricPoint[]> {
  return getJson<MetricPoint[]>(`/services/${encodeURIComponent(name)}/metrics?range=${rangeSeconds}`);
}

export function getAnomalies(): Promise<Anomaly[]> {
  return getJson<Anomaly[]>("/anomalies");
}

export function getLogs(limit: number): Promise<LogEntry[]> {
  return getJson<LogEntry[]>(`/logs?limit=${limit}`);
}
