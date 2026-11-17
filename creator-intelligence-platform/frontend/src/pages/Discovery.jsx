import { useEffect, useState } from "react";
import { AlertTriangle, ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, X } from "lucide-react";
import { Card, CardBody, CardHeader, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { useFetch } from "../hooks/useFetch";
import { fetchCreator, fetchFilters, searchCreators } from "../services/discovery";
import { formatInt, formatPct } from "../utils/format";

const PAGE_SIZE = 20;
const EMPTY = {
  q: "", platform: "", category: "", language: "", content_type: "", sponsored: "",
  min_followers: "", max_followers: "", min_engagement: "", max_engagement: "",
};

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-600";

const Na = () => <span className="text-slate-400">n/a</span>;
const yesNo = (v) => (v == null ? <Na /> : v ? "Yes" : "No");

function validate(d) {
  const errs = [];
  const n = (v) => (v === "" ? null : Number(v));
  const minF = n(d.min_followers), maxF = n(d.max_followers);
  const minE = n(d.min_engagement), maxE = n(d.max_engagement);
  const bad = (v) => v !== null && (Number.isNaN(v) || v < 0);
  if ([minF, maxF].some((v) => bad(v) || (v !== null && !Number.isInteger(v))))
    errs.push("Follower limits must be whole numbers of 0 or more.");
  if ([minE, maxE].some(bad)) errs.push("Engagement limits must be numbers of 0 or more.");
  if (minF !== null && maxF !== null && minF > maxF)
    errs.push("Minimum followers cannot be greater than maximum followers.");
  if (minE !== null && maxE !== null && minE > maxE)
    errs.push("Minimum engagement cannot be greater than maximum engagement.");
  return errs;
}

function Field({ id, label, children, hint }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

function Badge({ tone = "slate", title, children }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    amber: "bg-amber-100 text-amber-800",
    red: "bg-red-50 text-red-700",
  };
  return (
    <span title={title} className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

function SortTh({ label, k, sort, order, onSort, className = "" }) {
  const active = sort === k;
  const Icon = !active ? ArrowUpDown : order === "asc" ? ArrowUp : ArrowDown;
  return (
    <th scope="col" className={`px-3 py-3 font-medium ${className}`}
      aria-sort={active ? (order === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" onClick={() => onSort(k)}
        className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide hover:text-slate-800">
        {label}
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </th>
  );
}

/* ---------- detail panel ---------- */
function Row({ label, children }) {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-2 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-900">{children}</dd>
    </div>
  );
}

function Detail({ id, onClose }) {
  const { data: d, error, loading, reload } = useFetch(() => fetchCreator(id), [id]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/40" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label={`Details for record ${id}`}
        onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-md overflow-y-auto bg-white p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Record {id}</h2>
            <p className="text-sm text-slate-500">One creator post from the dataset</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close details"
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100">
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {loading && !d && <Skeleton className="mt-6 h-64 w-full" />}
        {error && <ErrorState message={error} onRetry={reload} />}

        {d && (
          <>
            {d.identity_warning && (
              <div role="note" className="mt-4 flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <p>{d.identity_warning}</p>
              </div>
            )}
            <dl className="mt-4">
              <Row label="Name">{d.creator_name ?? <Na />}</Row>
              <Row label="Source creator ID">{d.source_creator_id}</Row>
              <Row label="Platform">{d.platform}</Row>
              <Row label="Category">
                {d.category}
                {d.category_mapping === "partial" && <span className="ml-1 text-xs text-amber-700">(partial mapping)</span>}
              </Row>
              <Row label="Language">{d.language ?? <Na />}</Row>
              <Row label="Content type">{d.content_type ?? <Na />}</Row>
              <Row label="Followers">{formatInt(d.follower_count)}</Row>
              <Row label="Sponsored">{yesNo(d.is_sponsored)}</Row>
              <Row label="Engagement (on views)">{formatPct(d.engagement_rate_views_pct)}</Row>
              <Row label="Engagement (on followers)">{formatPct(d.engagement_rate_followers_pct)}</Row>
              <Row label="Reach rate">{formatPct(d.reach_rate_pct)}</Row>
              <Row label="Data completeness">{formatPct(d.completeness_pct, 1)}</Row>
              <Row label="Likes exceed views">{yesNo(d.flag_likes_exceed_views)}</Row>
              <Row label="Interactions exceed followers">{yesNo(d.flag_interactions_exceed_followers)}</Row>
              <Row label="Records with this source ID">{formatInt(d.same_id_records)}</Row>
            </dl>
          </>
        )}
      </aside>
    </div>
  );
}

/* ---------- page ---------- */
export default function Discovery() {
  const filters = useFetch(fetchFilters, []);
  const f = filters.data;

  const [draft, setDraft] = useState(EMPTY);
  const [applied, setApplied] = useState(EMPTY);
  const [sort, setSort] = useState("followers");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);

  const errors = validate(draft);
  const set = (k) => (e) => setDraft({ ...draft, [k]: e.target.value });

  const { data, error, loading, reload } = useFetch(
    () => searchCreators({ ...applied, sort, order, page, page_size: PAGE_SIZE }),
    [JSON.stringify(applied), sort, order, page],
  );

  const apply = (e) => {
    e.preventDefault();
    if (errors.length) return;
    setApplied({ ...draft, q: draft.q.trim() });
    setPage(1);
  };
  const reset = () => {
    setDraft(EMPTY);
    setApplied(EMPTY);
    setPage(1);
  };
  const onSort = (k) => {
    if (sort === k) setOrder(order === "desc" ? "asc" : "desc");
    else {
      setSort(k);
      setOrder(k === "name" ? "asc" : "desc");
    }
    setPage(1);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Creator discovery</h1>
        <p className="mt-1 text-sm text-slate-500">
          Search and filter every record in the database. Each record is one creator post, not a verified unique creator.
        </p>
      </div>

      <Card>
        <CardHeader title="Search and filters" description="Set your filters, then press Apply." />
        <CardBody>
          <form onSubmit={apply} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="sm:col-span-2">
              <Field id="q" label="Name or source ID">
                <input id="q" type="search" maxLength={100} placeholder="e.g. nicole or creator_586"
                  className={inputClass} value={draft.q} onChange={set("q")} />
              </Field>
            </div>
            <Field id="platform" label="Platform">
              <select id="platform" className={inputClass} value={draft.platform} onChange={set("platform")}>
                <option value="">All platforms</option>
                {(f?.platforms ?? []).map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </Field>
            <Field id="category" label="Category">
              <select id="category" className={inputClass} value={draft.category} onChange={set("category")}>
                <option value="">All categories</option>
                {(f?.categories ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field id="language" label="Language">
              <select id="language" className={inputClass} value={draft.language} onChange={set("language")}>
                <option value="">Any language</option>
                {(f?.languages ?? []).map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </Field>
            <Field id="ctype" label="Content type">
              <select id="ctype" className={inputClass} value={draft.content_type} onChange={set("content_type")}>
                <option value="">Any type</option>
                {(f?.content_types ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field id="sponsored" label="Sponsored">
              <select id="sponsored" className={inputClass} value={draft.sponsored} onChange={set("sponsored")}>
                <option value="">Any</option>
                <option value="true">Sponsored only</option>
                <option value="false">Not sponsored</option>
              </select>
            </Field>
            <Field id="minf" label="Minimum followers"
              hint={f ? `Data range: ${formatInt(f.follower_min)} to ${formatInt(f.follower_max)}` : undefined}>
              <input id="minf" type="number" min="0" step="1" className={inputClass}
                value={draft.min_followers} onChange={set("min_followers")} />
            </Field>
            <Field id="maxf" label="Maximum followers">
              <input id="maxf" type="number" min="0" step="1" className={inputClass}
                value={draft.max_followers} onChange={set("max_followers")} />
            </Field>
            <Field id="mine" label="Minimum engagement (% of views)">
              <input id="mine" type="number" min="0" step="0.1" className={inputClass}
                value={draft.min_engagement} onChange={set("min_engagement")} />
            </Field>
            <Field id="maxe" label="Maximum engagement (% of views)">
              <input id="maxe" type="number" min="0" step="0.1" className={inputClass}
                value={draft.max_engagement} onChange={set("max_engagement")} />
            </Field>

            <div className="sm:col-span-2 lg:col-span-4">
              {errors.length > 0 && (
                <ul role="alert" className="mb-3 list-disc pl-5 text-sm text-red-600">
                  {errors.map((m) => <li key={m}>{m}</li>)}
                </ul>
              )}
              <div className="flex flex-wrap gap-2">
                <button type="submit" disabled={errors.length > 0}
                  className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50">
                  Apply filters
                </button>
                <button type="button" onClick={reset}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                  Clear all
                </button>
              </div>
            </div>
          </form>
          {filters.error && (
            <p role="alert" className="mt-3 text-sm text-red-600">
              Filter options could not be loaded: {filters.error}
            </p>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Results"
          description={data ? `${formatInt(data.total)} matching records` : "Loading records…"}
        />
        {error && <ErrorState message={error} onRetry={reload} />}
        {!error && !data && <CardBody><Skeleton className="h-64 w-full" /></CardBody>}
        {data && data.items.length === 0 && (
          <EmptyState title="No records match these filters">
            Try widening the follower or engagement range, or press Clear all.
          </EmptyState>
        )}
        {data && data.items.length > 0 && (
          <>
            <div className={`overflow-x-auto ${loading ? "opacity-60" : ""}`}>
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead className="text-slate-500">
                  <tr>
                    <SortTh label="Record" k="name" sort={sort} order={order} onSort={onSort} className="px-5" />
                    <th scope="col" className="px-3 py-3 text-xs font-medium uppercase tracking-wide">Platform</th>
                    <th scope="col" className="px-3 py-3 text-xs font-medium uppercase tracking-wide">Category</th>
                    <SortTh label="Followers" k="followers" sort={sort} order={order} onSort={onSort} />
                    <SortTh label="Engagement" k="engagement" sort={sort} order={order} onSort={onSort} />
                    <SortTh label="Completeness" k="completeness" sort={sort} order={order} onSort={onSort} />
                    <th scope="col" className="px-3 py-3 text-xs font-medium uppercase tracking-wide">Data flags</th>
                    <th scope="col" className="px-5 py-3"><span className="sr-only">Details</span></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((r) => {
                    const flagged = r.flag_likes_exceed_views || r.flag_interactions_exceed_followers;
                    return (
                      <tr key={r.id} className="hover:bg-slate-50">
                        <td className="px-5 py-3">
                          <p className="font-medium text-slate-900">
                            {r.creator_name ?? <span className="italic text-slate-400">Missing name</span>}
                          </p>
                          <p className="text-xs text-slate-500">Source ID {r.source_creator_id}</p>
                        </td>
                        <td className="px-3 py-3 text-slate-700">{r.platform}</td>
                        <td className="px-3 py-3 text-slate-700">
                          {r.category}
                          {r.category_mapping === "partial" && (
                            <div className="mt-0.5">
                              <Badge tone="amber" title="The source category only partly matches this target category.">
                                Partial mapping
                              </Badge>
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-3 font-medium text-slate-900">{formatInt(r.follower_count)}</td>
                        <td className="px-3 py-3 text-slate-700">{formatPct(r.engagement_rate_views_pct)}</td>
                        <td className="px-3 py-3">
                          <span className={r.completeness_pct < 60 ? "font-medium text-amber-700" : "text-slate-700"}>
                            {formatPct(r.completeness_pct, 0)}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          {flagged ? (
                            <Badge tone="amber" title="Interactions exceed views or followers in the source data.">
                              Data flag
                            </Badge>
                          ) : (
                            <span className="text-slate-400">None</span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <button type="button" onClick={() => setSelected(r.id)}
                            className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50">
                            View
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-5 py-3 text-sm text-slate-600">
              <span>Page {data.page} of {formatInt(data.pages)}</span>
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

      {selected != null && <Detail id={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}