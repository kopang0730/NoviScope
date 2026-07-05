import type { FormEvent } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createQuest } from "../api/quests";
import { getErrorMessage } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { Button } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input, TextArea } from "../components/input";

export function CreateQuestPage() {
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  const [title, setTitle] = useState("");
  const [initialDirection, setInitialDirection] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const quest = await createQuest({
        initial_direction: initialDirection,
        title,
      });
      navigate(`/?quest=${quest.id}`, { replace: true });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeading
        description="Create a research quest and seed the first workflow stage from the current backend."
        title="New Quest"
      />
      {!currentUser ? (
        <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Sign in first to create a quest. The form stays available here so the route can still be validated during UI smoke tests.
        </p>
      ) : null}
      <form className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]" onSubmit={(event) => void handleSubmit(event)}>
        <div className="space-y-4">
          <Input
            label="Quest Title"
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Handwritten text erasure benchmark"
            required
            value={title}
          />
        </div>
        <div className="space-y-4">
          <TextArea
            label="Initial Research Direction"
            onChange={(event) => setInitialDirection(event.target.value)}
            placeholder="Summarize the research goal, evaluation target, and immediate next step."
            required
            rows={8}
            value={initialDirection}
          />
        </div>
        <div className="lg:col-span-2">
          {error ? <p className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
          <Button loading={submitting} type="submit">
            Create Quest
          </Button>
        </div>
      </form>
    </Card>
  );
}
