"use client"

import { usePathname } from "next/navigation"

function pageTitle(pathname: string): string {
  if (pathname === "/library") return "Library"
  if (pathname === "/search") return "Search"
  if (pathname.startsWith("/topics/")) {
    const slug = pathname.replace("/topics/", "")
    return decodeURIComponent(slug)
  }
  return "llmlib"
}

export default function TopNav() {
  const pathname = usePathname()
  return (
    <header className="h-14 border-b border-border flex items-center px-6 shrink-0 sticky top-0 bg-background/80 backdrop-blur-sm z-10">
      <h1 className="text-sm font-semibold text-text-primary tracking-tight">
        {pageTitle(pathname)}
      </h1>
    </header>
  )
}
