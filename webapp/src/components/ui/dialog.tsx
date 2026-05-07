"use client"

import * as RadixDialog from "@radix-ui/react-dialog"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

export const Dialog = RadixDialog.Root
export const DialogTrigger = RadixDialog.Trigger
export const DialogClose = RadixDialog.Close

export function DialogContent({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <RadixDialog.Portal>
      <RadixDialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 animate-in fade-in duration-150" />
      <RadixDialog.Content
        className={cn(
          "fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50",
          "bg-surface border border-border rounded-lg shadow-xl",
          "max-w-2xl w-full max-h-[85vh] flex flex-col",
          "animate-in fade-in slide-in-from-bottom-4 duration-200",
          className,
        )}
      >
        {children}
        <RadixDialog.Close className="absolute top-3 right-3 p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-muted transition-colors duration-150">
          <X size={14} />
        </RadixDialog.Close>
      </RadixDialog.Content>
    </RadixDialog.Portal>
  )
}

export function DialogHeader({ children }: { children: React.ReactNode }) {
  return <div className="px-6 py-4 border-b border-border shrink-0">{children}</div>
}

export function DialogTitle({ children }: { children: React.ReactNode }) {
  return (
    <RadixDialog.Title className="text-sm font-semibold text-text-primary leading-tight">
      {children}
    </RadixDialog.Title>
  )
}

export function DialogBody({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("flex-1 overflow-y-auto px-6 py-4", className)}>{children}</div>
}
