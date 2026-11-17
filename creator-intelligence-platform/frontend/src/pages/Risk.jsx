import { useEffect, useState } from "react";
import { AlertTriangle, ChevronLeft, ChevronRight, X } from "lucide-react";
import { Card, CardBody, CardHeader, EmptyState, ErrorState, Skeleton } from "../components/ui";
import KpiCard from "../components/KpiCard";
import { useFetch } from "../hooks/useFetch";
import { fetchRiskPost, fetchRiskQueue, fetchRiskSummary } from "../services/risk";
import { formatInt } from "../utils/format";

const DEFAULTS = {
  outlier_percentile: 0.99,
  min_completeness_pct: 60,
  medium_threshold: 25,
  high_threshold: 50,
};

const LEVEL_STYLE = {
  high: "bg-red-50 text-red-700 ring-red-600/20",
  medium: "bg-amber-50 text-amber-800 ring-amber-600/20",
  low: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
};

const selectClass =
  "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-600";

function LevelBadge({ level }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${
        LEVEL_STYLE[level] ?? "bg-slate-50 text-slate-700 ring-slate-500/20"
      }`}
    >
      {level}
    </span>
  );
}

const show = (v) => (v == null ? "n/a" : typeof v === "boolean" ? (v ? "yes" : "no") : String(v));

/* ---------- settings ---------- */
function SettingsForm({ applied, onApply, busy }) {
  const [draft, setDraft] = useState(applied);
  const set = (k) => (e) => setDraft({ ...draft, [k]: e.target.value });
  const num = (v) => (v === "" ? NaN : Number(v));

  const comp = num(draft.min_completeness_pct);
  const med = num(draft.medium_threshold);
  const high = num(draft.high_threshold);
  const errors = [];
  if (!(comp >= 0 && comp <= 100)) errors.push("Minimum completeness must be between 0 and 100.");
  if (!(med >= 0 && high <= 100 && med < high))
    errors.push("The medium threshold must be lower than the high threshold, both between 0 and 100.");

  const submit = (e) => {
    e.preventDefault();
    if (errors.length) return;
    onApply({
      outlier_percentile: Number(draft.outlier_percentile),
      min_completeness_pct: comp,
      medium_threshold: med,
      high_threshold: high,
    });
  };

  return (
    <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div>
        <label htmlFor="pct" className="block text-sm font-medium text-slate-700">Outlier percentile</label>
        <select id="pct" className={`${selectClass} mt-1 w-full`} value={draft.outlier_percentile} onChange={set("outlier_percentile")}>
          {[0.95, 0.975, 0.99, 0.995].map((p) => (
            <option key={p} value={p}>{(p * 100).toFixed(1)}th percentile</option>
          ))}
        </select>
        <p className="mt-1 text-xs text-slate-500">Engagement or reach above this level for the platform counts as unusual.</p>
      </div>
      <div>
        <label htmlFor="comp" className="block text-sm font-medium text-slate-700">Minimum completeness (%)</label>
        <input id="comp" type="number" min="0" max="100" className={`${selectClass} mt-1 w-full`} value={draft.min_completeness_pct} onChange={set("min_completeness_pct")} />
        <p className="mt-1 text-xs text-slate-500">Records below this are flagged as low completeness.</p>
      </div>
      <div>
        <label htmlFor="med" className="block text-sm font-medium text-slate-700">Medium priority from score</label>
        <input id="med" type="number" min="0" max="100" className={`${selectClass} mt-1 w-full`} value={draft.medium_threshold} onChange={set("medium_threshold")} />
      </div>
      <div>
        <label htmlFor="high" className="block text-sm font-medium text-slate-700">High priority from score</label>
        <input id="high" type="number" min="0" max="100" className={`${selectClass} mt-1 w-full`} value={draft.high_threshold} onChange={set("high_threshold")} />
      </div>
      <div className="sm:col-span-2 lg:col-span-4">
        {errors.length > 0 && (
          <ul role="alert" className="mb-3 list-disc pl-5 text-sm text-red-600">
            {errors.map((m) => <li key={m}>{m}</li>)}
          </ul>
        )}
        <div className="flex flex-wrap gap-2">
          <button type="submit" disabled={busy || errors.length > 0}
            className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50">
            {busy ? "Applying…" : "Apply settings"}
          </button>
          <button type="button" disabled={busy}
            onClick={() => { setDraft(DEFAULTS); onApply(DEFAULTS); }}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50">
            Reset to defaults
          </button>
        </div>
      </div>
    </form>
  );
}

/* ---------- record detail ---------- */
function PostDetail({ id, cfg, onClose }) {
  const { data, error, loading, reload } = useFetch(() => fetchRiskPost(id, cfg), [id, JSON.stringify(cfg)]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/40" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label={`Risk details for record ${id}`}
        onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-md overflow-y-auto bg-white p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Record {id}</h2>
            {data && <p className="text-sm text-slate-500">{data.creator_name ?? "Unnamed"} · {data.platform ?? "Unknown platform"}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="Close details"
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100">
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {loading && !data && <Skeleton className="mt-6 h-40 w-full" />}
        {error && <ErrorState message={error} onRetry={reload} />}

        {data && (
          <>
            <div className="mt-4 flex items-center gap-3">
              <span className="text-3xl font-semibold text-slate-900">{data.risk_score}</span>
              <span className="text-sm text-slate-500">/ 100 review score</span>
              <LevelBadge level={data.review_priority} />
            </div>
            <ul className="mt-5 space-y-3">
              {data.signals.map((s) => {
                const status = !s.evaluated ? "Not evaluated" : s.triggered ? "Triggered" : "Not triggered";
                const tone = !s.evaluated ? "bg-slate-100 text-slate-600" : s.triggered ? "bg-amber-100 text-amber-800" : "bg-emerald-50 text-emerald-700";
                return (
                  <li key={s.key} className="rounded-lg border border-slate-200 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-slate-900">{s.label}</p>
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>{status}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">{s.explanation}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Value: {show(s.value)} · Threshold: {show(s.threshold)} · Weight: {s.weight}
                    </p>
                  </li>
                );
              })}
            </ul>
            <p className="mt-5 rounded-lg bg-slate-50 p-3 text-xs leading-relaxed text-slate-600">{data.disclaimer}</p>
          </>
        )}
      </aside>
    </div>
  );
}

/* ---------- review queue ---------- */
function QueueSection({ cfg, platforms, signals, labelOf, onSelect }) {
  const [level, setLevel] = useState("");
  const [platform, setPlatform] = useState("");
  const [signal, setSignal] = useState("");
  const [page, setPage] = useState(1);

  const { data, error, loading, reload } = useFetch(
    () => fetchRiskQueue({ ...cfg, level, platform, signal, page, page_size: 20 }),
    [JSON.stringify(cfg), level, platform, signal, page],
  );
  const change = (setter) => (e) => { setter(e.target.value); setPage(1); };

  return (
    <Card>
      <CardHeader
        title="Review queue"
        description="Records sorted by review score, highest first. A high score means 'look at this', not 'this is fraud'."
        action={
          <div className="flex flex-wrap gap-2">
            <select aria-label="Filter by priority" className={selectClass} value={level} onChange={change(setLevel)}>
              <option value="">All priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select aria-label="Filter by platform" className={selectClass} value={platform} onChange={change(setPlatform)}>
              <option value="">All platforms</option>
              {platforms.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <select aria-label="Filter by signal" className={selectClass} value={signal} onChange={change(setSignal)}>
              <option value="">Any signal</option>
              {signals.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
            </select>
          </div>
        }
      />
      {error && <ErrorState message={error} onRetry={reload} />}
      {!error && !data && <CardBody><Skeleton className="h-48 w-full" /></CardBody>}
      {data && data.items.length === 0 && (
        <EmptyState title="No records match these filters">Try removing a filter or lowering the thresholds.</EmptyState>
      )}
      {data && data.items.length > 0 && (
        <>
          <div className={`overflow-x-auto ${loading ? "opacity-60" : ""}`}>
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Record</th>
                  <th className="px-3 py-3 font-medium">Platform</th>
                  <th className="px-3 py-3 font-medium">Score</th>
                  <th className="px-3 py-3 font-medium">Priority</th>
                  <th className="px-3 py-3 font-medium">Signals triggered</th>
                  <th className="px-5 py-3"><span className="sr-only">Details</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((r) => (
                  <tr key={r.profile_id} className="hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <p className="font-medium text-slate-900">{r.creator_name ?? "Unnamed"}</p>
                      <p className="text-xs text-slate-500">ID {r.profile_id}</p>
                    </td>
                    <td className="px-3 py-3 text-slate-700">{r.platform ?? "n/a"}</td>
                    <td className="px-3 py-3 font-medium text-slate-900">{r.risk_score}</td>
                    <td className="px-3 py-3"><LevelBadge level={r.review_priority} /></td>
                    <td className="px-3 py-3 text-slate-600">
                      {r.signals_triggered.length ? r.signals_triggered.map(labelOf).join(", ") : "None"}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button type="button" onClick={() => onSelect(r.profile_id)}
                        className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50">
                        Explain
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-5 py-3 text-sm text-slate-600">
            <span>{formatInt(data.total)} records · page {data.page} of {data.pages}</span>
            <div className="flex gap-2">
              <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Previous page"
                className="rounded-lg border border-slate-300 p-1.5 hover:bg-slate-50 disabled:opacity-40">
                <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              </button>
              <button type="button" disabled={page >= data.pages} onClick={() => setPage(page + 1)} aria-label="Next page"
                className="rounded-lg border border-slate-300 p-1.5 hover:bg-slate-50 disabled:opacity-40">
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}

/* ---------- page ---------- */
export default function Risk() {
  const [cfg, setCfg] = useState(DEFAULTS);
  const [selected, setSelected] = useState(null);
  const summary = useFetch(() => fetchRiskSummary(cfg), [JSON.stringify(cfg)]);
  const s = summary.data;

  const labelOf = (key) => s?.signals.find((x) => x.key === key)?.label ?? key;
  const total = s?.total ?? 0;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Trust and risk</h1>
        <p className="mt-1 text-sm text-slate-500">
          Rule-based signals that help decide which records to check first. Each record is one creator post.
        </p>
      </div>

      <div role="note" className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <p>
          {s?.disclaimer ??
            "Risk signals are not proof of fraud. Unusual values can have innocent explanations."}{" "}
          This is a transparent rule set, not a machine-learning model.
        </p>
      </div>

      {summary.error && (
        <Card><ErrorState message={summary.error} onRetry={summary.reload} /></Card>
      )}

      {!summary.error && (
        <>
          {summary.loading && !s && (
            <p className="text-sm text-slate-500">
              Scoring all records. The first load can take several seconds.
            </p>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Records scored" value={formatInt(s?.total)} loading={summary.loading && !s}
              hint="Every imported record is scored with the same rules." />
            <KpiCard label="High priority" value={formatInt(s?.review_priority.high)} loading={summary.loading && !s}
              hint={`Score of ${cfg.high_threshold} or more.`} />
            <KpiCard label="Medium priority" value={formatInt(s?.review_priority.medium)} loading={summary.loading && !s}
              hint={`Score of ${cfg.medium_threshold} to below ${cfg.high_threshold}.`} />
            <KpiCard label="Low priority" value={formatInt(s?.review_priority.low)} loading={summary.loading && !s}
              hint={`Score below ${cfg.medium_threshold}.`} />
          </div>

          <Card>
            <CardHeader title="Risk settings" description="Change the thresholds and see the counts and queue update." />
            <CardBody>
              <SettingsForm applied={cfg} onApply={setCfg} busy={summary.loading} />
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="How often each signal fires" description="Share of all records where the signal was triggered." />
            <CardBody>
              {!s ? (
                <Skeleton className="h-32 w-full" />
              ) : (
                <ul className="space-y-3">
                  {s.signals.map((sig) => {
                    const pct = total ? (sig.count / total) * 100 : 0;
                    return (
                      <li key={sig.key}>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-800">{sig.label}</span>
                          <span className="text-slate-500">{formatInt(sig.count)} ({pct.toFixed(1)}%)</span>
                        </div>
                        <div className="mt-1 h-2 rounded-full bg-slate-100">
                          <div className="h-2 rounded-full bg-teal-600" style={{ width: `${Math.min(100, pct)}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardBody>
          </Card>

          {s && (
            <QueueSection cfg={cfg} platforms={Object.keys(s.baselines).sort()} signals={s.signals}
              labelOf={labelOf} onSelect={setSelected} />
          )}
        </>
      )}

      {selected != null && <PostDetail id={selected} cfg={cfg} onClose={() => setSelected(null)} />}
    </div>
  );
}