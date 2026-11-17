import api from "./api";

// Drop empty filter values so the API only sees filters the user actually set.
const clean = (o) =>
  Object.fromEntries(Object.entries(o).filter(([, v]) => v !== "" && v != null));

export const fetchFilters = () => api.get("/api/discovery/filters").then((r) => r.data);

export const searchCreators = (params) =>
  api.get("/api/discovery/creators", { params: clean(params) }).then((r) => r.data);

export const fetchCreator = (id) => api.get(`/api/discovery/creators/${id}`).then((r) => r.data);