import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../services/api";

// Runs an async fetcher on mount and whenever `deps` change.
// Ignores out-of-date responses, keeps old data visible while reloading,
// and exposes reload() which resolves to true (ok) or false (failed).
export function useFetch(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const latest = useRef(0);

  const run = useCallback(async () => {
    const id = ++latest.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetcher();
      if (id === latest.current) setState({ data, error: null, loading: false });
      return true;
    } catch (err) {
      if (id === latest.current) setState({ data: null, error: errorMessage(err), loading: false });
      return false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { ...state, reload: run };
}
