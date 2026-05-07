import type { Metadata } from "next"
import { GeistSans } from "geist/font/sans"
import { GeistMono } from "geist/font/mono"
import "./globals.css"
import { TopicsProvider } from "@/lib/topics-context"
import Sidebar from "@/components/layout/Sidebar"
import TopNav from "@/components/layout/TopNav"

export const metadata: Metadata = {
  title: "llmlib — Knowledge Library",
  description: "Your personal LLM conversation knowledge base",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable}`}
    >
      <body className="bg-background text-text-primary antialiased min-h-screen">
        <TopicsProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex-1 flex flex-col min-h-screen" style={{ marginLeft: 240 }}>
              <TopNav />
              <main className="flex-1 px-6 py-6 w-full max-w-[1280px] mx-auto">
                {children}
              </main>
            </div>
          </div>
        </TopicsProvider>
      </body>
    </html>
  )
}
