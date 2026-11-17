import { useFetch } from "../hooks/useFetch";
import { fetchHealthDb } from "../services/dashboard";

export default function ApiStatus() {
  const { error, loading, reload } = useFetch(fetchHealthDb, []);

  let tone = "bg-emerald-50 text-emerald-800";
  let dot = "bg-emerald-500";
  let text = "Backend and database online";
  if (loading) {
    tone = "bg-slate-100 text-slate-600";
    dot = "bg-slate-400";
    text = "Checking connection";
  } else if (error) {
    tone = "bg-red-50 text-red-700";
    dot = "bg-red-500";
    text = "Backend offline";
  }

  return (
    <button
      type="button"
      onClick={reload}
      title={error ? `${error} Click to check again.` : "Click to check again"}
      aria-live="polite"
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${tone}`}
    >
      <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />
      <span className="sr-only sm:not-sr-only">{text}</span>
    </button>
  );
}
