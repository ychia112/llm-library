"use client"

import { useState } from "react"
import { ChevronDown, ExternalLink } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { cn, timeAgo, questionTypeBadgeColor, platformLabel } from "@/lib/utils"
import { fetchSession } from "@/lib/api"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogBody,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import type { Session, SessionDetail } from "@/types"

function MessageBubble({ role, content }: { role: string; content: string }) {
  const isUser = role === "user" || role === "human"
  const parts = content.split(/(```[\s\S]*?```)/g)

  return (
    <div className={cn("flex mb-3", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2 text-sm",
          isUser
            ? "bg-muted text-text-primary"
            : "bg-surface border border-border text-text-primary",
        )}
      >
        {parts.map((part, i) =>
          part.startsWith("```") ? (
            <pre
              key={i}
              className="bg-background font-mono text-xs p-2 rounded mt-1 mb-1 overflow-x-auto whitespace-pre-wrap"
            >
              {part.replace(/^```\w*\n?/, "").replace(/```$/, "")}
            </pre>
          ) : (
            <span key={i} className="whitespace-pre-wrap">{part}</span>
          ),
        )}
      </div>
    </div>
  )
}

function ConversationDialog({
  open,
  onOpenChange,
  session,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  session: SessionDetail | null
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{session?.title}</DialogTitle>
          {session && (
            <div className="flex gap-2 mt-1">
              <Badge variant="muted">{platformLabel(session.platform)}</Badge>
              {session.question_type && (
                <span
                  className={cn(
                    "inline-flex items-center rounded-full px-2 py-0.5 font-mono text-xs border",
                    questionTypeBadgeColor(session.question_type),
                  )}
                >
                  {session.question_type}
                </span>
              )}
            </div>
          )}
        </DialogHeader>
        <DialogBody>
          {session?.messages.map((msg, i) => (
            <MessageBubble key={i} role={msg.role} content={msg.content} />
          ))}
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}

export default function SessionRow({ session }: { session: Session }) {
  const [expanded, setExpanded] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [fullSession, setFullSession] = useState<SessionDetail | null>(null)
  const [loadingFull, setLoadingFull] = useState(false)

  const openDialog = async () => {
    setDialogOpen(true)
    if (fullSession) return
    setLoadingFull(true)
    try {
      const data = await fetchSession(session.id)
      setFullSession(data)
    } catch {
      // keep null
    } finally {
      setLoadingFull(false)
    }
  }

  return (
    <>
      <div className="border border-border rounded-lg overflow-hidden">
        <button
          className={cn(
            "w-full text-left px-4 py-3 flex items-start gap-3 transition-colors duration-150",
            expanded ? "bg-surface" : "bg-surface hover:bg-muted/30",
          )}
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-medium text-text-primary leading-snug truncate">
                {session.title}
              </span>
            </div>
            {session.summary && (
              <p className="text-xs text-text-secondary line-clamp-1 mb-2">{session.summary}</p>
            )}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
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
            <ChevronDown
              size={13}
              className={cn(
                "text-text-muted transition-transform duration-150",
                expanded && "rotate-180",
              )}
            />
          </div>
        </button>

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.18, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="px-4 py-3 border-t border-border bg-background/60 space-y-3">
                {session.summary && (
                  <div>
                    <p className="text-xs text-text-muted uppercase tracking-wider font-mono mb-1">Summary</p>
                    <p className="text-sm text-text-secondary">{session.summary}</p>
                  </div>
                )}

                {session.key_entities.length > 0 && (
                  <div>
                    <p className="text-xs text-text-muted uppercase tracking-wider font-mono mb-1.5">Entities</p>
                    <div className="flex flex-wrap gap-1.5">
                      {session.key_entities.map((e) => (
                        <span
                          key={e}
                          className="text-xs px-2 py-0.5 rounded-full bg-accent-dim text-accent border border-accent/20 font-mono"
                        >
                          {e}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between pt-1">
                  {session.sub_topic && (
                    <span className="text-xs text-text-muted font-mono">
                      {session.topic} / {session.sub_topic}
                    </span>
                  )}
                  <button
                    onClick={openDialog}
                    className="ml-auto flex items-center gap-1.5 text-xs text-accent hover:text-lime-300 transition-colors duration-150 font-medium"
                  >
                    View full conversation
                    <ExternalLink size={11} />
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <ConversationDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        session={loadingFull ? null : fullSession}
      />
    </>
  )
}
