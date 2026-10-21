import { useState } from "react";
import { createAlert } from "./api.js";

const EXAMPLE = `{
  "service": "checkout-api",
  "message": "5xx rate above 20% for 5 minutes",
  "severity_hint": "high",
  "timestamp": "2026-10-22T10:00:00Z"
}`;

export default function AlertForm({ onCreated }) {
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function submit(e) {
    e.preventDefault();
    let body;
    try {
      body = JSON.parse(text);
    } catch (err) {
      setError(`Invalid JSON: ${err.message}`);
      return;
    }
    setSending(true);
    setError("");
    try {
      const alert = await createAlert(body);
      setText("");
      onCreated(alert);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <label htmlFor="alert-json">Alert JSON</label>
      <textarea
        id="alert-json"
        rows={7}
        value={text}
        placeholder={EXAMPLE}
        spellCheck={false}
        onChange={(e) => setText(e.target.value)}
      />
      {error && <p className="error" role="alert">{error}</p>}
      <button type="submit" disabled={sending || !text.trim()}>
        {sending ? "Submitting" : "Submit"}
      </button>
    </form>
  );
}
