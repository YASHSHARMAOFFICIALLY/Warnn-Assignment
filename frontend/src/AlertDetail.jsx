import { useEffect, useState } from "react";
import { getAlert } from "./api.js";

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
          <dd>{Math.round(r.confidence * 100)}%</dd>
          <dt>Severity</dt>
          <dd>{r.severity}</dd>
          <dt>Action items</dt>
          <dd>
            <ul>{r.action_items.map((item, i) => <li key={i}>{item}</li>)}</ul>
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
