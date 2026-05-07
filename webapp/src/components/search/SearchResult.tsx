import { cn, timeAgo, platformLabel } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import type { AskResponse, Session } from "@/types"

function HitDot({ hitType }: { hitType: AskResponse["hit_type"] }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "w-2 h-2 rounded-full",
          hitType === "hit"     && "bg-accent",
          hitType === "partial" && "bg-yellow-400",
          hitType === "miss"    && "bg-text-muted",
        )}
      />
      <span
        className={cn(
          "font-mono text-xs uppercase tracking-wider",
          hitType === "hit"     && "text-accent",
          hitType === "partial" && "text-yellow-400",
          hitType === "miss"    && "text-text-muted",
        )}
      >
        {hitType === "hit"     && "Match found"}
        {hitType === "partial" && "Partial match"}
        {hitType === "miss"    && "Not in library"}
      </span>
    </div>
  )
}

function SessionCard({ session }: { session: Session }) {
  return (
    <div className="border border-border rounded-lg px-4 py-3 bg-surface">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-text-primary leading-snug truncate mb-1">
            {session.title}
          </p>
          {session.summary && (
            <p className="text-xs text-text-secondary line-clamp-2 mb-2">{session.summary}</p>
          )}
          <div className="flex flex-wrap gap-x-2 gap-y-0.5">
            {session.tags.slice(0, 4).map((tag) => (
              <span key={tag} className="font-mono text-xs text-text-muted">
                #{tag}
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <Badge variant="muted">{platformLabel(session.platform)}</Badge>
          <span className="font-mono text-xs text-text-muted">{timeAgo(session.updated_at)}</span>
        </div>
      </div>
    </div>
  )
}

export default function SearchResult({ result }: { result: AskResponse }) {
  const { hit_type, answer, referenced_sessions } = result

  return (
    <div className="w-full max-w-xl mx-auto mt-8 space-y-4">
      <HitDot hitType={hit_type} />
      <Separator />

      {/* Hit: one prominent session */}
      {hit_type === "hit" && referenced_sessions[0] && (
        <SessionCard session={referenced_sessions[0]} />
      )}

      {/* Answer text for partial + miss */}
      {(hit_type === "partial" || hit_type === "miss") && answer && (
        <div
          className={cn(
            "rounded-lg px-4 py-3 text-sm border",
            hit_type === "partial"
              ? "bg-surface border-border text-text-primary"
              : "bg-background border-border text-text-muted",
          )}
        >
          {answer}
        </div>
      )}

      {/* Related sessions for partial */}
      {hit_type === "partial" && referenced_sessions.length > 0 && (
        <div>
          <p className="text-xs text-text-muted font-mono uppercase tracking-wider mb-2">
            Related sessions ({referenced_sessions.length})
          </p>
          <div className="space-y-2">
            {referenced_sessions.map((s) => (
              <SessionCard key={s.id} session={s} />
            ))}
          </div>
        </div>
      )}

      {/* Miss: no sessions */}
      {hit_type === "miss" && (
        <p className="text-xs text-text-muted font-mono text-center py-4">
          No relevant sessions found in library.
        </p>
      )}
    </div>
  )
}
