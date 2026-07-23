// Thin API client. Base URL and key come from Vite env vars.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";
const API_KEY = import.meta.env.VITE_API_KEY || "dev-key-12345";

function headers(extra = {}) {
  return { "X-API-Key": API_KEY, ...extra };
}

export async function uploadImage(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/v1/images/upload`, {
    method: "POST",
    headers: headers(),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function getStatus(requestId) {
  const res = await fetch(`${BASE_URL}/v1/images/${requestId}/status`, {
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Status check failed (${res.status})`);
  return res.json();
}

export async function listImages(limit = 20, status) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set("status", status);
  const res = await fetch(`${BASE_URL}/v1/images?${params}`, { headers: headers() });
  if (!res.ok) throw new Error(`List failed (${res.status})`);
  return res.json();
}
