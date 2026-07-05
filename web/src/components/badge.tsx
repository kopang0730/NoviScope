import type { ReactNode } from "react";

export type BadgeTone = "blue" | "gray" | "green" | "amber" | "red" | "teal";

const toneClassNames: Record<BadgeTone, string> = {
  amber: "bg-amber-100 text-amber-800",
  blue: "bg-sky-100 text-sky-800",
  gray: "bg-slate-100 text-slate-700",
  green: "bg-emerald-100 text-emerald-800",
  red: "bg-rose-100 text-rose-800",
  teal: "bg-teal-100 text-teal-800",
};

export function Badge({ children, tone = "gray" }: { children: ReactNode; tone?: BadgeTone }) {
  return (
    <span className={["inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium", toneClassNames[tone]].join(" ")}>
      {children}
    </span>
  );
}
