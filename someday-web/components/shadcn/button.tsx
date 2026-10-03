import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"
import { Slot } from "radix-ui"

// Style guide section 4: exactly two button looks. Variants reuse the global
// .btn-primary / .btn-ghost classes so shadcn buttons match the rest of the
// app. "destructive" is the ghost button with --cp text, never a red fill.
const buttonVariants = cva(
  "text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-60",
  {
    variants: {
      variant: {
        default: "btn-primary",
        outline: "btn-ghost",
        // text-destructive! because .btn-ghost (unlayered) sets color and wins over utilities.
        destructive: "btn-ghost text-destructive!",
      },
      size: {
        default: "px-5 py-3",
        sm: "px-4 py-2",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
