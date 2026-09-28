export type ServiceStatusLevel = "healthy" | "slow" | "failing";

export interface ServiceStatus {
  name: string;
  status: ServiceStatusLevel;
  last_heartbeat: string;
  error_rate: number;
  p95_latency_ms: number | null;
  seconds_since_heartbeat: number;
}

export interface MetricPoint {
  timestamp: string;
  latency_ms: number;
  status_code: number;
}

export interface Anomaly {
  service: string;
  metric: string;
  value: number;
  baseline_mean: number;
  z_score: number;
  started_at: string;
  resolved_at: string | null;
}

export interface LogEntry {
  service: string;
  timestamp: string;
  level: string;
  message: string;
}
