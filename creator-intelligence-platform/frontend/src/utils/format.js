const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const full = new Intl.NumberFormat("en");

export const formatCompact = (v) => (v == null ? "n/a" : compact.format(v));
export const formatInt = (v) => (v == null ? "n/a" : full.format(v));
export const formatPct = (v, digits = 2) => (v == null ? "n/a" : `${Number(v).toFixed(digits)}%`);
export const formatDateTime = (iso) =>
  iso ? new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "n/a";
