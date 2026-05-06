import { User } from "lucide-react";
import { cn } from "@/lib/utils";

interface UserIconProps {
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  className?: string;
}

const sizeClasses = {
  xs: "h-6 w-6",
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-12 w-12",
  xl: "h-16 w-16",
};

const iconSizes = {
  xs: 12,
  sm: 14,
  md: 18,
  lg: 22,
  xl: 28,
};

export function UserIcon({ size = "md", className }: UserIconProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full bg-white/10 border border-white/10",
        sizeClasses[size],
        className
      )}
    >
      <User size={iconSizes[size]} className="text-neutral-400" />
    </div>
  );
}
