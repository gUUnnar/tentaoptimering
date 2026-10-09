import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const variants = cva("inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-700 disabled:pointer-events-none disabled:opacity-50", { variants: { variant: { default: "bg-sky-800 text-white hover:bg-sky-900", outline: "border border-slate-300 bg-white hover:bg-slate-50", ghost: "hover:bg-slate-100", destructive: "bg-red-700 text-white" }, size: { default: "h-9 px-3", sm: "h-8 px-2.5 text-xs", lg: "h-10 px-4" } }, defaultVariants: { variant: "default", size: "default" } })
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof variants> {}
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, ...props }, ref) => <button ref={ref} className={cn(variants({ variant, size }), className)} {...props} />)
Button.displayName = "Button"
