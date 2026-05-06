import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default:
          "bg-white/10 text-white/70",
        secondary:
          "bg-white/5 text-white/60",
        destructive:
          "bg-red-500/10 text-red-400",
        outline: 
          "border border-white/10 bg-transparent text-white/70",
        success:
          "bg-emerald-500/10 text-emerald-400",
        warning:
          "bg-amber-500/10 text-amber-400",
        info:
          "bg-blue-500/10 text-blue-400",
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
