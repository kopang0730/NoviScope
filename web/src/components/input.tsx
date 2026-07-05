import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

export const fieldClassName =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-200";

function Field({
  children,
  error,
  hint,
  label,
}: {
  children: ReactNode;
  error?: string;
  hint?: string;
  label: string;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {children}
      {error ? <span className="text-xs text-rose-600">{error}</span> : hint ? <span className="text-xs text-slate-500">{hint}</span> : null}
    </label>
  );
}

type TextInputProps = InputHTMLAttributes<HTMLInputElement> & {
  error?: string;
  hint?: string;
  label: string;
};

export function Input({ className, error, hint, label, ...props }: TextInputProps) {
  return (
    <Field error={error} hint={hint} label={label}>
      <input className={[fieldClassName, className].filter(Boolean).join(" ")} {...props} />
    </Field>
  );
}

type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  error?: string;
  hint?: string;
  label: string;
};

export function TextArea({ className, error, hint, label, rows = 4, ...props }: TextAreaProps) {
  return (
    <Field error={error} hint={hint} label={label}>
      <textarea
        className={[fieldClassName, "min-h-[120px] resize-y py-2.5", className].filter(Boolean).join(" ")}
        rows={rows}
        {...props}
      />
    </Field>
  );
}

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  error?: string;
  hint?: string;
  label: string;
};

export function Select({ children, className, error, hint, label, ...props }: SelectProps) {
  return (
    <Field error={error} hint={hint} label={label}>
      <select className={[fieldClassName, className].filter(Boolean).join(" ")} {...props}>
        {children}
      </select>
    </Field>
  );
}
