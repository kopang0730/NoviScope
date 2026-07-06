import { useEffect, useState, type ReactNode } from "react";
import { getErrorMessage } from "../api/client";
import { buildStageArtifactDownloadPath, getStageArtifacts } from "../api/quests";
import type { MarkdownArtifactManifestItem, MarkdownArtifactManifestResponse, StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import {
  buildPaperMeetingWriterView,
  type MarkdownArtifact,
} from "../lib/paper-meeting-view";
import { downloadTextFile } from "../lib/download-file";
import { Badge } from "./badge";
import { Button, buttonClassName } from "./button";
import { SourceStageList } from "./source-stage-list";

function BulletList({ emptyLabel, items }: { readonly emptyLabel: string; readonly items: readonly string[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{emptyLabel}</p>;
  }

  return (
    <ul className="space-y-1 text-sm text-slate-600">
      {items.map((item) => (
        <li className="flex gap-2" key={item}>
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function DetailBlock({
  children,
  title,
}: {
  readonly children: ReactNode;
  readonly title: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <div className="mt-2">{children}</div>
    </div>
  );
}

function findManifestItem(
  manifest: MarkdownArtifactManifestResponse | null,
  artifact: MarkdownArtifact,
) {
  return manifest?.artifacts.find((item) => item.key === artifact.key) ?? null;
}

function ArtifactCard({
  artifact,
  manifestError,
  manifestItem,
}: {
  readonly artifact: MarkdownArtifact;
  readonly manifestError: string;
  readonly manifestItem: MarkdownArtifactManifestItem | null;
}) {
  const { t } = useI18n();
  const hasContent = artifact.content.trim().length > 0;
  const filename = manifestItem?.filename ?? artifact.filename;
  const preview = hasContent ? artifact.content.split("\n").slice(0, 10).join("\n") : t("notAvailable");
  const serverDownloadPath =
    manifestItem?.available === true ? buildStageArtifactDownloadPath(manifestItem.download_url) : "";
  const missingReason = manifestItem?.available === false ? manifestItem.missing_reason : "";
  const canUseLocalFallback = !serverDownloadPath && manifestError.length > 0 && hasContent;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">{t(artifact.titleKey)}</p>
          <p className="mt-1 text-xs text-slate-500">{filename}</p>
        </div>
        {serverDownloadPath ? (
          <a
            className={buttonClassName({ size: "sm", variant: "secondary" })}
            download={filename}
            href={serverDownloadPath}
          >
            {t("downloadMarkdown")}
          </a>
        ) : (
          <Button
            disabled={!canUseLocalFallback}
            onClick={() =>
              downloadTextFile({
                content: artifact.content,
                filename,
                mimeType: "text/markdown;charset=utf-8",
              })
            }
            size="sm"
            title={manifestError || t("artifactDownloadPreparing")}
            type="button"
            variant="secondary"
          >
            {t("downloadMarkdown")}
          </Button>
        )}
      </div>
      {missingReason ? <p className="mt-3 text-xs text-slate-500">{missingReason}</p> : null}
      {canUseLocalFallback ? <p className="mt-3 text-xs text-slate-500">{t("artifactDownloadFallbackNotice")}</p> : null}
      <pre className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100">
        {preview}
      </pre>
    </div>
  );
}

export function PaperMeetingOutput({ stage }: { readonly stage: StageCard }) {
  const { t } = useI18n();
  const view = buildPaperMeetingWriterView(stage);
  const [manifest, setManifest] = useState<MarkdownArtifactManifestResponse | null>(null);
  const [manifestError, setManifestError] = useState("");

  useEffect(() => {
    let isCurrent = true;

    setManifest(null);
    setManifestError("");

    void getStageArtifacts(stage.id)
      .then((nextManifest) => {
        if (isCurrent) {
          setManifest(nextManifest);
        }
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setManifestError(getErrorMessage(error));
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [stage.id]);

  if (!view) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
        {t("noPaperArtifactsFound")}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="amber">{t("draftOnlyNotice")}</Badge>
          <Badge tone="teal">
            {t("stageConfidence")}: {labelFromEnum(view.confidence)}
          </Badge>
        </div>
        <p className="mt-3 text-sm text-amber-900">{view.summary}</p>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        {view.artifacts.map((artifact) => (
          <ArtifactCard
            artifact={artifact}
            key={artifact.key}
            manifestError={manifestError}
            manifestItem={findManifestItem(manifest, artifact)}
          />
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <DetailBlock title={t("verifiedFacts")}>
          <BulletList emptyLabel={t("notAvailable")} items={view.verifiedFacts} />
        </DetailBlock>
        <DetailBlock title={t("modelGeneratedHypotheses")}>
          <BulletList emptyLabel={t("notAvailable")} items={view.modelGeneratedHypotheses} />
        </DetailBlock>
        <DetailBlock title={t("experimentResultsNotAvailable")}>
          <BulletList emptyLabel={t("notAvailable")} items={view.experimentResultsNotAvailable} />
        </DetailBlock>
        <DetailBlock title={t("humanReviewRequired")}>
          <BulletList emptyLabel={t("notAvailable")} items={view.humanReviewRequired} />
        </DetailBlock>
        <DetailBlock title={t("sourceStages")}>
          <SourceStageList sourceStageIds={view.sourceStageIds} />
        </DetailBlock>
      </div>

      {view.warnings.length > 0 ? (
        <DetailBlock title={t("warnings")}>
          <BulletList emptyLabel={t("notAvailable")} items={view.warnings} />
        </DetailBlock>
      ) : null}
    </div>
  );
}
