import type { HTMLAttributes, ReactNode } from "react";

export function Card({ children, className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <section
      className={["rounded-lg border border-slate-200 bg-white p-5 shadow-panel sm:p-6", className].filter(Boolean).join(" ")}
      {...props}
    >
      {children}
    </section>
  );
}

export function CardHeading({
  action,
  description,
  title,
}: {
  action?: ReactNode;
  description?: string;
  title: string;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
