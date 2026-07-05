import { Card } from "./card";

export function JsonView({ title, value }: { title: string; value: Record<string, unknown> }) {
  return (
    <Card className="bg-slate-950 p-0">
      <div className="border-b border-slate-800 px-4 py-3">
        <p className="text-sm font-medium text-slate-100">{title}</p>
      </div>
      <pre className="overflow-x-auto px-4 py-4 text-xs leading-6 text-slate-200">
        {JSON.stringify(value, null, 2)}
      </pre>
    </Card>
  );
}
