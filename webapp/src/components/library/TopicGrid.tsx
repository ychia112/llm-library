import TopicCard from "./TopicCard"
import { Skeleton } from "@/components/ui/skeleton"
import type { TopicSummary } from "@/types"

export default function TopicGrid({
  topics,
  isLoading,
}: {
  topics: TopicSummary[]
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-36 rounded-lg" />
        ))}
      </div>
    )
  }

  if (topics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-text-muted text-sm">No topics yet.</p>
        <p className="text-text-muted text-xs mt-1">
          Run <code className="font-mono text-accent">llmlib ingest</code> to populate your library.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {topics.map((t) => (
        <TopicCard key={t.topic} topic={t} />
      ))}
    </div>
  )
}
