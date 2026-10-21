import { useEffect, useState } from "react";
import { listAlerts } from "./api.js";
import AlertForm from "./AlertForm.jsx";
import AlertList from "./AlertList.jsx";
import AlertDetail from "./AlertDetail.jsx";

export default function App() {
  const [alerts, setAlerts] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const load = () =>
      listAlerts()
        .then((data) => {
          setAlerts(data);
          setError("");
        })
        .catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <>
      <header>Alert triage</header>
      <main>
        <section>
          <AlertForm onCreated={(alert) => setSelected(alert.id)} />
          <AlertList alerts={alerts} error={error} selected={selected} onSelect={setSelected} />
        </section>
        <section>
          <AlertDetail id={selected} />
        </section>
      </main>
    </>
  );
}
