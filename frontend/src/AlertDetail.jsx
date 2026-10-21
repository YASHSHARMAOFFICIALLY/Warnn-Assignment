import { useEffect, useState } from "react";
import { getAlert } from "./api.js";
import Severity from "./Severity.jsx";

export default function AlertDetail({ id }) {
  const [alert, setAlert] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (id == null) return;
    setAlert(null);
    const load = () =>
      getAlert(id)
        .then((data) => {
          setAlert(data);
          setError("");
        })
        .catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [id]);

  if (id == null) return <p className="muted">Select an alert to see its triage result.</p>;
  if (error) return <p className="error">{error}</p>;
  if (!alert) return <p className="muted">Loading</p>;

  const r = alert.result;
  const confidence = r ? Math.round(r.confidence * 100) : 0;
  return (
    <div>
      <h2>{alert.service}</h2>
      <p>{alert.message}</p>
      <p className="muted">
        Status: <span className={`status ${alert.status}`}>{alert.status}</span>
        {alert.severity_hint && <> &middot; hint: {alert.severity_hint}</>}
      </p>
      {r ? (
        <dl>
          <dt>Probable cause</dt>
          <dd>{r.probable_cause}</dd>
          <dt>Confidence</dt>
          <dd className="confidence">
            <div className="bar" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={confidence}>
              <div style={{ width: `${confidence}%` }} />
            </div>
            {confidence}%
          </dd>
          <dt>Severity</dt>
          <dd><Severity value={r.severity} /></dd>
          <dt>Action items</dt>
          <dd>
            <ol>{r.action_items.map((item, i) => <li key={i}>{item}</li>)}</ol>
          </dd>
        </dl>
      ) : (
        <p className="muted">
          {alert.status === "failed" ? "Triage failed, no result." : "No result yet."}
        </p>
      )}
    </div>
  );
}
