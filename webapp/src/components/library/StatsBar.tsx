"use client"

import { useState, useEffect, useCallback } from "react"
import { RefreshCw, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { startRetopicize, fetchRetopicizeStatus, fetchIngestStatus } from "@/lib/api"
import { useTopics } from "@/lib/topics-context"
import type { LibraryOverview, RetopicizeStatus, IngestStatus } from "@/types"

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-text-muted text-xs uppercase tracking-wider font-mono">{label}</span>
      <span className="font-mono text-sm text-text-primary font-medium">{value}</span>
    </div>
  )
}

export default function StatsBar({ overview }: { overview: LibraryOverview | null }) {
  const { refresh: refreshTopics } = useTopics()
  const [retopStatus, setRetopStatus] = useState<RetopicizeStatus | null>(null)
  const [ingestStatus, setIngestStatus] = useState<IngestStatus | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const pollStatus = useCallback(async () => {
    try {
      const [retop, ingest] = await Promise.all([
        fetchRetopicizeStatus(),
        fetchIngestStatus(),
      ])
      setRetopStatus(retop)
      setIngestStatus(ingest)
    } catch {
      // server may be offline
    }
  }, [])

  // Initial status fetch
  useEffect(() => {
    pollStatus()
  }, [pollStatus])

  // Poll while retopicize is running or starting
  useEffect(() => {
    if (!retopStatus?.running && !isStarting) {
      if (retopStatus?.done) refreshTopics()
      return
    }
    const id = setInterval(pollStatus, 2000)
    return () => clearInterval(id)
  }, [retopStatus?.running, retopStatus?.done, isStarting, pollStatus, refreshTopics])

  const handleRetopicize = async () => {
    if (isStarting) return
    setIsStarting(true)
    setError(null)
    try {
      await startRetopicize(8)
      setIsStarting(false)
    } catch (e) {
      setError("Failed to start retopicize")
      console.error(e)
      setIsStarting(false)
    }
  }

  const isRetopRunning = retopStatus?.running ?? false
  const isIngestRunning = ingestStatus?.running ?? false
  const platforms = overview?.by_platform.map((p) => p.platform).join(" · ") || "—"

  return (
    <div className="flex items-center gap-5 mb-6 flex-wrap">
      {overview ? (
        <>
          <Stat label="sessions" value={overview.total_sessions} />
          <Separator className="h-3 w-px bg-border hidden sm:block" />
          <Stat label="topics" value={overview.by_topic.length} />
          <Separator className="h-3 w-px bg-border hidden sm:block" />
          <Stat label="platforms" value={platforms} />
        </>
      ) : (
        <span className="font-mono text-xs text-text-muted">Loading…</span>
      )}

      <div className="ml-auto flex items-center gap-2">
        {isRetopRunning && (
          <span className="font-mono text-xs text-text-muted">
            Clustering{retopStatus?.total ? ` ${retopStatus.total} sessions…` : "…"}
          </span>
        )}
        {retopStatus?.done && !isRetopRunning && retopStatus.clusters_found > 0 && (
          <span className="font-mono text-xs text-accent">
            {retopStatus.clusters_found} clusters
          </span>
        )}
        {error && <span className="text-xs text-red-400">{error}</span>}
        <Button
          variant="outline"
          size="sm"
          onClick={handleRetopicize}
          disabled={isRetopRunning || isIngestRunning || isStarting}
          className="gap-1.5"
        >
          {isRetopRunning || isStarting ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <RefreshCw size={12} />
          )}
          Retopicize
        </Button>
      </div>
    </div>
  )
}
