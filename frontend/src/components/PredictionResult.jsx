export default function PredictionResult({ predictions, previewUrl }) {
  return (
    <div className="mt-4 grid gap-4 md:grid-cols-2">
      {previewUrl && (
        <img
          src={previewUrl}
          alt="uploaded preview"
          className="max-h-56 w-full rounded-lg object-contain bg-gray-50"
        />
      )}
      <div className="space-y-2">
        {predictions.map((p) => (
          <div key={p.rank}>
            <div className="flex justify-between text-sm">
              <span className="font-medium text-gray-700">
                #{p.rank} {p.label}
              </span>
              <span className="text-gray-500">{(p.confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="h-2 w-full rounded bg-gray-100">
              <div
                className="h-2 rounded bg-indigo-500"
                style={{ width: `${Math.max(2, p.confidence * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
