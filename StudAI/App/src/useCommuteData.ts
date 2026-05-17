import { useEffect, useRef, useState } from "react";
import type { Housing, CommuteMap } from "./types";
import {
  getCachedCommute,
  setCachedCommute,
  fetchOsrmCommute,
} from "./lib/commuteRouter";

export type { CommuteMap };

const THROTTLE_MS = 200;

export function useCommuteData(
  housing: Housing[],
  workPin: [number, number] | null
): {
  commuteMap: CommuteMap;
  isComputing: boolean;
  remaining: number;
  total: number;
  routingError: string | null;
} {
  const [commuteMap, setCommuteMap] = useState<CommuteMap>({});
  const [isComputing, setIsComputing] = useState(false);
  const [remaining, setRemaining] = useState(0);
  const [total, setTotal] = useState(0);
  const [routingError, setRoutingError] = useState<string | null>(null);

  const abortRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    abortRef.current = true;
    clearTimeout(timerRef.current);
    setRoutingError(null);

    if (!workPin) {
      setCommuteMap({});
      setIsComputing(false);
      setRemaining(0);
      setTotal(0);
      return;
    }

    abortRef.current = false;

    const map: CommuteMap = {};
    const queue: Housing[] = [];
    for (const h of housing) {
      const cached = getCachedCommute(h.id, workPin);
      if (cached) map[h.id] = cached;
      else queue.push(h);
    }
    setCommuteMap(map);
    setTotal(queue.length);
    setRemaining(queue.length);

    if (queue.length === 0) {
      setIsComputing(false);
      return;
    }

    setIsComputing(true);
    let idx = 0;
    const pin = workPin;

    const processNext = async () => {
      if (abortRef.current || idx >= queue.length) {
        if (!abortRef.current) setIsComputing(false);
        return;
      }
      const h = queue[idx++];
      try {
        const result = await fetchOsrmCommute([h.lat, h.lng], pin);
        if (abortRef.current) return;
        setCachedCommute(h.id, pin, result);
        setCommuteMap((prev) => ({ ...prev, [h.id]: result }));
        setRemaining((n) => Math.max(0, n - 1));
      } catch (err) {
        if (abortRef.current) return;
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes("429")) {
          setRoutingError("Rate limited — try again in a moment");
          setIsComputing(false);
          return;
        }
        setRemaining((n) => Math.max(0, n - 1));
      }
      if (!abortRef.current) {
        timerRef.current = setTimeout(processNext, THROTTLE_MS);
      }
    };

    processNext();

    return () => {
      abortRef.current = true;
      clearTimeout(timerRef.current);
    };
  }, [housing, workPin]);

  return { commuteMap, isComputing, remaining, total, routingError };
}
