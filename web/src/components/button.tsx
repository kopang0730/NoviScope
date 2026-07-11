import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md";

export function buttonClassName({
  className,
  size = "md",
  variant = "primary",
}: {
  className?: string;
  size?: ButtonSize;
  variant?: ButtonVariant;
}) {
  const sizeClassName = size === "sm" ? "h-11 px-3 text-sm" : "h-11 px-4 text-sm";
  const variantClassName =
    variant === "primary"
      ? "bg-teal-600 text-white hover:bg-teal-700"
      : variant === "secondary"
        ? "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
        : "bg-transparent text-slate-700 hover:bg-slate-100";

  return [
    "inline-flex items-center justify-center whitespace-nowrap rounded-lg font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60",
    sizeClassName,
    variantClassName,
    className,
  ]
    .filter(Boolean)
    .join(" ");
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  loading?: boolean;
  size?: ButtonSize;
  variant?: ButtonVariant;
};

export function Button({
  children,
  className,
  disabled,
  loading = false,
  size = "md",
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  return (
    <button
      className={buttonClassName({ className, size, variant })}
      disabled={disabled || loading}
      type={type}
      {...props}
    >
      {loading ? "Working..." : children}
    </button>
  );
}
