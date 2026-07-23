import { useRef, useState } from "react";

export default function UploadForm({ onUpload, disabled }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);

  function pick(f) {
    if (f && f.type.startsWith("image/")) setFile(f);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    pick(e.dataTransfer.files?.[0]);
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition
          ${dragging ? "border-indigo-500 bg-indigo-50" : "border-gray-300 hover:border-gray-400"}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0])}
        />
        {file ? (
          <p className="text-gray-700">
            <span className="font-medium">{file.name}</span>{" "}
            <span className="text-gray-400">({(file.size / 1024).toFixed(1)} KB)</span>
          </p>
        ) : (
          <p className="text-gray-500">Drag & drop an image here, or click to browse</p>
        )}
      </div>

      <button
        disabled={!file || disabled}
        onClick={() => onUpload(file)}
        className="w-full rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white
          disabled:cursor-not-allowed disabled:bg-gray-300 hover:bg-indigo-700"
      >
        {disabled ? "Uploading…" : "Classify image"}
      </button>
    </div>
  );
}
