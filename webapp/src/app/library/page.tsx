"use client"

import { useTopics } from "@/lib/topics-context"
import StatsBar from "@/components/library/StatsBar"
import TopicGrid from "@/components/library/TopicGrid"
import { timeAgo, platformLabel } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"

export default function LibraryPage() {
  const { topics, overview, isLoading } = useTopics()

  return (
    <div>
      <StatsBar overview={overview} />
      <TopicGrid topics={topics} isLoading={isLoading} />

      {/* Recent sessions strip */}
      {!isLoading && overview?.recent_sessions && overview.recent_sessions.length > 0 && (
        <div className="mt-8">
          <p className="text-xs text-text-muted font-mono uppercase tracking-wider mb-3">
            Recent
          </p>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {overview.recent_sessions.map((s) => (
              <div
                key={s.id}
                className="shrink-0 w-56 bg-surface border border-border rounded-lg px-3 py-2.5"
              >
                <p className="text-xs font-medium text-text-primary leading-snug line-clamp-2 mb-2">
                  {s.title}
                </p>
                <div className="flex items-center justify-between">
                  <Badge variant="muted">{platformLabel(s.platform)}</Badge>
                  <span className="font-mono text-xs text-text-muted">{timeAgo(s.updated_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
