import api from "./api";

// The first request after an import scores every record, so allow extra time.
const SLOW = { timeout: 120000 };

const clean = (o) =>
  Object.fromEntries(Object.entries(o).filter(([, v]) => v !== "" && v != null));

export const fetchRiskSummary = (cfg) =>
  api.get("/api/risk/summary", { params: clean(cfg), ...SLOW }).then((r) => r.data);

export const fetchRiskQueue = (params) =>
  api.get("/api/risk/queue", { params: clean(params), ...SLOW }).then((r) => r.data);

export const fetchRiskPost = (id, cfg) =>
  api.get(`/api/risk/posts/${id}`, { params: clean(cfg), ...SLOW }).then((r) => r.data);