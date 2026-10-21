const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options) {
  const res = await fetch(API + path, options);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export const listAlerts = () => request("/alerts");
export const getAlert = (id) => request(`/alerts/${id}`);
export const createAlert = (body) =>
  request("/alerts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
