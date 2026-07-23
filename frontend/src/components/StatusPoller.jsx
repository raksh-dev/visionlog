import { usePredictionStatus } from "../hooks/usePredictionStatus";
import PredictionResult from "./PredictionResult";

const BADGE = {
  PENDING: "bg-yellow-100 text-yellow-800",
  PROCESSING: "bg-blue-100 text-blue-800",
  COMPLETED: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",
};

export default function StatusPoller({ requestId, previewUrl }) {
  const { status, predictions, error, isLoading } = usePredictionStatus(requestId);

  return (
    <div className="mt-6 rounded-xl border border-gray-200 p-5">
      <div className="flex items-center gap-3">
        <span className={`rounded-full px-3 py-1 text-sm font-medium ${BADGE[status] || ""}`}>
          {status}
        </span>
        {isLoading && (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-indigo-600" />
        )}
        <code className="ml-auto text-xs text-gray-400">{requestId}</code>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {status === "COMPLETED" && (
        <PredictionResult predictions={predictions} previewUrl={previewUrl} />
      )}
    </div>
  );
}
