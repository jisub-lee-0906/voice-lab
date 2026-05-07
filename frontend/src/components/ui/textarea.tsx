import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn("min-h-28 w-full rounded-xl border border-gray-200 bg-white px-3 py-3 text-sm text-gray-950 shadow-sm outline-none transition placeholder:text-gray-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100", className)}
    {...props}
  />
));
Textarea.displayName = "Textarea";
