"use client"

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react"
import { fetchTopics, fetchOverview } from "./api"
import type { TopicSummary, LibraryOverview } from "@/types"

interface TopicsContextValue {
  topics: TopicSummary[]
  overview: LibraryOverview | null
  isLoading: boolean
  refresh: () => void
}

const TopicsContext = createContext<TopicsContextValue>({
  topics: [],
  overview: null,
  isLoading: true,
  refresh: () => {},
})

export function TopicsProvider({ children }: { children: ReactNode }) {
  const [topics, setTopics] = useState<TopicSummary[]>([])
  const [overview, setOverview] = useState<LibraryOverview | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    try {
      const [t, o] = await Promise.all([fetchTopics(), fetchOverview()])
      setTopics(t)
      setOverview(o)
    } catch (err) {
      console.error("Failed to load library data:", err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <TopicsContext.Provider value={{ topics, overview, isLoading, refresh }}>
      {children}
    </TopicsContext.Provider>
  )
}

export const useTopics = () => useContext(TopicsContext)
