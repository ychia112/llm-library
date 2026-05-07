import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function timeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const secs = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (secs < 60) return "just now"
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months}mo ago`
  return `${Math.floor(months / 12)}y ago`
}

export function questionTypeColor(type: string): string {
  switch (type.toLowerCase()) {
    case "debug":    return "bg-blue-500"
    case "research": return "bg-green-500"
    case "howto":    return "bg-orange-500"
    case "design":   return "bg-purple-500"
    default:         return "bg-zinc-500"
  }
}

export function questionTypeBadgeColor(type: string): string {
  switch (type.toLowerCase()) {
    case "debug":    return "text-blue-400 bg-blue-400/10 border-blue-400/20"
    case "research": return "text-green-400 bg-green-400/10 border-green-400/20"
    case "howto":    return "text-orange-400 bg-orange-400/10 border-orange-400/20"
    case "design":   return "text-purple-400 bg-purple-400/10 border-purple-400/20"
    default:         return "text-text-muted bg-muted/30 border-border"
  }
}

export function platformLabel(platform: string): string {
  return platform.toUpperCase()
}
