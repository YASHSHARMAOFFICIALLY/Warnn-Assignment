const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

// the backend sends {detail: "text"} for errors, or a list of field errors for 422
async function errorMessage(res) {
  try {
    const { detail } = await res.json();
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => `${d.loc.slice(2).join(".")}: ${d.msg}`).join(", ");
  } catch {
    // body was not JSON
  }
  return `Request failed (${res.status})`;
}

async function request(path, options) {
  const res = await fetch(API + path, options);
  if (!res.ok) throw new Error(await errorMessage(res));
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
