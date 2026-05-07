import { cn } from "@/lib/utils"
import { type ButtonHTMLAttributes, forwardRef } from "react"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "outline"
  size?: "sm" | "md" | "icon"
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "ghost", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 font-medium transition-colors duration-150 rounded-lg disabled:opacity-40 disabled:pointer-events-none",
          variant === "primary" && "bg-accent text-black hover:bg-lime-300 px-4 py-2 text-sm",
          variant === "ghost" && "text-text-secondary hover:text-text-primary hover:bg-muted px-3 py-1.5 text-sm",
          variant === "outline" && "border border-border text-text-secondary hover:text-text-primary hover:border-accent px-3 py-1.5 text-sm",
          size === "sm" && "px-2.5 py-1 text-xs",
          size === "icon" && "p-1.5 w-8 h-8",
          className,
        )}
        {...props}
      />
    )
  },
)
Button.displayName = "Button"

export { Button }
