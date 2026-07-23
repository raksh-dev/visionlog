import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listImages } from "../api/visionlog";

const BADGE = {
  PENDING: "bg-yellow-100 text-yellow-800",
  PROCESSING: "bg-blue-100 text-blue-800",
  COMPLETED: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",
};

export default function Dashboard() {
  const [items, setItems] = useState([]);
  const [expanded, setExpanded] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const data = await listImages(20);
      setItems(data.items || []);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Recent predictions</h1>
        <div className="flex gap-2">
          <button onClick={load} className="rounded-lg border px-3 py-1.5 text-sm hover:bg-gray-50">
            Refresh
          </button>
          <Link to="/" className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm text-white">
            Upload
          </Link>
        </div>
      </div>

      {error && <p className="text-red-600">{error}</p>}
      {loading && <p className="text-gray-500">Loading…</p>}

      <div className="overflow-hidden rounded-xl border border-gray-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="px-4 py-2">File</th>
              <th className="px-4 py-2">Top prediction</th>
              <th className="px-4 py-2">Confidence</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => {
              const top = it.predictions?.[0];
              const open = expanded === it.requestId;
              return (
                <Fragment key={it.requestId}>
                  <tr
                    onClick={() => setExpanded(open ? null : it.requestId)}
                    className="cursor-pointer border-t hover:bg-gray-50"
                  >
                    <td className="px-4 py-2">{it.fileName || "—"}</td>
                    <td className="px-4 py-2">{top ? top.label : "—"}</td>
                    <td className="px-4 py-2">{top ? `${(top.confidence * 100).toFixed(1)}%` : "—"}</td>
                    <td className="px-4 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${BADGE[it.status] || ""}`}>
                        {it.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-400">
                      {it.uploadedAt ? new Date(it.uploadedAt).toLocaleString() : "—"}
                    </td>
                  </tr>
                  {open && top && (
                    <tr className="bg-gray-50">
                      <td colSpan={5} className="px-4 py-2">
                        <ul className="space-y-1">
                          {it.predictions.map((p) => (
                            <li key={p.rank} className="text-gray-600">
                              #{p.rank} {p.label} — {(p.confidence * 100).toFixed(1)}%
                            </li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
