import { type HTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

const variants = {
  default: "border-transparent bg-primary text-primary-foreground",
  secondary: "border-transparent bg-secondary text-secondary-foreground",
  destructive: "border-transparent bg-destructive text-destructive-foreground",
  outline: "text-foreground",
  success: "border-transparent bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  warning: "border-transparent bg-amber-500/10 text-amber-600 dark:text-amber-400",
} as const;

interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: keyof typeof variants;
}

export const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold transition-colors",
          variants[variant],
          className,
        )}
        {...props}
      />
    );
  },
);
Badge.displayName = "Badge";
