import { cn } from "@/lib/utils"
import { type InputHTMLAttributes, forwardRef } from "react"

const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted",
        "focus:outline-none focus:border-accent transition-colors duration-150",
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = "Input"

export { Input }
