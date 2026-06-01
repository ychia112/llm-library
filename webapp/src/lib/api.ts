import type {
  LibraryOverview,
  TopicSummary,
  PaginatedSessions,
  SessionDetail,
  AskResponse,
  IngestStatus,
  RetopicizeStatus,
} from "@/types"

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765"

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json()
}

export function fetchOverview(): Promise<LibraryOverview> {
  return api("/library/overview")
}

export function fetchTopics(): Promise<TopicSummary[]> {
  return api("/library/topics")
}

export function fetchSessions(params: {
  topic?: string
  tag?: string
  platform?: string
  question_type?: string
  limit?: number
  offset?: number
}): Promise<PaginatedSessions> {
  const q = new URLSearchParams()
  if (params.topic)         q.set("topic", params.topic)
  if (params.tag)           q.set("tag", params.tag)
  if (params.platform)      q.set("platform", params.platform)
  if (params.question_type) q.set("question_type", params.question_type)
  if (params.limit != null) q.set("limit", String(params.limit))
  if (params.offset != null) q.set("offset", String(params.offset))
  return api(`/sessions?${q}`)
}

export function fetchSession(id: string): Promise<SessionDetail> {
  return api(`/sessions/${encodeURIComponent(id)}`)
}

export function askQuestion(
  query: string,
  provider = "ollama",
): Promise<AskResponse> {
  return api("/ask", {
    method: "POST",
    body: JSON.stringify({ query, provider }),
  })
}

export function startIngest(
  filePath: string,
  platform: string,
  provider: string,
): Promise<void> {
  return api("/ingest", {
    method: "POST",
    body: JSON.stringify({ file_path: filePath, platform, provider }),
  })
}

export function fetchIngestStatus(): Promise<IngestStatus> {
  return api("/ingest/status")
}

export function startRetopicize(targetTopics = 8): Promise<void> {
  return api("/library/retopicize", {
    method: "POST",
    body: JSON.stringify({ target_topics: targetTopics }),
  })
}

export function fetchRetopicizeStatus(): Promise<RetopicizeStatus> {
  return api("/library/retopicize/status")
}
