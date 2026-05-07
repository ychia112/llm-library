"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Library, Search, type LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { useTopics } from "@/lib/topics-context"
import { Skeleton } from "@/components/ui/skeleton"

function NavItem({
  href,
  icon: Icon,
  label,
  active,
}: {
  href: string
  icon: LucideIcon
  label: string
  active: boolean
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-sm transition-colors duration-150",
        active
          ? "bg-muted text-text-primary"
          : "text-text-secondary hover:text-text-primary hover:bg-muted/50",
      )}
    >
      <Icon size={15} />
      {label}
    </Link>
  )
}

export default function Sidebar() {
  const pathname = usePathname()
  const { topics, overview, isLoading } = useTopics()

  return (
    <div
      className="fixed left-0 top-0 h-screen flex flex-col bg-background border-r border-border"
      style={{ width: 240 }}
    >
      {/* Brand */}
      <div className="h-14 flex items-center px-4 border-b border-border shrink-0">
        <span className="text-accent font-semibold text-lg">◈</span>
        <span className="ml-2 font-semibold text-text-primary tracking-tight">llmlib</span>
      </div>

      {/* Primary nav */}
      <nav className="p-2 space-y-0.5 shrink-0">
        <NavItem href="/library" icon={Library} label="Library" active={pathname === "/library"} />
        <NavItem href="/search" icon={Search} label="Search" active={pathname === "/search"} />
      </nav>

      <div className="px-4 pt-3 pb-2 shrink-0">
        <div className="h-px bg-border mb-3" />
        <p className="text-text-muted text-xs uppercase tracking-widest font-mono">Topics</p>
      </div>

      {/* Topics list */}
      <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-6 mx-1 rounded-md" />
          ))
        ) : (
          topics.map((t) => {
            const href = `/topics/${encodeURIComponent(t.topic)}`
            const active = pathname === href || pathname.startsWith(href + "/")
            return (
              <Link
                key={t.topic}
                href={href}
                className={cn(
                  "flex items-center justify-between px-2.5 py-1.5 rounded-md text-sm transition-colors duration-150 border-l-2",
                  active
                    ? "border-accent text-text-primary bg-accent-dim"
                    : "border-transparent text-text-secondary hover:text-text-primary hover:bg-muted/50",
                )}
              >
                <span className="truncate">{t.topic}</span>
                <span className="font-mono text-xs text-text-muted shrink-0 ml-1">{t.count}</span>
              </Link>
            )
          })
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border shrink-0">
        <p className="font-mono text-xs text-text-muted">
          {overview?.total_sessions ?? 0} sessions
        </p>
      </div>
    </div>
  )
}
