import { cn } from "@/lib/utils"
import type { ReactNode } from "react"
export function Badge({ className, children }: { className?: string, children: ReactNode }) { return <span className={cn("inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700", className)}>{children}</span> }
