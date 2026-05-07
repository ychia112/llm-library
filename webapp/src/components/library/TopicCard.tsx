"use client"

import { useRouter } from "next/navigation"
import { cn, questionTypeColor } from "@/lib/utils"
import type { TopicSummary } from "@/types"

export default function TopicCard({ topic }: { topic: TopicSummary }) {
  const router = useRouter()
  const total = topic.by_question_type.reduce((s, q) => s + q.count, 0)
  const sorted = [...topic.by_question_type].sort((a, b) => b.count - a.count)

  return (
    <button
      onClick={() => router.push(`/topics/${encodeURIComponent(topic.topic)}`)}
      className={cn(
        "w-full text-left bg-surface border border-border rounded-lg p-4 transition-colors duration-150",
        "hover:border-accent focus:outline-none focus:border-accent",
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="font-semibold text-text-primary tracking-tight text-sm leading-snug">
          {topic.topic}
        </h3>
        <span className="font-mono text-xs text-text-muted shrink-0 bg-muted/40 px-2 py-0.5 rounded-full">
          {topic.count}
        </span>
      </div>

      {/* Key entities — lime pills */}
      {topic.top_entities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {topic.top_entities.slice(0, 4).map((e) => (
            <span
              key={e}
              className="text-xs px-2 py-0.5 rounded-full bg-accent-dim text-accent border border-accent/20 font-mono"
            >
              {e}
            </span>
          ))}
        </div>
      )}

      {/* Top tags */}
      {topic.top_tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {topic.top_tags.map((tag) => (
            <span key={tag} className="font-mono text-xs text-text-muted">
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Question type bar */}
      {total > 0 && (
        <div className="flex gap-0.5 rounded overflow-hidden h-1.5 mt-1">
          {sorted.map((qt) => (
            <div
              key={qt.question_type}
              className={cn("h-full opacity-70", questionTypeColor(qt.question_type))}
              style={{ width: `${(qt.count / total) * 100}%` }}
              title={`${qt.question_type}: ${qt.count}`}
            />
          ))}
        </div>
      )}
    </button>
  )
}
