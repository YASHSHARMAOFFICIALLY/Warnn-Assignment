import Severity from "./Severity.jsx";

const formatTime = (iso) =>
  new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });

export default function AlertList({ alerts, error, selected, onSelect }) {
  if (!alerts && !error) return <p className="muted">Loading alerts</p>;

  return (
    <>
      {error && <p className="error">Could not refresh alerts: {error}</p>}
      {alerts && alerts.length === 0 && <p className="muted">No alerts yet. Paste one above.</p>}
      {alerts && alerts.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Service</th>
              <th>Message</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Received</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id} className={a.id === selected ? "selected" : ""}>
                <td>{a.service}</td>
                <td>
                  <button className="link" aria-current={a.id === selected} onClick={() => onSelect(a.id)}>{a.message}</button>
                </td>
                <td><Severity value={a.severity} /></td>
                <td><span className={`status ${a.status}`}>{a.status}</span></td>
                <td className="muted nowrap">{formatTime(a.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
