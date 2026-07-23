import { useState } from "react";
import { Link } from "react-router-dom";
import UploadForm from "./components/UploadForm";
import StatusPoller from "./components/StatusPoller";
import { uploadImage } from "./api/visionlog";

export default function App() {
  const [requestId, setRequestId] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  async function handleUpload(file) {
    setUploading(true);
    setError(null);
    setPreviewUrl(URL.createObjectURL(file));
    try {
      const res = await uploadImage(file);
      setRequestId(res.requestId);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-800">VisionLog</h1>
        <Link to="/dashboard" className="text-sm text-indigo-600 hover:underline">
          Dashboard →
        </Link>
      </header>

      <p className="mb-4 text-gray-500">
        Upload an image and VisionLog will classify it using MobileNetV2 on Vertex AI.
      </p>

      <UploadForm onUpload={handleUpload} disabled={uploading} />
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {requestId && <StatusPoller requestId={requestId} previewUrl={previewUrl} />}
    </div>
  );
}
