"use client"

import { useState, type FormEvent } from "react"
import { ArrowRight, Loader2 } from "lucide-react"
import { Input } from "@/components/ui/input"

interface Props {
  onSearch: (query: string) => void
  isLoading: boolean
  recentSearches: string[]
  onRecentClick: (q: string) => void
}

export default function SearchInput({
  onSearch,
  isLoading,
  recentSearches,
  onRecentClick,
}: Props) {
  const [value, setValue] = useState("")

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const q = value.trim()
    if (q) onSearch(q)
  }

  return (
    <div className="w-full max-w-xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask your library anything…"
          className="pr-10 py-3 text-base h-12"
          autoFocus
        />
        <button
          type="submit"
          disabled={!value.trim() || isLoading}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-accent disabled:opacity-30 transition-colors duration-150"
        >
          {isLoading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <ArrowRight size={16} />
          )}
        </button>
      </form>

      {recentSearches.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <span className="text-xs text-text-muted font-mono">Recent:</span>
          {recentSearches.map((q) => (
            <button
              key={q}
              onClick={() => onRecentClick(q)}
              className="text-xs text-text-secondary hover:text-text-primary transition-colors duration-150 font-mono border border-border rounded-full px-2.5 py-0.5 hover:border-muted"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
