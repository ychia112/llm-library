"use client"

import { useState, useEffect, useCallback } from "react"
import { askQuestion } from "@/lib/api"
import SearchInput from "@/components/search/SearchInput"
import SearchResult from "@/components/search/SearchResult"
import { Skeleton } from "@/components/ui/skeleton"
import type { AskResponse } from "@/types"

const RECENT_KEY = "llmlib_recent_searches"
const MAX_RECENT = 5

function loadRecent(): string[] {
  if (typeof window === "undefined") return []
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]")
  } catch {
    return []
  }
}

function saveRecent(query: string, prev: string[]): string[] {
  const next = [query, ...prev.filter((q) => q !== query)].slice(0, MAX_RECENT)
  localStorage.setItem(RECENT_KEY, JSON.stringify(next))
  return next
}

export default function SearchPageClient() {
  const [recentSearches, setRecentSearches] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<AskResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setRecentSearches(loadRecent())
  }, [])

  const handleSearch = useCallback(async (query: string) => {
    setIsLoading(true)
    setResult(null)
    setError(null)
    setRecentSearches((prev) => saveRecent(query, prev))

    try {
      const data = await askQuestion(query)
      setResult(data)
    } catch (e) {
      setError("Search failed. Make sure the llmlib server is running.")
      console.error(e)
    } finally {
      setIsLoading(false)
    }
  }, [])

  return (
    <div className="max-w-2xl mx-auto pt-8">
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-text-primary tracking-tight mb-1">Ask</h1>
        <p className="text-sm text-text-muted font-mono">Query your conversation library</p>
      </div>

      <SearchInput
        onSearch={handleSearch}
        isLoading={isLoading}
        recentSearches={recentSearches}
        onRecentClick={handleSearch}
      />

      {isLoading && (
        <div className="mt-8 space-y-3 w-full max-w-xl mx-auto">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-px w-full" />
          <Skeleton className="h-24 rounded-lg" />
        </div>
      )}

      {error && (
        <p className="mt-8 text-sm text-red-400 text-center font-mono">{error}</p>
      )}

      {!isLoading && result && <SearchResult result={result} />}

      {!isLoading && !result && !error && (
        <div className="mt-16 text-center">
          <p className="text-xs text-text-muted font-mono uppercase tracking-wider mb-2">
            Example queries
          </p>
          <div className="flex flex-col gap-2 items-center">
            {[
              "How did I implement authentication?",
              "What debugging tools did I use last month?",
              "Explain the vector search approach",
            ].map((q) => (
              <button
                key={q}
                onClick={() => handleSearch(q)}
                className="text-sm text-text-secondary hover:text-text-primary font-mono transition-colors duration-150"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
