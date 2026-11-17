import {
  Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { formatInt } from "../utils/format";

export const SERIES_COLORS = ["#0f766e", "#0369a1", "#b45309", "#6d28d9", "#64748b"];

// Horizontal bars drawn in plain HTML so empty categories can stay visible.
export function CoverageList({ rows }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <ul className="space-y-3">
      {rows.map((r) => (
        <li key={r.name} className="grid grid-cols-[minmax(0,9.5rem)_1fr_auto] items-center gap-3 text-sm sm:grid-cols-[11rem_1fr_auto]">
          <span className={`truncate ${r.has_data ? "font-medium text-slate-800" : "text-slate-500"}`} title={r.name}>
            {r.name}
          </span>
          {r.has_data ? (
            <div className="h-2.5 rounded-full bg-slate-100" aria-hidden="true">
              <div className="h-2.5 rounded-full bg-teal-700" style={{ width: `${(r.count / max) * 100}%` }} />
            </div>
          ) : (
            <span className="rounded-md border border-dashed border-slate-300 px-2 py-0.5 text-xs text-slate-500">
              No data in this dataset
            </span>
          )}
          <span className={`w-16 text-right ${r.has_data ? "font-medium text-slate-800" : "text-slate-400"}`}>
            {r.has_data ? formatInt(r.count) : "0"}
          </span>
        </li>
      ))}
    </ul>
  );
}

const tick = { fill: "#64748b", fontSize: 12 };

export function VBarChart({ data, valueKey, tickFormat, tooltipFormat, ariaLabel, height = 240 }) {
  return (
    <div role="img" aria-label={ariaLabel} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey="name" tickLine={false} axisLine={false} tick={tick} interval={0} />
          <YAxis tickLine={false} axisLine={false} tick={tick} tickFormatter={tickFormat} domain={[0, "auto"]} width={48} />
          <Tooltip
            formatter={(v) => [tooltipFormat(v), "Average"]}
            cursor={{ fill: "#f1f5f9" }}
            contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }}
          />
          <Bar dataKey={valueKey} fill="#0f766e" radius={[4, 4, 0, 0]} maxBarSize={56} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DonutChart({ data, ariaLabel }) {
  const total = data.reduce((sum, d) => sum + d.count, 0) || 1;
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div role="img" aria-label={ariaLabel} className="h-44 w-44 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="count" nameKey="name" innerRadius={52} outerRadius={80} paddingAngle={2} stroke="none">
              {data.map((d, i) => (
                <Cell key={d.name} fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(v, name) => [`${formatInt(v)} records`, name]}
              contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="w-full space-y-2 text-sm">
        {data.map((d, i) => (
          <li key={d.name} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }} aria-hidden="true" />
            <span className="flex-1 text-slate-700">{d.name}</span>
            <span className="text-slate-500">{formatInt(d.count)}</span>
            <span className="w-12 text-right font-medium text-slate-800">{((d.count / total) * 100).toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
