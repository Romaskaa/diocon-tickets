import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold transition-colors border",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--hover-2)] text-[var(--text-secondary)] border-[var(--border-color)]",
        secondary:
          "bg-transparent text-[var(--text-muted)] border-[var(--border-color)]",
        destructive:
          "bg-[var(--error)]/8 text-[var(--error)] border-[var(--error)]/15",
        outline: 
          "bg-transparent text-[var(--text-secondary)] border-[var(--border-color)]",
        success:
          "bg-[var(--success)]/8 text-[var(--success)] border-[var(--success)]/15",
        warning:
          "bg-[var(--warning)]/8 text-[var(--warning)] border-[var(--warning)]/15",
        info:
          "bg-[var(--info)]/8 text-[var(--info)] border-[var(--info)]/15",
        brand:
          "bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent-soft)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
