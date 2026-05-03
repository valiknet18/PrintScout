import { cva, type VariantProps } from "class-variance-authority"
import * as React from "react"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98] focus-visible:outline-none",
  {
    variants: {
      variant: {
        primary: "bg-tg-button text-tg-button-text hover:opacity-90",
        secondary: "bg-tg-secondary-bg text-tg-text hover:opacity-90",
        ghost: "bg-transparent text-tg-link hover:bg-tg-secondary-bg",
        destructive: "bg-tg-destructive text-white hover:opacity-90",
      },
      size: {
        sm: "h-9 px-3",
        md: "h-11 px-4",
        lg: "h-14 px-6 text-base",
        full: "h-12 w-full px-4",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
)
Button.displayName = "Button"
