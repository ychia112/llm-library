export interface Message {
  role: string
  content: string
  timestamp: string | null
}

export interface Session {
  id: string
  platform: string
  title: string
  topic: string | null
  sub_topic: string | null
  tags: string[]
  key_entities: string[]
  question_type: string | null
  summary: string | null
  created_at: string
  updated_at: string
}

export interface SessionDetail extends Session {
  messages: Message[]
}

export interface QuestionTypeStat {
  question_type: string
  count: number
}

export interface TopicSummary {
  topic: string
  count: number
  top_tags: string[]
  by_question_type: QuestionTypeStat[]
  top_entities: string[]
}

export interface LibraryOverview {
  total_sessions: number
  by_topic: TopicSummary[]
  by_question_type: QuestionTypeStat[]
  by_platform: { platform: string; count: number }[]
  top_tags: { tag: string; count: number }[]
  recent_sessions: Session[]
}

export interface AskResponse {
  answer: string
  hit_type: "hit" | "partial" | "miss"
  referenced_sessions: Session[]
  tokens_used: number
}

export interface PaginatedSessions {
  sessions: Session[]
  total: number
}

export interface IngestStatus {
  running: boolean
  total: number
  processed: number
  current_title: string
  error: string | null
}

export interface RetopicizeStatus {
  running: boolean
  done: boolean
  clusters_found: number
  total: number
  error: string | null
}
