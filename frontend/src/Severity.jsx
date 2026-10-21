export default function Severity({ value }) {
  if (!value) return <span className="muted">-</span>;
  return <span className={`badge ${value.toLowerCase()}`}>{value}</span>;
}
