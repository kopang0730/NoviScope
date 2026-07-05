import type { HTMLAttributes, ReactNode, ThHTMLAttributes, TdHTMLAttributes } from "react";

export function Table({ children, className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="hidden overflow-x-auto md:block">
      <table className={["min-w-full border-separate border-spacing-0 text-left text-sm", className].filter(Boolean).join(" ")} {...props}>
        {children}
      </table>
    </div>
  );
}

export function TableHead({ children, className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={["border-b border-slate-200 px-4 py-3 text-xs font-medium uppercase tracking-[0.08em] text-slate-500", className].filter(Boolean).join(" ")}
      {...props}
    >
      {children}
    </th>
  );
}

export function TableCell({ children, className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={["border-b border-slate-100 px-4 py-3 align-top text-slate-700", className].filter(Boolean).join(" ")} {...props}>
      {children}
    </td>
  );
}

export function MobileStack({ children }: { children: ReactNode }) {
  return <div className="space-y-3 md:hidden">{children}</div>;
}
