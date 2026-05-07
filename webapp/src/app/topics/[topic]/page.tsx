"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft } from "lucide-react"
import { fetchSessions } from "@/lib/api"
import { cn, questionTypeColor, questionTypeBadgeColor } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import SessionRow from "@/components/library/SessionRow"
import { useTopics } from "@/lib/topics-context"
import type { Session } from "@/types"

export default function TopicDetailPage() {
  const params = useParams()
  const router = useRouter()
  const topic = decodeURIComponent(params.topic as string)
  const { topics } = useTopics()

  const [sessions, setSessions] = useState<Session[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeSubTopic, setActiveSubTopic] = useState<string | null>(null)
  const [activeQType, setActiveQType] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      setIsLoading(true)
      setError(null)
      try {
        const data = await fetchSessions({ topic, limit: 200 })
        setSessions(data.sessions)
      } catch (e) {
        setError("Failed to load sessions")
        console.error(e)
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [topic])

  // Derive sub-topics from sessions
  const subTopics = Array.from(
    new Set(sessions.map((s) => s.sub_topic).filter(Boolean) as string[]),
  ).sort()

  // Derive question types + totals from sessions
  const qTypeMap: Record<string, number> = {}
  sessions.forEach((s) => {
    if (s.question_type) qTypeMap[s.question_type] = (qTypeMap[s.question_type] || 0) + 1
  })
  const qTypes = Object.entries(qTypeMap).sort((a, b) => b[1] - a[1])
  const qTotal = sessions.length

  // Top tags from the matched topic summary
  const topicSummary = topics.find((t) => t.topic === topic)
  const topTags = topicSummary?.top_tags ?? []

  // Filtered sessions
  const filtered = sessions.filter((s) => {
    if (activeSubTopic && s.sub_topic !== activeSubTopic) return false
    if (activeQType && s.question_type !== activeQType) return false
    return true
  })

  return (
    <div className="max-w-2xl">
      {/* Back + header */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-text-muted hover:text-text-primary text-xs font-mono mb-4 transition-colors duration-150"
      >
        <ArrowLeft size={12} />
        Back
      </button>

      <div className="mb-5">
        <div className="flex items-baseline gap-3 mb-2">
          <h1 className="text-xl font-semibold text-text-primary tracking-tight">{topic}</h1>
          <span className="font-mono text-sm text-text-muted">{sessions.length} sessions</span>
        </div>

        {/* Top tags */}
        {topTags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {topTags.map((tag) => (
              <span key={tag} className="font-mono text-xs text-text-muted">#{tag}</span>
            ))}
          </div>
        )}

        {/* Question type distribution bar */}
        {qTotal > 0 && (
          <div className="flex gap-0.5 rounded overflow-hidden h-2 mb-3">
            {qTypes.map(([type, count]) => (
              <div
                key={type}
                className={cn("h-full cursor-pointer opacity-70 hover:opacity-100 transition-opacity", questionTypeColor(type))}
                style={{ width: `${(count / qTotal) * 100}%` }}
                title={`${type}: ${count}`}
                onClick={() => setActiveQType(activeQType === type ? null : type)}
              />
            ))}
          </div>
        )}

        {/* Question type legend */}
        {qTypes.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-1">
            {qTypes.map(([type, count]) => (
              <span
                key={type}
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 font-mono text-xs border cursor-pointer transition-colors duration-150",
                  questionTypeBadgeColor(type),
                  activeQType === type && "ring-1 ring-offset-0 ring-current",
                )}
                onClick={() => setActiveQType(activeQType === type ? null : type)}
              >
                {type} · {count}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Sub-topic filter pills */}
      {subTopics.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-5">
          <button
            onClick={() => setActiveSubTopic(null)}
            className={cn(
              "px-3 py-1 rounded-full text-xs font-mono border transition-colors duration-150",
              activeSubTopic === null
                ? "bg-accent-dim text-accent border-accent/30"
                : "border-border text-text-secondary hover:text-text-primary hover:border-muted",
            )}
          >
            All
          </button>
          {subTopics.map((sub) => {
            const count = sessions.filter((s) => s.sub_topic === sub).length
            return (
              <button
                key={sub}
                onClick={() => setActiveSubTopic(activeSubTopic === sub ? null : sub)}
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-mono border transition-colors duration-150",
                  activeSubTopic === sub
                    ? "bg-accent-dim text-accent border-accent/30"
                    : "border-border text-text-secondary hover:text-text-primary hover:border-muted",
                )}
              >
                {sub} · {count}
              </button>
            )
          })}
        </div>
      )}

      <Separator className="mb-4" />

      {/* Session list */}
      <div>
        <p className="text-xs text-text-muted font-mono uppercase tracking-wider mb-3">
          Sessions ({filtered.length})
        </p>

        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))}
          </div>
        ) : error ? (
          <p className="text-sm text-red-400">{error}</p>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-text-muted font-mono">No sessions match the selected filters.</p>
        ) : (
          <div className="space-y-2">
            {filtered.map((s) => (
              <SessionRow key={s.id} session={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
