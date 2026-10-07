import { forwardRef, type ButtonHTMLAttributes } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
// shadcn-style local component: accessible native button, no remote runtime.
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement>
>(function Button({ className, ...props }, ref) {
  return (
    <button
      ref={ref}
      className={twMerge(clsx("button", className))}
      {...props}
    />
  );
});
