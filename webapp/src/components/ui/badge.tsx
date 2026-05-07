import { cn } from "@/lib/utils"
import type { HTMLAttributes } from "react"

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "accent" | "muted"
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 font-mono text-xs border transition-colors duration-150",
        variant === "default" && "border-border text-text-secondary",
        variant === "accent"  && "border-accent/30 bg-accent-dim text-accent",
        variant === "muted"   && "border-transparent bg-muted/40 text-text-muted",
        className,
      )}
      {...props}
    />
  )
}
