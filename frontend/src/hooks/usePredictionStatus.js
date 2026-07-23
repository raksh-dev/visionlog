import { useEffect, useRef, useState } from "react";
import { getStatus } from "../api/visionlog";

const TERMINAL = new Set(["COMPLETED", "FAILED"]);

// Polls GET /v1/images/{requestId}/status every 2s until a terminal state.
export function usePredictionStatus(requestId, initialStatus = "PENDING") {
  const [status, setStatus] = useState(initialStatus);
  const [predictions, setPredictions] = useState([]);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(Boolean(requestId));
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!requestId) return undefined;
    setIsLoading(true);

    async function poll() {
      try {
        const data = await getStatus(requestId);
        setStatus(data.status);
        setPredictions(data.predictions || []);
        if (data.status === "FAILED") setError(data.errorMessage || "Inference failed");
        if (TERMINAL.has(data.status)) {
          setIsLoading(false);
          clearInterval(intervalRef.current);
        }
      } catch (e) {
        setError(e.message);
        setIsLoading(false);
        clearInterval(intervalRef.current);
      }
    }

    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => clearInterval(intervalRef.current);
  }, [requestId]);

  return { status, predictions, error, isLoading };
}
