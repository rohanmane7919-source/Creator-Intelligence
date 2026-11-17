import api from "./api";

export const fetchSummary = () => api.get("/api/dashboard/summary").then((r) => r.data);

export const fetchTopCreators = (metric, limit = 10) =>
  api.get("/api/dashboard/top-creators", { params: { metric, limit } }).then((r) => r.data);

export const fetchHealthDb = () => api.get("/api/health/db").then((r) => r.data);
