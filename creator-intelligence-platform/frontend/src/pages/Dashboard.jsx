import { useState } from "react";
import { Info, RefreshCw } from "lucide-react";
import KpiCard from "../components/KpiCard";
import { CoverageList, DonutChart, VBarChart } from "../components/charts";
import { Card, CardBody, CardHeader, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { useFetch } from "../hooks/useFetch";
import { useToast } from "../components/Toast";
import { fetchSummary, fetchTopCreators } from "../services/dashboard";
import { formatCompact, formatDateTime, formatInt, formatPct } from "../utils/format";

const METRIC_OPTIONS = [
  { value: "followers", label: "Followers" },
  { value: "engagement_rate_views_pct", label: "Engagement rate (per view)" },
  { value: "engagement_rate_followers_pct", label: "Engagement rate (per follower)" },
  { value: "reach_rate_pct", label: "Reach rate (views per follower)" },
  { value: "views", label: "Views" },
  { value: "likes", label: "Likes" },
];

// Plain-language note on how far apart the bars really are.
function spreadNote(rows) {
  const vals = rows
    .filter((r) => r.has_data && r.avg_engagement_rate_views_pct != null)
    .map((r) => r.avg_engagement_rate_views_pct);
  if (vals.length < 2) return null;
  const hi = Math.max(...vals);
  const lo = Math.min(...vals);
  return `Highest ${hi.toFixed(2)}%, lowest ${lo.toFixed(2)}%, a difference of ${(hi - lo).toFixed(2)} percentage points.`;
}

const pctTick = (v) => `${Math.round(v * 10) / 10}%`;
const pctTip = (v) => `${Number(v).toFixed(2)}%`;

export default function Dashboard() {
  const toast = useToast();
  const [metric, setMetric] = useState("followers");
  const summary = useFetch(fetchSummary, []);
  const top = useFetch(() => fetchTopCreators(metric), [metric]);
  const [refreshing, setRefreshing] = useState(false);

  const s = summary.data;
  const loading = summary.loading && !s;
  const dq = s?.data_quality;

  async function refresh() {
    setRefreshing(true);
    const [a, b] = await Promise.all([summary.reload(), top.reload()]);
    setRefreshing(false);
    if (a && b) toast.success("Dashboard refreshed");
    else toast.error("Could not refresh the dashboard. Check that the backend is running.");
  }

  if (summary.error && !s) {
    return (
      <Card>
        <ErrorState message={summary.error} onRetry={summary.reload} />
      </Card>
    );
  }

  const targets = s ? s.categories.filter((c) => c.is_target) : [];
  const coverageRows = s ? s.categories.filter((c) => c.is_target || c.count > 0) : [];
  const withData = targets.filter((c) => c.has_data).length;
  const platformsWithData = s ? s.platforms.filter((p) => p.has_data) : [];
  const tiersWithData = s ? s.follower_tiers.filter((t) => t.has_data) : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">
            {loading
              ? "Loading dataset details"
              : dq
              ? `Source file ${dq.source_file}, imported ${formatDateTime(dq.imported_at)}, ${formatInt(dq.rows_imported)} records.`
              : "No dataset has been imported yet."}
          </p>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />
          Refresh data
        </button>
      </div>

      {dq && dq.warnings.length > 0 && (
        <div role="note" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <details>
            <summary className="flex cursor-pointer items-center gap-2 font-medium">
              <Info className="h-4 w-4 shrink-0" aria-hidden="true" />
              {dq.warnings.length} data-quality {dq.warnings.length === 1 ? "note" : "notes"} from the cleaning report. Read before interpreting the charts.
            </summary>
            <ul className="mt-3 list-disc space-y-1.5 pl-9">
              {dq.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </details>
        </div>
      )}

      {s && s.kpis.total_records === 0 && (
        <Card>
          <EmptyState title="No creator records in the database">
            Run python scripts\db_tools.py import from the project folder, then refresh this page.
          </EmptyState>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard
          label="Creator records"
          loading={loading}
          value={s && formatInt(s.kpis.total_records)}
          hint="Each record is one creator post in the dataset."
        />
        <KpiCard
          label="Total followers"
          loading={loading}
          value={s && formatCompact(s.kpis.total_followers)}
          title={s && formatInt(s.kpis.total_followers)}
          hint="Sum of follower counts across all records. Not a unique audience: one account can appear in many records."
        />
        <KpiCard
          label="Average engagement rate"
          loading={loading}
          value={s && formatPct(s.kpis.avg_engagement_rate_views_pct)}
          hint="(Likes + comments + shares) divided by views, averaged over all records."
        />
        <KpiCard
          label="Sponsored records"
          loading={loading}
          value={s && formatPct(s.kpis.sponsored_share_pct, 1)}
          hint="Share of records marked as sponsored."
        />
        <KpiCard
          label="Average data completeness"
          loading={loading}
          value={s && formatPct(s.kpis.avg_completeness_pct, 1)}
          hint="Share of 8 tracked fields that are filled in per record. Unknown counts as missing."
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader
            title="Category coverage"
            description={
              s
                ? `${withData} of ${targets.length} target categories have records. Empty ones stay visible so gaps in the data are clear.`
                : "Records per target category."
            }
          />
          <CardBody>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 6 }, (_, i) => (
                  <Skeleton key={i} className="h-6 w-full" />
                ))}
              </div>
            ) : (
              <CoverageList rows={coverageRows} />
            )}
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader title="Platform distribution" description="Share of records on each platform." />
          <CardBody>
            {loading ? (
              <Skeleton className="h-44 w-full" />
            ) : platformsWithData.length === 0 ? (
              <EmptyState title="No platform data" />
            ) : (
              <DonutChart
                data={platformsWithData}
                ariaLabel={`Platform distribution: ${platformsWithData.map((p) => `${p.name} ${p.count}`).join(", ")}`}
              />
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Engagement by platform" description="Average engagement rate per view. Bars start at zero." />
          <CardBody>
            {loading ? (
              <Skeleton className="h-60 w-full" />
            ) : platformsWithData.length === 0 ? (
              <EmptyState title="No data to compare" />
            ) : (
              <>
                <VBarChart
                  data={platformsWithData}
                  valueKey="avg_engagement_rate_views_pct"
                  tickFormat={pctTick}
                  tooltipFormat={pctTip}
                  ariaLabel="Average engagement rate by platform"
                />
                <p className="mt-3 text-xs text-slate-500">{spreadNote(platformsWithData)}</p>
              </>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Engagement by follower tier" description="Average engagement rate per view for each follower range." />
          <CardBody>
            {loading ? (
              <Skeleton className="h-60 w-full" />
            ) : tiersWithData.length === 0 ? (
              <EmptyState title="No data to compare" />
            ) : (
              <>
                <VBarChart
                  data={tiersWithData}
                  valueKey="avg_engagement_rate_views_pct"
                  tickFormat={pctTick}
                  tooltipFormat={pctTip}
                  ariaLabel="Average engagement rate by follower tier"
                />
                <p className="mt-3 text-xs text-slate-500">{spreadNote(tiersWithData)}</p>
              </>
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader
            title="Top creators"
            description="Each row is one creator-post record from the dataset."
            action={
              <div className="flex items-center gap-2">
                <label htmlFor="metric" className="text-sm text-slate-500">Rank by</label>
                <select
                  id="metric"
                  value={metric}
                  onChange={(e) => setMetric(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-800"
                >
                  {METRIC_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            }
          />
          <div className="overflow-x-auto px-5 py-2">
            {top.error && !top.data ? (
              <ErrorState message={top.error} onRetry={top.reload} />
            ) : !top.data ? (
              <div className="space-y-2 py-3">
                {Array.from({ length: 6 }, (_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : top.data.items.length === 0 ? (
              <EmptyState title="No records to rank" />
            ) : (
              <table className={`w-full min-w-[520px] text-left text-sm ${top.loading ? "opacity-60" : ""}`}>
                <caption className="sr-only">Top {top.data.items.length} records ranked by {top.data.label}</caption>
                <thead className="border-b border-slate-200 text-slate-500">
                  <tr>
                    <th scope="col" className="py-2 pr-3 font-medium">#</th>
                    <th scope="col" className="py-2 pr-3 font-medium">Creator</th>
                    <th scope="col" className="py-2 pr-3 font-medium">Platform</th>
                    <th scope="col" className="py-2 pr-3 font-medium">Category</th>
                    {top.data.metric !== "followers" && (
                      <th scope="col" className="py-2 pr-3 text-right font-medium">Followers</th>
                    )}
                    <th scope="col" className="py-2 text-right font-medium">{top.data.label}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {top.data.items.map((c, i) => (
                    <tr key={c.profile_id}>
                      <td className="py-2.5 pr-3 text-slate-400">{i + 1}</td>
                      <td className="py-2.5 pr-3 font-medium text-slate-900">
                        {c.creator_name || <span className="font-normal text-slate-400">Name missing</span>}
                        <span className="block text-xs font-normal text-slate-400">{c.source_content_id}</span>
                      </td>
                      <td className="py-2.5 pr-3 text-slate-700">{c.platform}</td>
                      <td className="py-2.5 pr-3 text-slate-700">{c.category}</td>
                      {top.data.metric !== "followers" && (
                        <td className="py-2.5 pr-3 text-right text-slate-700">{formatInt(c.follower_count)}</td>
                      )}
                      <td className="py-2.5 text-right font-semibold text-slate-900">
                        {top.data.unit === "percent" ? formatPct(c.value) : formatInt(c.value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader title="Recent business searches" />
            <CardBody>
              {loading ? (
                <Skeleton className="h-16 w-full" />
              ) : s.recent_searches.length === 0 ? (
                <EmptyState title="No searches yet">Searches made on AI recommendations will be listed here.</EmptyState>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {s.recent_searches.map((r) => (
                    <li key={r.id} className="py-2.5">
                      <p className="text-sm font-medium text-slate-900">
                        {r.industry || "Any category"}
                        {r.objective ? `, ${r.objective}` : ""}
                      </p>
                      <p className="text-xs text-slate-500">
                        {formatDateTime(r.created_at)}, {r.result_count ?? 0} results
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Model status" />
            <CardBody>
              {loading ? (
                <Skeleton className="h-16 w-full" />
              ) : s.models.length === 0 ? (
                <EmptyState title="No model runs recorded">
                  Evaluation results appear here after a model has been trained.
                </EmptyState>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {s.models.map((m) => (
                    <li key={m.id} className="py-2.5">
                      <p className="text-sm font-medium text-slate-900">
                        {m.model_name} <span className="font-normal text-slate-500">({m.status})</span>
                      </p>
                      <p className="text-xs text-slate-500">{m.task}</p>
                      <p className="text-xs text-slate-400">Trained {formatDateTime(m.trained_at)}</p>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
