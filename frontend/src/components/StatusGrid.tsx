import type { ServiceStatus, ServiceStatusLevel } from "../types";

const STATUS_COLORS: Record<ServiceStatusLevel, string> = {
  healthy: "#2e7d32",
  slow: "#f9a825",
  failing: "#c62828",
};

export function StatusGrid({ services }: { services: ServiceStatus[] }) {
  if (services.length === 0) {
    return <p className="empty">No services reporting yet.</p>;
  }

  return (
    <div className="status-grid">
      {services.map((service) => (
        <div key={service.name} className="status-card" style={{ borderColor: STATUS_COLORS[service.status] }}>
          <div className="status-card-header">
            <span className="status-dot" style={{ backgroundColor: STATUS_COLORS[service.status] }} />
            <strong>{service.name}</strong>
          </div>
          <div className="status-card-body">
            <div>{service.status.toUpperCase()}</div>
            <div>p95: {service.p95_latency_ms !== null ? `${service.p95_latency_ms.toFixed(0)}ms` : "–"}</div>
            <div>errors: {(service.error_rate * 100).toFixed(1)}%</div>
          </div>
        </div>
      ))}
    </div>
  );
}
