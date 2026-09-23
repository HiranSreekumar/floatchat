const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export async function checkHealth() {
  const res = await fetch(`${BACKEND_URL}/api/health`);
  if (!res.ok) throw new Error(`Backend unhealthy (${res.status})`);
  return res.json();
}

export async function sendChatMessage(message) {
  const res = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  const data = await res.json();
  if (!res.ok) {
    const err = new Error(data.detail || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

export { BACKEND_URL };
