import { useState } from "react";
import { getErrorMessage } from "../api/client";
import { getQuestExport } from "../api/quests";
import type { Quest } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { downloadTextFile } from "../lib/download-file";
import { Button } from "./button";

type CanvasTrustExportButtonProps = {
  readonly quest: Quest | null;
};

function trustExportFilename(quest: Quest) {
  return `${quest.id}-trust-export.json`;
}

export function CanvasTrustExportButton({ quest }: CanvasTrustExportButtonProps) {
  const { t } = useI18n();
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  if (!quest) {
    return null;
  }

  const currentQuest = quest;

  async function downloadTrustExport() {
    setDownloadError(null);
    setDownloading(true);

    try {
      const trustExport = await getQuestExport(currentQuest.id);
      downloadTextFile({
        content: `${JSON.stringify(trustExport, null, 2)}\n`,
        filename: trustExportFilename(currentQuest),
        mimeType: "application/json;charset=utf-8",
      });
    } catch (error) {
      if (error instanceof Error) {
        setDownloadError(getErrorMessage(error));
        return;
      }
      throw error;
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <Button
        loading={downloading}
        onClick={() => void downloadTrustExport()}
        size="sm"
        type="button"
        variant="secondary"
      >
        {t("downloadTrustExport")}
      </Button>
      {downloadError ? <span className="max-w-[220px] text-xs leading-5 text-rose-700">{downloadError}</span> : null}
    </div>
  );
}
