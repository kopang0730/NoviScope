import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { getQuest, getQuestStages, updateStage } from "../api/quests";
import { getErrorMessage } from "../api/client";
import type { Quest, StageCard, StageStatus } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { Badge } from "../components/badge";
import { Button, buttonClassName } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Select, TextArea } from "../components/input";
import { JsonView } from "../components/json-view";
import { formatDateTime, labelFromEnum, stringifyJson } from "../lib/format";

const stageStatuses: StageStatus[] = ["pending", "running", "blocked", "complete"];

type FormState = {
  evidencePayload: string;
  humanApproved: "pending_review" | "approved" | "rejected";
  inputPayload: string;
  outputPayload: string;
  reviewNotes: string;
  status: StageStatus;
  summary: string;
};

function stageTone(status: StageStatus) {
  if (status === "complete") {
    return "green";
  }
  if (status === "running") {
    return "amber";
  }
  if (status === "blocked") {
    return "red";
  }
  return "gray";
}

function buildFormState(stage: StageCard): FormState {
  return {
    evidencePayload: stringifyJson(stage.evidence_payload),
    humanApproved: stage.human_approved === null ? "pending_review" : stage.human_approved ? "approved" : "rejected",
    inputPayload: stringifyJson(stage.input_payload),
    outputPayload: stringifyJson(stage.output_payload),
    reviewNotes: stage.review_notes,
    status: stage.status,
    summary: stage.summary,
  };
}

export function StageDetailPage() {
  const { stageId } = useParams();
  const [searchParams] = useSearchParams();
  const { authReady, currentUser } = useAuth();
  const questId = searchParams.get("quest");

  const [quest, setQuest] = useState<Quest | null>(null);
  const [stage, setStage] = useState<StageCard | null>(null);
  const [formState, setFormState] = useState<FormState | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!stageId || !questId || !currentUser) {
      setQuest(null);
      setStage(null);
      setFormState(null);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setLoadError(null);

    void Promise.all([getQuest(questId), getQuestStages(questId)])
      .then(([nextQuest, stages]) => {
        if (!active) {
          return;
        }

        const nextStage = stages.find((candidate) => candidate.id === stageId);
        if (!nextStage) {
          throw new Error("Stage not found in the selected quest.");
        }

        setQuest(nextQuest);
        setStage(nextStage);
        setFormState(buildFormState(nextStage));
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setLoadError(getErrorMessage(error));
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [currentUser, questId, stageId]);

  const workflowBackLink = useMemo(() => (questId ? `/?quest=${questId}` : "/"), [questId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!stageId || !formState) {
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    setSuccessMessage(null);

    try {
      const inputPayload = JSON.parse(formState.inputPayload) as Record<string, unknown>;
      const outputPayload = JSON.parse(formState.outputPayload) as Record<string, unknown>;
      const evidencePayload = JSON.parse(formState.evidencePayload) as Record<string, unknown>;
      const humanApproved =
        formState.humanApproved === "pending_review" ? undefined : formState.humanApproved === "approved";

      const updatedStage = await updateStage(stageId, {
        evidence_payload: evidencePayload,
        human_approved: humanApproved,
        input_payload: inputPayload,
        output_payload: outputPayload,
        review_notes: formState.reviewNotes,
        status: formState.status,
        summary: formState.summary,
      });

      setStage(updatedStage);
      setFormState(buildFormState(updatedStage));
      setSuccessMessage("Stage updated successfully.");
    } catch (error) {
      setSubmitError(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  if (!questId) {
    return (
      <Card>
        <CardHeading description="Open this view from a quest workflow so the page knows which quest owns the stage." title="Stage Detail" />
        <p className="mt-4 text-sm text-slate-600">Missing `quest` query parameter.</p>
      </Card>
    );
  }

  if (!currentUser && authReady) {
    return (
      <Card>
        <CardHeading description="Sign in to edit a workflow stage." title="Stage Detail" />
        <Link className={buttonClassName({ variant: "primary" })} to="/login">
          Go to login
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm text-slate-500">Stage Editor</p>
            <h1 className="mt-1 text-xl font-semibold text-slate-900">{stage?.title ?? "Workflow stage"}</h1>
            {quest ? <p className="mt-2 text-sm text-slate-600">{quest.title}</p> : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {stage ? <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge> : null}
            <Link className={buttonClassName({ variant: "secondary", size: "sm" })} to={workflowBackLink}>
              Back to Workflow
            </Link>
          </div>
        </div>
        {loadError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{loadError}</p> : null}
        {loading ? <p className="mt-4 text-sm text-slate-500">Loading stage data...</p> : null}
        {stage ? (
          <div className="mt-4 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
            <p>Agent ID: {stage.agent_id}</p>
            <p>Updated: {formatDateTime(stage.updated_at)}</p>
          </div>
        ) : null}
      </Card>

      {stage && formState ? (
        <>
          <Card>
            <CardHeading description="Update stage status, summary, approval, and payloads." title="Edit Stage" />
            <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
              <div className="grid gap-4 lg:grid-cols-2">
                <Select
                  label="Status"
                  onChange={(event) => setFormState((current) => (current ? { ...current, status: event.target.value as StageStatus } : current))}
                  value={formState.status}
                >
                  {stageStatuses.map((status) => (
                    <option key={status} value={status}>
                      {labelFromEnum(status)}
                    </option>
                  ))}
                </Select>
                <Select
                  hint={
                    formState.humanApproved === "pending_review"
                      ? "This stage has not been reviewed yet. Choose Approved or Rejected to record a decision."
                      : "You can change the current decision, but the API does not support clearing it back to no decision."
                  }
                  label="Human Approval"
                  onChange={(event) =>
                    setFormState((current) =>
                      current ? { ...current, humanApproved: event.target.value as FormState["humanApproved"] } : current,
                    )
                  }
                  value={formState.humanApproved}
                >
                  {formState.humanApproved === "pending_review" ? (
                    <option value="pending_review">Not yet reviewed</option>
                  ) : null}
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                </Select>
              </div>
              <TextArea
                label="Summary"
                onChange={(event) => setFormState((current) => (current ? { ...current, summary: event.target.value } : current))}
                rows={5}
                value={formState.summary}
              />
              <TextArea
                label="Review Notes"
                onChange={(event) => setFormState((current) => (current ? { ...current, reviewNotes: event.target.value } : current))}
                rows={4}
                value={formState.reviewNotes}
              />
              <div className="grid gap-4 xl:grid-cols-3">
                <TextArea
                  label="Input Payload"
                  onChange={(event) => setFormState((current) => (current ? { ...current, inputPayload: event.target.value } : current))}
                  rows={10}
                  value={formState.inputPayload}
                />
                <TextArea
                  label="Output Payload"
                  onChange={(event) => setFormState((current) => (current ? { ...current, outputPayload: event.target.value } : current))}
                  rows={10}
                  value={formState.outputPayload}
                />
                <TextArea
                  label="Evidence Payload"
                  onChange={(event) => setFormState((current) => (current ? { ...current, evidencePayload: event.target.value } : current))}
                  rows={10}
                  value={formState.evidencePayload}
                />
              </div>
              {submitError ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitError}</p> : null}
              {successMessage ? <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{successMessage}</p> : null}
              <Button loading={submitting} type="submit">
                Save Stage
              </Button>
            </form>
          </Card>

          <div className="grid gap-4 xl:grid-cols-3">
            <JsonView title="Input Payload" value={stage.input_payload} />
            <JsonView title="Output Payload" value={stage.output_payload} />
            <JsonView title="Evidence Payload" value={stage.evidence_payload} />
          </div>
        </>
      ) : null}
    </div>
  );
}
