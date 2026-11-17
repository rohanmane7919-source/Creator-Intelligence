import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 20000,
});

// Turns any failed request into one clear sentence for the user.
export function errorMessage(err) {
  if (err?.response) {
    const detail = err.response.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) return detail.map((d) => d.msg).join("; ");
    return `The server returned an error (${err.response.status}).`;
  }
  if (err?.code === "ECONNABORTED") return "The request timed out. Try again.";
  return "Cannot reach the API. Check that the backend is running on port 8000.";
}

export default api;
