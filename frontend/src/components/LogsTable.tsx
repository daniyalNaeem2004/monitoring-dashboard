import type { LogEntry } from "../types";

const LEVEL_COLORS: Record<string, string> = {
  ERROR: "#c62828",
  WARN: "#f9a825",
  INFO: "#1565c0",
  DEBUG: "#616161",
};

export function LogsTable({ logs }: { logs: LogEntry[] }) {
  if (logs.length === 0) {
    return <p className="empty">No logs yet.</p>;
  }

  return (
    <table className="logs-table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Service</th>
          <th>Level</th>
          <th>Message</th>
        </tr>
      </thead>
      <tbody>
        {logs.map((log, i) => (
          <tr key={i}>
            <td>{new Date(log.timestamp).toLocaleTimeString()}</td>
            <td>{log.service}</td>
            <td style={{ color: LEVEL_COLORS[log.level.toUpperCase()] ?? "inherit" }}>{log.level}</td>
            <td>{log.message}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
