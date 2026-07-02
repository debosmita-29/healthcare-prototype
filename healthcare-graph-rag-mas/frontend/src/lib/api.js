const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function createBriefing(payload) {
  const response = await fetch(`${API_BASE_URL}/api/briefings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export async function getBriefing(runId) {
  const response = await fetch(`${API_BASE_URL}/api/briefings/${runId}`);
  if (!response.ok) {
    throw new Error(`Run lookup failed: ${response.status}`);
  }
  return response.json();
}

export function openEventStream(runId, onEvent) {
  const source = new EventSource(`${API_BASE_URL}/api/briefings/${runId}/events`);
  source.onmessage = (message) => onEvent(JSON.parse(message.data));
  source.onerror = () => source.close();
  return source;
}

